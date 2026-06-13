# scripts/import_gutenberg.py

import argparse
import logging
import re
import sqlite3
from pathlib import Path

logger = logging.getLogger("ThrobbinHood.import_gutenberg")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def clean_gutenberg_text(text: str) -> str:
    """Removes standard Project Gutenberg headers, footers, and boilerplate legal blocks."""
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
            
    for i, line in enumerate(lines[-1000:]):
        real_idx = len(lines) - 1000 + i
        if any(re.search(marker, line, re.IGNORECASE) for marker in end_markers):
            end_idx = real_idx
            break
            
    cleaned_lines = lines[start_idx:end_idx]
    return "\n".join(cleaned_lines).strip()


def parse_gutenberg_metadata(text: str) -> tuple[str, str]:
    """Extracts Title and Author metadata from the header lines of a Project Gutenberg file."""
    title = "Unknown Title"
    author = "Unknown Author"
    
    title_match = re.search(r"Title:\s*(.+)", text, re.IGNORECASE)
    if title_match:
        title = title_match.group(1).strip()
        
    author_match = re.search(r"Author:\s*(.+)", text, re.IGNORECASE)
    if author_match:
        author = author_match.group(1).strip()
        
    return title, author


def import_file(db_path: str, file_path: Path, min_length: int = 5000) -> None:
    """Normalizes encoding, cleans, parses, and imports a single Gutenberg text file into the DB."""
    logger.info(f"Processing file: {file_path}")
    
    raw_content = ""
    encodings = ["utf-8", "latin-1", "cp1252"]
    for encoding in encodings:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                raw_content = f.read()
            break
        except UnicodeDecodeError:
            continue
            
    if not raw_content:
        logger.error(f"Could not decode file {file_path} with available encodings.")
        return

    title, author = parse_gutenberg_metadata(raw_content)
    cleaned_content = clean_gutenberg_text(raw_content)
    
    if len(cleaned_content) < min_length:
        logger.warning(f"Skipping {file_path}: cleaned content length ({len(cleaned_content)}) below threshold {min_length}")
        return

    query = "INSERT INTO source_stories (title, author, content) VALUES (?, ?, ?);"
    try:
        with sqlite3.connect(db_path) as conn:
            with conn:
                conn.execute(query, (title, author, cleaned_content))
        logger.info(f"Successfully imported '{title}' by {author}")
    except Exception as e:
        logger.error(f"Failed to insert story into database: {e}", exc_info=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Project Gutenberg texts into ThrobbinHood DB")
    parser.add_argument("--db", default="database/stories.db", help="Path to SQLite database")
    parser.add_argument("--source", required=True, help="Path to file or directory containing Gutenberg TXT files")
    parser.add_argument("--min-len", type=int, default=5000, help="Minimum text character length threshold")
    
    args = parser.parse_args()
    source_path = Path(args.source)
    
    if source_path.is_file():
        import_file(args.db, source_path, args.min_len)
    elif source_path.is_dir():
        for txt_file in source_path.glob("**/*.txt"):
            import_file(args.db, txt_file, args.min_len)
    else:
        logger.error(f"Provided source path does not exist or is invalid: {source_path}")


if __name__ == "__main__":
    main()