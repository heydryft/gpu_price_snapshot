from datetime import datetime, timedelta
import re
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from gpu_index.config import Config
from gpu_index.db import get_connection, get_latest_prices, get_recent_prices

app = FastAPI(title="GPU Index API")

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GpuPrice(BaseModel):
    provider: str
    gpu_id: str
    display_name: str | None
    memory_gb: float | None
    instance_type: str
    price_per_hour: float
    stock_status: str | None
    fetched_at: datetime


# List of verified/common GPU models to focus on
VERIFIED_GPUS = {
    "H100", "H100 NVL", "H200", "A100 80GB", "A100 40GB", "A100",
    "RTX 6000 Ada", "RTX A6000", "RTX A5000", "RTX A4000", "A40",
    "RTX 4090", "RTX 4090 Ti", "RTX 4080", "RTX 4080 Super",
    "RTX 4070", "RTX 4070 Ti", "RTX 4070 Super", "RTX 3090",
    "RTX 3090 Ti", "RTX 3080", "RTX 3080 Ti", "RTX 3070",
    "RTX 3070 Ti", "MI300X", "MI250X", "MI210", "MI200", "L40S",
    "L40", "V100 32GB", "V100 16GB", "V100",
}


def canonical_gpu_name(
    display_name: str | None,
    gpu_id: str | None,
    memory_gb: float | None,
) -> str:
    name = (display_name or gpu_id or "Unknown").upper()
    name = re.sub(r"\bNVIDIA\b|\bGEFORCE\b|\bTESLA\b", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    compact = re.sub(r"[^A-Z0-9]", "", name)

    if "H100NVL" in compact:
        return "H100 NVL"
    if "H200" in compact:
        return "H200"
    if "H100" in compact:
        return "H100"
    if "A100" in compact:
        if "80GB" in compact or (memory_gb is not None and memory_gb >= 70):
            return "A100 80GB"
        if "40GB" in compact or (memory_gb is not None and 35 <= memory_gb < 70):
            return "A100 40GB"
        return "A100"
    if "RTX6000ADA" in compact or "6000ADA" in compact:
        return "RTX 6000 Ada"
    if "RTXA6000" in compact or compact == "A6000":
        return "RTX A6000"
    if "RTXA5000" in compact or compact == "A5000":
        return "RTX A5000"
    if "RTXA4000" in compact or compact == "A4000":
        return "RTX A4000"
    if compact == "A40" or compact == "RTXA40":
        return "A40"
    if "L40S" in compact:
        return "L40S"
    if compact == "L40":
        return "L40"
    if "V100" in compact:
        if memory_gb is not None and memory_gb >= 28:
            return "V100 32GB"
        if memory_gb is not None and memory_gb >= 14:
            return "V100 16GB"
        return "V100"
    for series in ("4090", "4080", "4070", "3090", "3080", "3070"):
        if series in compact:
            suffix = ""
            if "TI" in compact:
                suffix = " Ti"
            elif "SUPER" in compact or compact.endswith("S"):
                suffix = " Super"
            return f"RTX {series}{suffix}"
    for model in ("MI300X", "MI250X", "MI210", "MI200"):
        if model in compact:
            return model
    return (display_name or gpu_id or "Unknown").strip()


def is_verified_gpu(
    display_name: str | None,
    gpu_id: str | None,
    memory_gb: float | None = None,
) -> bool:
    """Check if GPU is in the verified list"""
    return canonical_gpu_name(display_name, gpu_id, memory_gb) in VERIFIED_GPUS


def with_canonical_name(price: dict[str, Any]) -> dict[str, Any]:
    result = dict(price)
    result["canonical_name"] = canonical_gpu_name(
        price.get("display_name"),
        price.get("gpu_id"),
        price.get("memory_gb"),
    )
    return result


def price_metric(
    runpod: list[dict[str, Any]],
    vast: list[dict[str, Any]],
    runpod_types: set[str],
    vast_types: set[str],
) -> dict[str, Any] | None:
    runpod_prices = [
        row["price_per_hour"] for row in runpod
        if row["instance_type"] in runpod_types
    ]
    vast_prices = [
        row["price_per_hour"] for row in vast
        if row["instance_type"] in vast_types
    ]
    if not runpod_prices or not vast_prices:
        return None
    runpod_price = min(runpod_prices)
    vast_price = min(vast_prices)
    difference = abs(runpod_price - vast_price)
    baseline = max(runpod_price, vast_price)
    return {
        "runpod_price": runpod_price,
        "vast_price": vast_price,
        "difference_per_hour": difference,
        "difference_percent": (difference / baseline * 100) if baseline else 0,
        "cheaper_provider": "runpod" if runpod_price < vast_price else "vast",
    }


@app.get("/api/gpus/latest")
def get_latest_gpu_prices() -> dict[str, Any]:
    """Get latest GPU prices, filtered to verified models"""
    config = Config.from_env()
    
    with get_connection(config.database_url) as conn:
        all_prices = get_latest_prices(conn)
    
    # Filter to verified GPUs
    verified_prices = [
        with_canonical_name(price) for price in all_prices
        if is_verified_gpu(
            price.get("display_name"),
            price.get("gpu_id"),
            price.get("memory_gb"),
        )
    ]
    provider_counts = {
        provider: sum(1 for price in verified_prices if price["provider"] == provider)
        for provider in ("runpod", "vast")
    }
    
    return {"prices": verified_prices, "provider_counts": provider_counts}


@app.get("/api/gpus/history/{gpu_id}")
def get_gpu_history(gpu_id: str, hours: int = 168) -> dict[str, Any]:
    """Get price history for a specific GPU over the last N hours (default 7 days)"""
    config = Config.from_env()
    cutoff = datetime.now() - timedelta(hours=hours)
    
    with get_connection(config.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    gm.provider,
                    gm.gpu_id,
                    gm.display_name,
                    ps.instance_type,
                    ps.price_per_hour,
                    ps.stock_status,
                    ps.fetched_at
                FROM price_snapshots ps
                JOIN gpu_models gm ON gm.id = ps.gpu_model_id
                WHERE gm.gpu_id = %s
                    AND ps.fetched_at >= %s
                ORDER BY ps.fetched_at ASC
                """,
                (gpu_id, cutoff),
            )
            history = cur.fetchall()
    
    return {"gpu_id": gpu_id, "history": history}


@app.get("/api/gpus/compare")
def compare_providers() -> dict[str, Any]:
    """Compare prices between RunPod and Vast for common GPUs"""
    config = Config.from_env()
    
    with get_connection(config.database_url) as conn:
        all_prices = get_latest_prices(conn)
    
    # Group by GPU name
    gpu_comparison: dict[str, dict[str, Any]] = {}
    for raw_price in all_prices:
        price = with_canonical_name(raw_price)
        canonical_name = price["canonical_name"]
        if canonical_name not in VERIFIED_GPUS:
            continue
        if canonical_name not in gpu_comparison:
            gpu_comparison[canonical_name] = {
                "canonical_name": canonical_name,
                "display_name": canonical_name,
                "memory_gb": price.get("memory_gb"),
                "runpod": [],
                "vast": [],
            }
        provider = price.get("provider")
        if provider in ("runpod", "vast"):
            gpu_comparison[canonical_name][provider].append(price)
    
    # Filter to GPUs available on both platforms or verified
    comparison_list = []
    for gpu in gpu_comparison.values():
        if not gpu["runpod"] or not gpu["vast"]:
            continue
        gpu["on_demand"] = price_metric(
            gpu["runpod"],
            gpu["vast"],
            {"secure", "community"},
            {"ondemand"},
        )
        gpu["interruptible"] = price_metric(
            gpu["runpod"],
            gpu["vast"],
            {"secure_spot", "community_spot"},
            {"bid"},
        )
        if gpu["on_demand"] or gpu["interruptible"]:
            comparison_list.append(gpu)
    comparison_list.sort(key=lambda gpu: gpu["canonical_name"])
    
    return {"comparison": comparison_list}


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy"}
