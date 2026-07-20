CREATE TABLE IF NOT EXISTS classifications (
    id INTEGER,
    filename TEXT,
    hash TEXT,
    description TEXT,
    PRIMARY KEY("id" AUTOINCREMENT)
);

CREATE TABLE IF NOT EXISTS embeddings (
    id INTEGER,
    classification_id INTEGER,
    embedding BLOB NOT NULL,
    PRIMARY KEY("id" AUTOINCREMENT),
    FOREIGN KEY(classification_id) REFERENCES classifications(id)
);
