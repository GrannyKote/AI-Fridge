CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE SCHEMA IF NOT EXISTS catalog_eval;
CREATE TABLE IF NOT EXISTS catalog_eval.product (
    id integer PRIMARY KEY,
    name text NOT NULL,
    key text NOT NULL,
    document tsvector GENERATED ALWAYS AS (to_tsvector('russian', key)) STORED
);
CREATE INDEX IF NOT EXISTS catalog_eval_prefix ON catalog_eval.product (lower(name) text_pattern_ops);
CREATE INDEX IF NOT EXISTS catalog_eval_key ON catalog_eval.product (key);
CREATE INDEX IF NOT EXISTS catalog_eval_trgm ON catalog_eval.product USING gist (key gist_trgm_ops);
CREATE INDEX IF NOT EXISTS catalog_eval_fts ON catalog_eval.product USING gin (document);
