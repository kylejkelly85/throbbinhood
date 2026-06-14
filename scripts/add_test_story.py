import argparse
import logging
import re
import sqlite3
from pathlib import Path
from typing import Optional
import requests

logger = logging.getLogger("ThrobbinHood.add_test_story")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Curated high-utility presets ideal for testing various creative writing genres & tropes
PRESETS = {
    "frankenstein": 84,       # Mary Shelley - Gothic / Sci-Fi / Tragedy
    "dracula": 345,           # Bram Stoker - Gothic Horror / Suspense
    "moby_dick": 2701,        # Herman Melville - Adventure / Sea / Obsession
    "alice": 11,              # Lewis Carroll - Surreal / Fantasy / Whimsical
    "yellow_wallpaper": 162   # Charlotte Perkins Gilman - Psychological / Drama
}


def clean_gutenberg_content(text: str, max_characters: int = 12000) -> str:
    """Removes standard Project Gutenberg headers, footers, and trims text to a clean character boundary."""
    start_markers = [
        r"\*\*\* START OF THIS PROJECT GUTENBERG EBOOK",
        r"\*\*\* START OF THE PROJECT GUTENBERG EBOOK",
        r"START AFTER THIS PROJECT GUTENBERG"
    ]
    end_markers = [
        r"\*\*\* END OF THIS PROJECT GUTENBERG EBOOK",
        r"\*\*\* END OF THE PROJECT GUTENBERG EBOOK",
        r"END OF THIS PROJECT GUTENBERG"
    ]
    
    lines = text.splitlines()
    start_idx = 0
    end_idx = len(lines)
    
    for i, line in enumerate(lines[:500]):
        if any(re.search(marker, line, re.IGNORECASE) for marker in start_markers):
            start_idx = i + 1
            break
            
    scan_offset = max(0, len(lines) - 1000)
    for i, line in enumerate(lines[scan_offset:]):
        if any(re.search(marker, line, re.IGNORECASE) for marker in end_markers):
            end_idx = scan_offset + i
            break
            
    cleaned_lines = lines[start_idx:end_idx]
    cleaned_text = "\n".join(cleaned_lines).strip()
    
    # Gracefully truncate if the content is longer than the target testing slice
    if len(cleaned_text) > max_characters:
        truncated = cleaned_text[:max_characters]
        last_double_newline = truncated.rfind("\n\n")
        if last_double_newline != -1:
            cleaned_text = truncated[:last_double_newline].strip()
        else:
            last_space = truncated.rfind(" ")
            cleaned_text = truncated[:last_space].strip() + "..."
            
    return cleaned_text


def parse_gutenberg_metadata(text: str) -> tuple[str, str]:
    """Parses Book Title and Author metadata fields from Gutenberg headers."""
    title = "Unknown Title"
    author = "Unknown Author"
    
    title_match = re.search(r"Title:\s*(.+)", text, re.IGNORECASE)
    if title_match:
        title = title_match.group(1).strip()
        
    author_match = re.search(r"Author:\s*(.+)", text, re.IGNORECASE)
    if author_match:
        author = author_match.group(1).strip()
        
    return title, author


def download_gutenberg_book(book_id: int) -> Optional[str]:
    """Downloads raw textbook content directly from Project Gutenberg's primary cache mirror."""
    url = f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt"
    logger.info(f"Downloading raw textbook stream from Project Gutenberg mirror: {url}")
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.text
        logger.error(f"Failed to fetch content from cache server. Status Code: {response.status_code}")
        return None
    except Exception as e:
        logger.error(f"Network request connection failed: {e}")
        return None


def add_story_to_db(db_path: str, title: str, author: str, content: str) -> None:
    """Inserts a successfully fetched and normalized source story into the target SQLite database."""
    query = "INSERT INTO source_stories (title, author, content, used) VALUES (?, ?, ?, 0);"
    try:
        with sqlite3.connect(db_path) as conn:
            with conn:
                conn.execute(query, (title, author, content))
        logger.info(f"Successfully database-imported '{title}' by {author} ({len(content)} characters).")
    except Exception as e:
        logger.error(f"Failed to insert source text into database: {e}", exc_info=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Directly download and seed Project Gutenberg texts into the ThrobbinHood database")
    parser.add_argument("--db", default="database/stories.db", help="Path to SQLite database")
    parser.add_argument("--preset", choices=list(PRESETS.keys()), help="Select a high-utility curated book preset")
    parser.add_argument("--id", type=int, help="Specify a custom Gutenberg Book ID (e.g. 84 for Frankenstein)")
    parser.add_argument("--max-len", type=int, default=12000, help="Maximum character length to import for testing (~2000 words)")
    
    args = parser.parse_args()
    
    book_id = None
    if args.preset:
        book_id = PRESETS[args.preset]
        logger.info(f"Resolving preset '{args.preset}' to Gutenberg Book ID {book_id}")
    elif args.id:
        book_id = args.id
        
    if not book_id:
        logger.error("You must provide either a valid --preset name or a custom Gutenberg --id to import a story.")
        return

    # Create directories if missing
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)

    raw_text = download_gutenberg_book(book_id)
    if not raw_text:
        logger.error("Terminating seed process: Source content could not be retrieved.")
        return
        
    title, author = parse_gutenberg_metadata(raw_text)
    cleaned_content = clean_gutenberg_content(raw_text, max_characters=args.max_len)
    
    if len(cleaned_content) < 100:
        logger.error("Cleaned text stream length is too short to be viable for pipeline mutation testing.")
        return
        
    add_story_to_db(args.db, title, author, cleaned_content)


if __name__ == "__main__":
    main()