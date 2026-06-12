CREATE TABLE source_stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    gutenberg_id INTEGER,
    source_title TEXT NOT NULL,
    source_author TEXT,
    source_url TEXT NOT NULL,

    language TEXT,
    word_count INTEGER,

    status TEXT DEFAULT 'available',

    imported_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE generated_stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    source_story_id INTEGER,

    generated_title TEXT NOT NULL,
    slug TEXT UNIQUE,

    genre TEXT,
    series TEXT,

    summary TEXT,

    markdown_path TEXT,

    published BOOLEAN DEFAULT FALSE,

    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);