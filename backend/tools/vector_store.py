"""pgvector-backed research cache (RAG).

Stores every web-research finding as an embedding in Postgres (Supabase/Neon) so
future briefs can retrieve semantically-related prior research — a cross-session
knowledge base that also cuts repeat Tavily calls.

Fully optional: if DATABASE_URL is unset or anything fails, every function no-ops
so the pipeline is unaffected (same graceful-degradation pattern as Tavily).
"""
import os
from typing import Dict, List

try:
    import psycopg2  # type: ignore
except Exception:  # noqa: BLE001
    psycopg2 = None

from openai import OpenAI

EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536
_schema_ready = False


def enabled() -> bool:
    return bool(os.getenv("DATABASE_URL")) and psycopg2 is not None


def _client() -> OpenAI:
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _connect():
    return psycopg2.connect(os.getenv("DATABASE_URL"), connect_timeout=8)


def _ensure_schema(conn):
    global _schema_ready
    if _schema_ready:
        return
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute(
            f"""CREATE TABLE IF NOT EXISTS research_chunks (
                id bigserial PRIMARY KEY,
                country text, business_type text,
                content text, url text,
                embedding vector({EMBED_DIM}),
                created_at timestamptz DEFAULT now()
            );"""
        )
        # HNSW approximate-nearest-neighbour index. vector_cosine_ops matches the `<=>`
        # (cosine distance) operator used in search(). m / ef_construction are graph build
        # params; query-time recall/speed is tuned via the hnsw.ef_search GUC (default 40).
        # Created on the empty table (instant + idempotent); building it later on a large
        # table would be slow and take a lock.
        cur.execute(
            "CREATE INDEX IF NOT EXISTS research_chunks_embedding_hnsw "
            "ON research_chunks USING hnsw (embedding vector_cosine_ops) "
            "WITH (m = 16, ef_construction = 64);"
        )
    conn.commit()
    _schema_ready = True


def _embed(texts: List[str]) -> List[List[float]]:
    resp = _client().embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]


def _vec(v: List[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


def search(query: str, k: int = 4) -> List[Dict]:
    """Semantic search over prior findings. Returns [] if disabled or on any error."""
    if not enabled() or not query.strip():
        return []
    try:
        conn = _connect()
        try:
            _ensure_schema(conn)
            qv = _vec(_embed([query])[0])
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT content, country, business_type, url, 1 - (embedding <=> %s::vector) AS score "
                    "FROM research_chunks ORDER BY embedding <=> %s::vector LIMIT %s",
                    (qv, qv, k),
                )
                rows = cur.fetchall()
            return [
                {"content": r[0], "country": r[1], "business_type": r[2], "url": r[3], "score": float(r[4])}
                for r in rows
            ]
        finally:
            conn.close()
    except Exception as e:  # noqa: BLE001
        print("WARN vector_store.search:", e)
        return []


def upsert_findings(country: str, business_type: str, findings: List[str], sources: List[Dict] = None) -> int:
    """Embed + store new findings for future retrieval. No-op if disabled."""
    if not enabled() or not findings:
        return 0
    sources = sources or []
    urls = [s.get("url") for s in sources]
    try:
        conn = _connect()
        try:
            _ensure_schema(conn)
            embs = _embed(findings)
            with conn.cursor() as cur:
                for i, (f, e) in enumerate(zip(findings, embs)):
                    url = urls[i] if i < len(urls) else None
                    cur.execute(
                        "INSERT INTO research_chunks (country, business_type, content, url, embedding) "
                        "VALUES (%s, %s, %s, %s, %s::vector)",
                        (country, business_type, f, url, _vec(e)),
                    )
            conn.commit()
            return len(findings)
        finally:
            conn.close()
    except Exception as e:  # noqa: BLE001
        print("WARN vector_store.upsert_findings:", e)
        return 0
