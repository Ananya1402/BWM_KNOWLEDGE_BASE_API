-- Enable pgvector extension for PostgreSQL
-- Run this as superuser (postgres) before running Alembic migrations

-- Connect to your database
\c rag_kb

-- Enable the vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Verify extensions are installed
SELECT * FROM pg_extension WHERE extname IN ('vector', 'uuid-ossp');

-- Show version info
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
