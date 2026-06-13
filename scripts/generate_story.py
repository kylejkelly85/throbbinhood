import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import jinja2
import ollama
from slugify import slugify
import yaml

import db

logger = logging.getLogger("ThrobbinHood.generate_story")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


@dataclass
class PlatformConfig:
    db_path: str = "database/stories.db"
    content_dir: str = "content/stories/"
    model_name: str = "llama3"
    temperature: float = 0.7
    top_p: float = 0.9
    repeat_penalty: float = 1.1
    genres: Dict[str, Any] = field(default_factory=dict)
    tropes: Dict[str, Any] = field(default_factory=dict)
    rules: Dict[str, Any] = field(default_factory=dict)


def get_ollama_client() -> ollama.Client:
    """Factory function initializing the strict Ollama network client assignment."""
    return ollama.Client(host="http://192.168.1.252:11434", timeout=120)


def load_configuration() -> PlatformConfig:
    """Loads and caches runtime parameters from local dictionary-structured YAML configuration files."""
    logger.info("Loading mapping-based configuration files from data/ directory.")
    try:
        with open("data/genres.yaml", "r", encoding="utf-8") as f:
            genres = yaml.safe_load(f) or {}

        with open("data/tropes.yaml", "r", encoding="utf-8") as f:
            tropes = yaml.safe_load(f) or {}

        with open("data/generation_rules.yaml", "r", encoding="utf-8") as f:
            rules = yaml.safe_load(f) or {}

        return PlatformConfig(
            model_name=rules.get("model", "llama3"),
            temperature=float(rules.get("temperature", 0.7)),
            top_p=float(rules.get("top_p", 0.9)),
            repeat_penalty=float(rules.get("repeat_penalty", 1.1)),
            genres=genres,
            tropes=tropes,
            rules=rules
        )
    except Exception as e:
        logger.error(f"Failed to load platform configuration files: {e}", exc_info=True)
        raise


def resolve_unique_slug(content_dir: Path, base_title: str) -> str:
    """Generates a guaranteed unique filesystem and routing path token string match."""
    base_slug = slugify(base_title)
    candidate_slug = base_slug
    counter = 1
    
    while (content_dir / f"story-{candidate_slug}.md").exists():
        candidate_slug = f"{base_slug}-{counter}"
        counter += 1
        
    return candidate_slug


def construct_prompt(
    source_story: Dict[str, Any], 
    genre_meta: Dict[str, Any], 
    selected_tropes_meta: List[Dict[str, Any]], 
    rules: Dict[str, Any]
) -> str:
    """Assembles deep thematic instructions using precise key-mapped metadata, forcing unlabeled prose paragraphs."""
    genre_title = genre_meta.get("title", "Unknown Genre")
    genre_desc = genre_meta.get("description", "")
    genre_setting = genre_meta.get("setting", "Unspecified Setting")
    genre_tones = ", ".join(genre_meta.get("tone", []))
    
    trope_instructions = []
    for t in selected_tropes_meta:
        trope_instructions.append(f"- {t.get('title')}: {t.get('description')}")
    tropes_string = "\n".join(trope_instructions)

    length_rule = rules.get("story_length", {"min_words": 1500, "max_words": 3000})
    min_words = length_rule.get("min_words", 1500)
    max_words = length_rule.get("max_words", 3000)

    example_prose = (
        "The brooding silhouette of the ancient estate loomed against the storm-swept sky, "
        "its stone walls harboring decades of secrets. She stepped across the threshold, her heart "
        "hammering as the heavy oak door clicked shut behind her.\\n\\n"
        "In the shadows of the grand parlor stood a mysterious figure, whose cold gaze offered no warmth "
        "to the unexpected visitor. Yet, as their eyes locked, an undeniable tension crackled through "
        "the room—a dangerous attraction that defied all warnings.\\n\\n"
        "By midnight, the long-buried mysteries of the manor could no longer be contained. Hand in hand, "
        "they confronted the hidden truth, shattering the curse that bound them and securing a future "
        "born from the ashes of their past."
    )

    schema_example = {
        "title": "Generated story title",
        "summary": "2-3 sentence synopsis matching required_sections rule",
        "genre": genre_title,
        "series": "Empty string unless explicitly part of a named series",
        "tropes": [t.get("title") for t in selected_tropes_meta],
        "characters": [
            {
                "name": "Character Name",
                "role": "Protagonist/Love Interest/Primary Antagonist/Supporting",
                "description": "Brief description"
            }
        ],
        "story": example_prose
    }

    prompt = f"""
You are an expert creative software writer specializing in long-form literary generation. 
Your objective is to adapt, evolve, and expand the provided source material text into a new story.

Target Genre Profile:
- Genre: {genre_title}
- Motif: {genre_desc}
- Required Contextual Setting: {genre_setting}
- Mandatory Tonal Elements: {genre_tones}

Required Narrative Tropes to Integrate:
{tropes_string}

Structural Constraints:
- Length Constraint: The generated "story" string text value MUST fall between {min_words} and {max_words} words. 
- Character Pool Constraint: Document between 2 and 8 primary characters. Prioritize Protagonist, Love Interest, and Antagonist roles. Do not include negligible background personas.

Execution Instructions:
- Write the story using natural prose paragraphs. Separate every paragraph with exactly two newline characters (\\n\\n). 
- Do NOT include text headers, labels, or prefixes like "Paragraph 1:", "Introduction:", or chapter titles inside the story content. Write only the raw story text.
- Output your entire tracking response inside a SINGLE, valid JSON object matching the schema below. Do not wrap the output in markdown formatting or triple backtick blocks (```json).

JSON Structural Blueprint Schema:
{json.dumps(schema_example, indent=2)}

Source Text Baseline Blueprint Material:
{source_story['content']}
"""
    return prompt.strip()


