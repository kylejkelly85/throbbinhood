# scripts/generate_story.py

import json
import logging
import random
import re
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
    mirostat: int = 0  # 0 = disabled, 1 = Mirostat, 2 = Mirostat 2.0
    mirostat_tau: float = 5.0  # Target entropy/perplexity (creativity level)
    mirostat_eta: float = 0.1  # Learning rate adjustments
    genres: Dict[str, Any] = field(default_factory=dict)
    tropes: Dict[str, Any] = field(default_factory=dict)
    rules: Dict[str, Any] = field(default_factory=dict)


def get_ollama_client() -> ollama.Client:
    """Factory function initializing the strict Ollama network client assignment."""
    return ollama.Client(host="http://192.168.1.252:11434", timeout=300)


def clean_json_response(text: str) -> str:
    """Extracts valid JSON boundaries from model outputs, stripping raw markdown fence wrappers safely."""
    ticks = "`" * 3
    text = re.sub(rf'{ticks}(?:json)?\s*', '', text)
    text = re.sub(rf'{ticks}\s*$', '', text)
    
    start_boundary = text.find('{')
    end_boundary = text.rfind('}')
    if start_boundary != -1 and end_boundary != -1:
        text = text[start_boundary:end_boundary + 1]
        
    return text.strip()


def load_configuration() -> PlatformConfig:
    """Loads and caches configuration parameters, dynamically mapping Mirostat options from execution rules."""
    logger.info("Loading system orchestration configuration parameters from data/ files.")
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
            mirostat=int(rules.get("mirostat", 0)),
            mirostat_tau=float(rules.get("mirostat_tau", 5.0)),
            mirostat_eta=float(rules.get("mirostat_eta", 0.1)),
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


def generate_metadata_layer(
    client: ollama.Client, 
    config: PlatformConfig, 
    source_story: Dict[str, Any], 
    genre_title: str, 
    tropes_string: str
) -> Dict[str, Any]:
    """Executes a structural metadata schema pass using strict user/system separation and JSON cleaning arrays."""
    logger.info("Dispatching Step 1: Structural metadata schema generation loop.")
    
    meta_schema = {
        "title": "Generated novel variation title",
        "summary": "Overall 3-act narrative blueprint master synopsis",
        "series": "Named collection identifier string or an empty string",
        "characters": [
            {
                "name": "Character Name",
                "role": "Protagonist / Love Interest / Primary Antagonist / Supporting",
                "description": "Thematic personality outline trait overview"
            }
        ]
    }

    prompt = f"""
Build architectural metadata for a new novel adaptation based on these target variables:
Source Premise: {source_story['title']}
Target Structural Genre: {genre_title}
Target Narrative Elements: {tropes_string}

Instructions:
- Construct structural elements targeting a title, overall summary blueprint, and character registry mapping context.
- Keep the character pool count restricted between 2 and 8 entries. Prioritize protagonist, love interest, and primary antagonist dynamics.
- Output your response strictly inside a SINGLE, valid JSON object matching the design template pattern below.

Target Pattern:
{json.dumps(meta_schema, indent=2)}
"""
    
    options_payload = {
        "temperature": 0.2,
        "top_p": 0.9,
        "repeat_penalty": config.repeat_penalty,
        "num_ctx": 4096
    }
    
    response = client.chat(
        model=config.model_name,
        messages=[
            {"role": "system", "content": "You are a JSON tracking asset validation tool. Output valid JSON objects exclusively."},
            {"role": "user", "content": prompt.strip()}
        ],
        format="json",
        options=options_payload
    )
    
    cleaned_content = clean_json_response(response["message"]["content"])
    return json.loads(cleaned_content)


