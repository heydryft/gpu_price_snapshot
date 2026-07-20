from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Generator

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from gpu_index.models import PriceSnapshot

SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS gpu_models (
        id SERIAL PRIMARY KEY,
        provider TEXT NOT NULL,
        gpu_id TEXT NOT NULL,
        display_name TEXT,
        memory_gb DOUBLE PRECISION,
        UNIQUE(provider, gpu_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS price_snapshots (
        id SERIAL PRIMARY KEY,
        gpu_model_id INTEGER NOT NULL REFERENCES gpu_models(id),
        fetched_at TIMESTAMPTZ NOT NULL,
        instance_type TEXT NOT NULL,
        price_per_hour DOUBLE PRECISION NOT NULL,
        currency TEXT DEFAULT 'USD',
        stock_status TEXT,
        raw_json JSONB,
        UNIQUE(gpu_model_id, fetched_at, instance_type)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_snapshots_fetched
    ON price_snapshots(fetched_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_snapshots_gpu
    ON price_snapshots(gpu_model_id)
    """,
]


@contextmanager
def get_connection(database_url: str) -> Generator[psycopg.Connection[Any], None, None]:
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        yield conn


def init_db(database_url: str) -> None:
    with get_connection(database_url) as conn:
        with conn.cursor() as cur:
            for statement in SCHEMA_STATEMENTS:
                cur.execute(statement)
        conn.commit()


def upsert_gpu_model(
    cur: psycopg.Cursor[Any],
    provider: str,
    gpu_id: str,
    display_name: str | None,
    memory_gb: float | None,
) -> int:
    cur.execute(
        """
        INSERT INTO gpu_models (provider, gpu_id, display_name, memory_gb)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT(provider, gpu_id) DO UPDATE SET
            display_name = COALESCE(EXCLUDED.display_name, gpu_models.display_name),
            memory_gb = COALESCE(EXCLUDED.memory_gb, gpu_models.memory_gb)
        RETURNING id
        """,
        (provider, gpu_id, display_name, memory_gb),
    )
    row = cur.fetchone()
    if row is None:
        raise RuntimeError(f"Failed to upsert gpu_model {provider}/{gpu_id}")
    return row["id"]


def save_snapshots(
    conn: psycopg.Connection[Any],
    snapshots: list[PriceSnapshot],
    fetched_at: datetime | None = None,
) -> int:
    if fetched_at is None:
        fetched_at = datetime.now(timezone.utc)

    fetched_at = fetched_at.replace(microsecond=0)
    saved = 0

    with conn.cursor() as cur:
        for snap in snapshots:
            gpu_model_id = upsert_gpu_model(
                cur,
                snap.provider,
                snap.gpu_id,
                snap.display_name,
                snap.memory_gb,
            )
            cur.execute(
                """
                INSERT INTO price_snapshots (
                    gpu_model_id, fetched_at, instance_type,
                    price_per_hour, stock_status, raw_json
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (gpu_model_id, fetched_at, instance_type) DO NOTHING
                """,
                (
                    gpu_model_id,
                    fetched_at,
                    snap.instance_type,
                    snap.price_per_hour,
                    snap.stock_status,
                    Jsonb(snap.raw_json) if snap.raw_json else None,
                ),
            )
            saved += cur.rowcount

    conn.commit()
    return saved


def get_latest_prices(conn: psycopg.Connection[Any]) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                gm.provider,
                gm.gpu_id,
                gm.display_name,
                gm.memory_gb,
                ps.instance_type,
                ps.price_per_hour,
                ps.stock_status,
                ps.fetched_at
            FROM price_snapshots ps
            JOIN gpu_models gm ON gm.id = ps.gpu_model_id
            WHERE ps.fetched_at = (
                SELECT MAX(provider_ps.fetched_at)
                FROM price_snapshots provider_ps
                JOIN gpu_models provider_gm
                    ON provider_gm.id = provider_ps.gpu_model_id
                WHERE provider_gm.provider = gm.provider
            )
            ORDER BY gm.provider, gm.display_name, ps.instance_type
            """
        )
        return cur.fetchall()


def get_recent_prices(
    conn: psycopg.Connection[Any],
    limit: int = 100,
) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                gm.provider,
                gm.gpu_id,
                gm.display_name,
                gm.memory_gb,
                ps.instance_type,
                ps.price_per_hour,
                ps.stock_status,
                ps.fetched_at
            FROM price_snapshots ps
            JOIN gpu_models gm ON gm.id = ps.gpu_model_id
            ORDER BY ps.fetched_at DESC, gm.provider, gm.display_name
            LIMIT %s
            """,
            (limit,),
        )
        return cur.fetchall()
