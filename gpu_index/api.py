import re
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gpu_index.config import Config
from gpu_index.db import get_connection, get_latest_prices

app = FastAPI(title="GPU Index API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Canonical name normalization
# ---------------------------------------------------------------------------

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
    return canonical_gpu_name(display_name, gpu_id, memory_gb) in VERIFIED_GPUS


def enrich(price: dict[str, Any]) -> dict[str, Any]:
    result = dict(price)
    result["canonical_name"] = canonical_gpu_name(
        price.get("display_name"),
        price.get("gpu_id"),
        price.get("memory_gb"),
    )
    return result


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/gpus/latest")
def get_latest_gpu_prices() -> dict[str, Any]:
    """All verified GPU prices from each provider's latest fetch."""
    config = Config.from_env()

    with get_connection(config.database_url) as conn:
        all_prices = get_latest_prices(conn)

    verified = [
        enrich(p) for p in all_prices
        if is_verified_gpu(p.get("display_name"), p.get("gpu_id"), p.get("memory_gb"))
    ]

    return {"prices": verified}


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy"}
