-- Schéma initial du corpus indexé (PLAN § 4.2, D14, SPEC § 4.5).
CREATE EXTENSION IF NOT EXISTS vector;

-- Version du corpus indexée par élection (sert à la clé du cache du chat, SPEC § 6.2 bis).
CREATE TABLE corpus_versions (
    election_id    text PRIMARY KEY,
    corpus_version text NOT NULL CHECK (corpus_version ~ '^[0-9a-f]{16}$'),
    indexed_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE chunks (
    election_id     text NOT NULL,
    id              text NOT NULL,
    candidate_id    text NOT NULL,
    document_title  text NOT NULL,
    source_url      text NOT NULL,
    document_sha256 text NOT NULL,
    page_number     integer NOT NULL CHECK (page_number >= 1),
    page_end        integer NOT NULL CHECK (page_end >= page_number),
    section_title   text,
    text            text NOT NULL,
    token_count     integer NOT NULL,
    corpus_version  text NOT NULL,
    -- Plein texte français sur le titre de section et le texte.
    tsv tsvector GENERATED ALWAYS AS (
        to_tsvector('french', coalesce(section_title, '') || ' ' || text)
    ) STORED,
    PRIMARY KEY (election_id, id)
);
CREATE INDEX chunks_candidate ON chunks (election_id, candidate_id);
CREATE INDEX chunks_tsv ON chunks USING gin (tsv);

-- Un vecteur par (extrait, modèle) : plusieurs modèles coexistent pour la comparaison M4.
-- Le thème dépend du modèle (similarité aux descriptions de thèmes, D16) : il est rangé ici.
CREATE TABLE chunk_embeddings (
    election_id text NOT NULL,
    chunk_id    text NOT NULL,
    model       text NOT NULL,
    theme       text,
    embedding   vector(1024) NOT NULL,
    PRIMARY KEY (election_id, chunk_id, model),
    FOREIGN KEY (election_id, chunk_id) REFERENCES chunks (election_id, id) ON DELETE CASCADE
);
CREATE INDEX chunk_embeddings_bge_m3 ON chunk_embeddings
    USING hnsw (embedding vector_cosine_ops) WHERE model = 'bge-m3';
CREATE INDEX chunk_embeddings_e5_large ON chunk_embeddings
    USING hnsw (embedding vector_cosine_ops) WHERE model = 'multilingual-e5-large';
