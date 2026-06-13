# scripts/import_gutenberg.py

import argparse
import logging
import re
import sqlite3
from pathlib import Path

logger = logging.getLogger("ThrobbinHood.import_gutenberg")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def clean_gutenberg_text(text: str, max_characters: int = 25000) -> str:
    """Removes boilerplate, extracts a clean seed window, and cuts safely at a paragraph break."""
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
    full_cleaned_text = "\n".join(cleaned_lines).strip()
    
    # If the text exceeds our maximum context allocation window, truncate it safely
    if len(full_cleaned_text) > max_characters:
        logger.info(f"Text length ({len(full_cleaned_text)}) exceeds max limit ({max_characters}). Executing graceful boundary slicing.")
        truncated_subset = full_cleaned_text[:max_characters]
        
        # Locate the last clean double-newline to avoid clipping a sentence or paragraph mid-thought
        last_paragraph = truncated_subset.rfind("\n\n")
        if last_paragraph != -1:
            full_cleaned_text = truncated_subset[:last_paragraph].strip()
        else:
            # Fallback to last space if no paragraph break is found nearby
            last_space = truncated_subset.rfind(" ")
            full_cleaned_text = truncated_subset[:last_space].strip() + "..."
            
    return full_cleaned_text


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


def import_file(db_path: str, file_path: Path, min_length: int = 5000, max_length: int = 25000) -> None:
    """Normalizes encoding, cleans, downsamples, and imports a Gutenberg text file into the DB."""
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
    cleaned_content = clean_gutenberg_text(raw_content, max_characters=max_length)
    
    if len(cleaned_content) < min_length:
        logger.warning(f"Skipping {file_path}: cleaned content length ({len(cleaned_content)}) below threshold {min_length}")
        return

    query = "INSERT INTO source_stories (title, author, content) VALUES (?, ?, ?);"
    try:
        with sqlite3.connect(db_path) as conn:
            with conn:
                conn.execute(query, (title, author, cleaned_content))
        logger.info(f"Successfully imported downsampled version of '{title}' by {author} ({len(cleaned_content)} chars)")
    except Exception as e:
        logger.error(f"Failed to insert story into database: {e}", exc_info=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Project Gutenberg texts into ThrobbinHood DB with size normalization")
    parser.add_argument("--db", default="database/stories.db", help="Path to SQLite database")
    parser.add_argument("--source", required=True, help="Path to file or directory containing Gutenberg TXT files")
    parser.add_argument("--min-len", type=int, default=5000, help="Minimum text character length threshold")
    parser.add_argument("--max-len", type=int, default=25000, help="Maximum text character length window limit (~4000 words)")
    
    args = parser.parse_args()
    source_path = Path(args.source)
    
    if source_path.is_file():
        import_file(args.db, source_path, args.min_len, args.max_len)
    elif source_path.is_dir():
        for txt_file in source_path.glob("**/*.txt"):
            import_file(args.db, txt_file, args.min_len, args.max_len)
    else:
        logger.error(f"Provided source path does not exist or is invalid: {source_path}")


if __name__ == "__main__":
    main()