def generate_act_layer(
    client: ollama.Client,
    config: PlatformConfig,
    act_name: str,
    act_instructions: str,
    meta_layer: Dict[str, Any],
    genre_meta: Dict[str, Any],
    tropes_string: str,
    prior_act_content: Optional[str] = None,
    max_continuations: int = 4
) -> str:
    """Generates a standalone prose segment chunk, utilizing Mirostat parameters dynamically if enabled in config."""
    logger.info(f"Generating prose segment chunk: {act_name}")
    
    genre_title = genre_meta.get("title", "Unknown Genre")
    genre_setting = genre_meta.get("setting", "Unspecified Setting")
    genre_tones = ", ".join(genre_meta.get("tone", []))
    char_string = "\n".join([f"- {c.get('name')} ({c.get('role')}): {c.get('description')}" for c in meta_layer.get("characters", [])])

    history_context = ""
    if prior_act_content:
        history_context = f"\nPreviously in the story, the following events occurred:\n[[[ PRIOR NARRATIVE HISTORY ]]]\n{prior_act_content[-2000:]}\n[[[ END OF HISTORY ]]]\n"

    base_prompt = f"""
You are a long-form creative writer. Write a fluid chronological segment of an immersive novel titled '{meta_layer['title']}'.

Current Processing Segment: {act_name}
Segment Objective: {act_instructions}

World Configuration Parameters:
- Genre: {genre_title}
- Setting Context: {genre_setting}
- Tonal Atmosphere: {genre_tones}
- Mandatory Integrated Themes: {tropes_string}
- Active Character Cast: 
{char_string}
{history_context}
Writing Instructions:
- Continue the sequence using fluid, natural prose paragraphs separated by a double line break (\\n\\n).
- Start writing the story text for this segment immediately without narrative preambles or notes.
"""
    
    options_payload = {
        "num_ctx": 4096,
        "num_predict": 512,
        "repeat_penalty": config.repeat_penalty
    }
    
    if config.mirostat in [1, 2]:
        options_payload["mirostat"] = config.mirostat
        options_payload["mirostat_tau"] = config.mirostat_tau
        options_payload["mirostat_eta"] = config.mirostat_eta
        options_payload["temperature"] = config.temperature
    else:
        options_payload["temperature"] = config.temperature
        options_payload["top_p"] = config.top_p

    response = client.chat(
        model=config.model_name,
        messages=[
            {"role": "system", "content": "You are an untamed creative writer. Output direct story prose text without conversational introduction meta notes."},
            {"role": "user", "content": base_prompt.strip()}
        ],
        options=options_payload
    )
    
    accumulated_prose = response["message"]["content"].strip()
    
    for loop_idx in range(max_continuations):
        if accumulated_prose and accumulated_prose[-1] not in [".", "!", "?", '"', '»']:
            logger.warning(f"Detected paragraph truncation split within {act_name}. Dispatching text continuation query turn {loop_idx + 1}.")
            
            continuation_prompt = f"Continue writing the story seamlessly from this exact point without repeating existing text:\n\n... {accumulated_prose[-400:]}"
            
            extension_res = client.chat(
                model=config.model_name,
                messages=[
                    {"role": "system", "content": "Continue writing raw story text seamlessly. No notes."},
                    {"role": "user", "content": continuation_prompt}
                ],
                options=options_payload
            )
            
            new_chunk = extension_res["message"]["content"].strip()
            new_chunk = re.sub(r'^(Here is|Continuing|Next paragraph).*?:', '', new_chunk).strip()
            if new_chunk.startswith("..."):
                new_chunk = new_chunk[3:].strip()
                
            overlap_len = min(60, len(accumulated_prose), len(new_chunk))
            overlap_found = False
            for match_size in range(overlap_len, 4, -1):
                if accumulated_prose[-match_size:].lower() == new_chunk[:match_size].lower():
                    new_chunk = new_chunk[match_size:]
                    overlap_found = True
                    break
                    
            if overlap_found:
                accumulated_prose = f"{accumulated_prose}{new_chunk}"
            else:
                accumulated_prose = f"{accumulated_prose}\n\n{new_chunk}"
        else:
            break
            
    return accumulated_prose


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

    genre_key = random.choice(list(config.genres.keys()))
    genre_metadata = config.genres[genre_key]
    
    max_tropes_allowed = config.rules.get("max_tropes_per_story", 4)
    all_trope_keys = list(config.tropes.keys())
    num_tropes_to_pick = random.randint(2, min(max_tropes_allowed, len(all_trope_keys)))
    selected_trope_keys = random.sample(all_trope_keys, num_tropes_to_pick)
    
    selected_tropes_metadata = [config.tropes[tk] for tk in selected_trope_keys]
    trope_titles_list = [tm.get("title") for tm in selected_tropes_metadata]
    tropes_formatted_string = "\n".join([f"- {t.get('title')}: {t.get('description')}" for t in selected_tropes_metadata])
    
    logger.info(f"Target profile chosen: Genre='{genre_metadata.get('title')}', Tropes={trope_titles_list}")
    client = get_ollama_client()
    
    try:
        meta_layer = generate_metadata_layer(client, config, source_story, genre_metadata.get("title", ""), tropes_formatted_string)
        
        act_i = generate_act_layer(
            client, config, "Act I: Setup & Inciting Incident", 
            "Introduce the characters, define the setting, establish the initial friction, and introduce the main thematic conflict.", 
            meta_layer, genre_metadata, tropes_formatted_string
        )
        
        act_ii = generate_act_layer(
            client, config, "Act II: Rising Action & Complication", 
            "Complicate the relationship dynamics. Force the characters to work through their friction together while confronting obstacles or uncovering secrets.", 
            meta_layer, genre_metadata, tropes_formatted_string, prior_act_content=act_i
        )
        
        act_iii = generate_act_layer(
            client, config, "Act III: Climax & Absolute Resolution", 
            "Bring the thematic tension to an explosive peak. Break the core barriers down, settle the conflict permanently, and provide a definitive emotional wrap-up ending.", 
            meta_layer, genre_metadata, tropes_formatted_string, prior_act_content=act_ii
        )
        
        full_story_text = f"{act_i}\n\n{act_ii}\n\n{act_iii}"
        
        story_metadata = {
            "title": meta_layer.get("title", f"Novel Adaptation of {source_story['title']}"),
            "summary": meta_layer.get("summary", ""),
            "series": meta_layer.get("series", ""),
            "characters": meta_layer.get("characters", []),
            "genre": genre_metadata.get("title"),
            "tropes": trope_titles_list,
            "story": full_story_text
        }
        
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
        logger.info("ThrobbinHood multi-act text pipeline iteration completed successfully with Mirostat checks.")
        
    except Exception as run_err:
        logger.error(f"Execution engine failure running story mutation pipeline: {run_err}", exc_info=True)


if __name__ == "__main__":
    main()