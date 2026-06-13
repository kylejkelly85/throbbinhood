# scripts/generate_story.py

import json
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
    genres: List[str] = field(default_factory=list)
    tropes: List[str] = field(default_factory=list)
    rules: Dict[str, Any] = field(default_factory=dict)


def get_ollama_client() -> ollama.Client:
    """Factory function initializing the strict Ollama network client assignment."""
    return ollama.Client(host="http://192.168.1.252:11434", timeout=120)


def load_configuration() -> PlatformConfig:
    """Loads and caches runtime parameters from local platform environment files."""
    logger.info("Loading generation platform configurations.")
    try:
        with open("data/genres.yaml", "r", encoding="utf-8") as f:
            genres_data = yaml.safe_load(f)
            genres = genres_data.get("genres", []) if genres_data else []

        with open("data/tropes.yaml", "r", encoding="utf-8") as f:
            tropes_data = yaml.safe_load(f)
            tropes = tropes_data.get("tropes", []) if tropes_data else []

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


def construct_prompt(source_story: Dict[str, Any], genre: str, selected_tropes: List[str]) -> str:
    """Assembles structural baseline guidelines restricting prompt responses strictly to target criteria."""
    tropes_string = ", ".join(selected_tropes)
    
    schema_example = {
        "title": "Generated story title",
        "summary": "2-3 sentence synopsis",
        "genre": "Single genre string matching the selected genre",
        "series": "Empty string unless the source material is explicitly part of a named series",
        "tropes": ["trope1", "trope2"],
        "characters": [
            {
                "name": "Character Name",
                "role": "Protagonist/Love Interest/Primary Antagonist/Supporting",
                "description": "Brief description"
            }
        ],
        "story": "The complete generated story text"
    }

    prompt = f"""
You are a creative writing AI. Rewrite the following source material into a completely new story.
Source Title: {source_story['title']}
Source Author: {source_story['author']}

Target Genre: {genre}
Required Tropes: {tropes_string}

Execution Instructions:
1. Synthesize a brand new narrative loosely inspired by the structure, premise, or themes of the source text.
2. The story must match the requested Target Genre and naturally integrate ALL requested Required Tropes.
3. Identify and construct between 2 and 8 distinct characters. Prioritize the protagonist, love interest, and primary antagonist, then fill remaining slots by narrative importance. Exclude minor one-scene characters.
4. Output must be a SINGLE valid JSON object matching the exact schema schema listed below. Do not wrap the JSON object inside markdown formatting, do not include triple backticks, and do not provide any preceding or concluding explanations.

JSON Schema Output Specification:
{json.dumps(schema_example, indent=2)}

Source Material Content:
{source_story['content']}
"""
    return prompt.strip()


def query_llm_with_retry(client: ollama.Client, config: PlatformConfig, prompt: str, retries: int = 3) -> Dict[str, Any]:
    """Handles structured communication operations targeting Ollama container ports directly."""
    current_prompt = prompt
    for attempt in range(1, retries + 1):
        logger.info(f"Ollama generation dispatch attempt {attempt}/{retries}")
        try:
            response = client.chat(
                model=config.model_name,
                messages=[{"role": "user", "content": current_prompt}],
                format="json",
                options={
                    "temperature": config.temperature,
                    "top_p": config.top_p,
                    "repeat_penalty": config.repeat_penalty
                }
            )
            
            response_content = response["message"]["content"].strip()
            parsed_json = json.loads(response_content)
            
            required_keys = ["title", "summary", "genre", "series", "tropes", "characters", "story"]
            if all(key in parsed_json for key in required_keys):
                return parsed_json
                
            logger.warning("Ollama response missing structural schema nodes. Initiating loop retry correction parameters.")
            current_prompt = f"{prompt}\n\nCRITICAL ERROR: Your previous response did not fulfill the structural JSON validation schema constraints. Try again and verify all fields are present."
            
        except (json.JSONDecodeError, KeyError) as err:
            logger.warning(f"Ollama structured interface compilation serialization rejection on attempt {attempt}: {err}")
            current_prompt = f"{prompt}\n\nCRITICAL ERROR: Your previous response was not parseable as valid JSON. Ensure absolute conformity to format guidelines without escaping errors."
            
    raise RuntimeError("Ollama text parsing operations failed consistently across processing allocation thresholds.")


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
        logger.error("Execution terminated: No valid processing candidates within data source parameters.")
        return

    if not config.genres or not config.tropes:
        logger.error("Execution terminated: Required structural definition variables (genres/tropes) missing content.")
        return

    selected_genre = random.choice(config.genres)
    num_tropes = random.randint(2, min(4, len(config.tropes)))
    selected_tropes = random.sample(config.tropes, num_tropes)
    
    logger.info(f"Target profile chosen: Genre='{selected_genre}', Tropes={selected_tropes}")
    
    prompt = construct_prompt(source_story, selected_genre, selected_tropes)
    client = get_ollama_client()
    
    try:
        story_metadata = query_llm_with_retry(client, config, prompt)
        
        story_metadata["genre"] = selected_genre
        story_metadata["tropes"] = selected_tropes
        
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
        logger.info("ThrobbinHood core transformation workflow iteration finished successfully.")
        
    except Exception as run_err:
        logger.error(f"Execution engine failure running story mutation pipeline: {run_err}", exc_info=True)


if __name__ == "__main__":
    main()