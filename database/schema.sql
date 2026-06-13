-- database/schema.sql

CREATE TABLE IF NOT EXISTS source_stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT,
    content TEXT NOT NULL,
    used INTEGER DEFAULT 0 CHECK (used IN (0, 1)),
    imported_at TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS generated_stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_story_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    summary TEXT NOT NULL,
    genre TEXT NOT NULL,
    series TEXT DEFAULT '',
    tropes TEXT NOT NULL, -- JSON array of strings
    characters TEXT NOT NULL, -- JSON array of objects
    story_text TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (source_story_id) REFERENCES source_stories(id)
);

CREATE INDEX IF NOT EXISTS idx_source_stories_used ON source_stories(used);
CREATE INDEX IF NOT EXISTS idx_generated_stories_slug ON generated_stories(slug);