def query_llm_with_retry(client: ollama.Client, config: PlatformConfig, prompt: str, retries: int = 3) -> Dict[str, Any]:
    """Handles structured communication operations, keeping num_ctx safe for 8GB hardware limits."""
    current_prompt = prompt
    for attempt in range(1, retries + 1):
        logger.info(f"Ollama structured interface compilation attempt {attempt}/{retries}")
        try:
            response = client.chat(
                model=config.model_name,
                messages=[{"role": "user", "content": current_prompt}],
                format="json",
                options={
                    "temperature": config.temperature,
                    "top_p": config.top_p,
                    "repeat_penalty": config.repeat_penalty,
                    "num_ctx": 4096  # Adjusted window to prevent VRAM buffer allocation crashes
                }
            )
            
            response_content = response["message"]["content"].strip()
            parsed_json = json.loads(response_content)
            
            required_keys = config.rules.get("required_metadata", ["title", "genre", "tropes", "series", "source_story"])
            required_sections = config.rules.get("required_sections", ["summary", "story"])
            all_validation_keys = set(required_keys + required_sections + ["characters"])
            
            missing_keys = [k for k in all_validation_keys if k != "source_story" and k not in parsed_json]
            
            if not missing_keys:
                return parsed_json
                
            logger.warning(f"Ollama response missing schema elements: {missing_keys}. Current keys found: {list(parsed_json.keys())}")
            current_prompt = f"{prompt}\n\nCRITICAL SYSTEM FAILURE: Your previous JSON object failed structural policy verification requirements. Missing keys: {missing_keys}. Ensure all requested object fields are populated."
            
        except (json.JSONDecodeError, KeyError) as err:
            logger.warning(f"Ollama compilation schema execution failure on attempt {attempt}: {err}")
            current_prompt = f"{prompt}\n\nCRITICAL SYSTEM FAILURE: The output string sent could not be deserialized by json.loads(). Output naked, unencapsulated clean valid JSON strings."
            
    raise RuntimeError("Ollama system resource context loops crashed across extreme attempt limits.")


def render_hugo_markdown(story_metadata: Dict[str, Any], source_title: str) -> str:
    """Compiles local pipeline content into static site markdown blocks using Jinja2 parsing tools."""
    template_str = """---
title: "{{ title }}"
date: {{ date }}
genres:
  - "{{ genre }}"
tropes:
{%- for trope in tropes %}
  - "{{ trope }}"
{%- endfor %}
series: "{{ series }}"
source_story: "{{ source_story }}"
summary: "{{ summary }}"
draft: false
---
{{ story }}
"""
    template = jinja2.Template(template_str)
    return template.render(
        title=story_metadata["title"],
        date=datetime.now().isoformat(),
        genre=story_metadata["genre"],
        tropes=story_metadata["tropes"],
        series=story_metadata.get("series", ""),
        source_story=source_title,
        summary=story_metadata["summary"],
        story=story_metadata["story"]
    )


def main() -> None:
    config = load_configuration()
    content_path = Path(config.content_dir)
    content_path.mkdir(parents=True, exist_ok=True)
    
    source_story = db.get_unused_source_story(config.db_path)
    if not source_story:
        logger.error("Execution terminated: No unused target story sources present inside storage paths.")
        return

    if not config.genres or not config.tropes:
        logger.error("Execution terminated: Metadata source parameter files contain missing or zero entries.")
        return

    genre_key = random.choice(list(config.genres.keys()))
    genre_metadata = config.genres[genre_key]
    
    max_tropes_allowed = config.rules.get("max_tropes_per_story", 4)
    all_trope_keys = list(config.tropes.keys())
    num_tropes_to_pick = random.randint(2, min(max_tropes_allowed, len(all_trope_keys)))
    selected_trope_keys = random.sample(all_trope_keys, num_tropes_to_pick)
    
    selected_tropes_metadata = [config.tropes[tk] for tk in selected_trope_keys]
    trope_titles_list = [tm.get("title") for tm in selected_tropes_metadata]
    
    logger.info(f"Target profile chosen: Genre='{genre_metadata.get('title')}', Tropes={trope_titles_list}")
    
    prompt = construct_prompt(source_story, genre_metadata, selected_tropes_metadata, config.rules)
    client = get_ollama_client()
    
    try:
        story_metadata = query_llm_with_retry(client, config, prompt)
        
        story_metadata["genre"] = genre_metadata.get("title")
        story_metadata["tropes"] = trope_titles_list
        
        unique_slug = resolve_unique_slug(content_path, story_metadata["title"])
        story_metadata["slug"] = unique_slug
        
        markdown_filename = f"story-{unique_slug}.md"
        target_file_path = content_path / markdown_filename
        
        markdown_output = render_hugo_markdown(story_metadata, source_story["title"])
        
        db.save_generated_story(config.db_path, story_metadata, source_story["id"])
        
        try:
            with open(target_file_path, "w", encoding="utf-8") as f:
                f.write(markdown_output)
            logger.info(f"Hugo content file compiled successfully: {target_file_path}")
        except Exception as file_err:
            logger.critical(f"Fatal platform state inconsistency: Database written, markdown file creation failed: {file_err}")
            raise
            
        db.mark_source_story_used(config.db_path, source_story["id"])
        logger.info("ThrobbinHood mapping-based text transformation workflow processing routine completed successfully.")
        
    except Exception as run_err:
        logger.error(f"Execution engine failure running story mutation pipeline: {run_err}", exc_info=True)


if __name__ == "__main__":
    main()