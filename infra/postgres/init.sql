-- Executado apenas na primeira inicialização do volume.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Banco separado para a suíte de testes do backend.
CREATE DATABASE zettabytes_test OWNER zettabytes;
\connect zettabytes_test
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
