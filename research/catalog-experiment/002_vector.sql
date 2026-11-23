CREATE EXTENSION IF NOT EXISTS vector;
ALTER TABLE catalog_eval.product ADD COLUMN IF NOT EXISTS embedding vector(128);
CREATE INDEX IF NOT EXISTS catalog_eval_hnsw ON catalog_eval.product
USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
