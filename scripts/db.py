# scripts/db.py

import json
import logging
import sqlite3
from typing import Any, Dict, Optional

logger = logging.getLogger("ThrobbinHood.db")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def initialize_database(db_path: str, schema_path: str) -> None:
    """Initializes the SQLite database using the provided schema SQL file."""
    logger.info(f"Initializing database at {db_path} using schema {schema_path}")
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            with conn:
                conn.executescript(schema_sql)
        logger.info("Database initialization completed successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise


def get_unused_source_story(db_path: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single unused source story from the database."""
    logger.info("Fetching an unused source story.")
    query = """
        SELECT id, title, author, content 
        FROM source_stories 
        WHERE used = 0 
        LIMIT 1;
    """
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query)
            row = cursor.fetchone()
            if row:
                story = dict(row)
                logger.info(f"Selected source story ID: {story['id']} - Title: {story['title']}")
                return story
            logger.warning("No unused source stories remaining in the database.")
            return None
    except Exception as e:
        logger.error(f"Error fetching unused source story: {e}", exc_info=True)
        raise


def save_generated_story(db_path: str, story_data: Dict[str, Any], source_story_id: int) -> None:
    """Saves a generated story's metadata and content into the database within a single transaction."""
    logger.info(f"Saving generated story titled '{story_data.get('title')}' for source story ID {source_story_id}")
    query = """
        INSERT INTO generated_stories (
            source_story_id, title, slug, summary, genre, series, tropes, characters, story_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """
    try:
        tropes_json = json.dumps(story_data.get("tropes", []))
        characters_json = json.dumps(story_data.get("characters", []))
        
        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            with conn:
                conn.execute(
                    query,
                    (
                        source_story_id,
                        story_data["title"],
                        story_data["slug"],
                        story_data["summary"],
                        story_data["genre"],
                        story_data.get("series", ""),
                        tropes_json,
                        characters_json,
                        story_data["story"]
                    )
                )
        logger.info(f"Generated story '{story_data['title']}' saved successfully.")
    except Exception as e:
        logger.error(f"Error saving generated story: {e}", exc_info=True)
        raise


def mark_source_story_used(db_path: str, source_story_id: int) -> None:
    """Marks a specific source story as used in the database."""
    logger.info(f"Marking source story ID {source_story_id} as used.")
    query = "UPDATE source_stories SET used = 1 WHERE id = ?;"
    try:
        with sqlite3.connect(db_path) as conn:
            with conn:
                cursor = conn.execute(query, (source_story_id,))
                if cursor.rowcount == 0:
                    logger.warning(f"No source story found with ID {source_story_id} to update.")
                else:
                    logger.info(f"Source story ID {source_story_id} marked as used.")
    except Exception as e:
        logger.error(f"Error marking source story as used: {e}", exc_info=True)
        raise