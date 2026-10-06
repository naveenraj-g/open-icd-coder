-- Runs once when the database volume is first initialized.

-- Vector similarity search (Stage 1 semantic retrieval).
CREATE EXTENSION IF NOT EXISTS vector;

-- Trigram matching for fuzzy lexical search on code descriptions (Stage 1 hybrid retrieval).
CREATE EXTENSION IF NOT EXISTS pg_trgm;
