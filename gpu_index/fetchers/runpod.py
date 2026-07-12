import logging
from typing import Any

import httpx

from gpu_index.models import PriceSnapshot

logger = logging.getLogger(__name__)

RUNPOD_GRAPHQL_URL = "https://api.runpod.io/graphql"

GPU_TYPES_QUERY = """
query {
  gpuTypes {
    id
    displayName
    memoryInGb
    secureCloud
    communityCloud
    securePrice
    communityPrice
    secureSpotPrice
    communitySpotPrice
    lowestPrice(input: { gpuCount: 1 }) {
      uninterruptablePrice
      minimumBidPrice
      stockStatus
    }
  }
}
"""

PRICE_FIELDS = [
    ("secure", "securePrice"),
    ("community", "communityPrice"),
    ("secure_spot", "secureSpotPrice"),
    ("community_spot", "communitySpotPrice"),
]


def _request_with_retry(
    client: httpx.Client,
    api_key: str,
    max_attempts: int = 2,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(max_attempts):
        try:
            response = client.post(
                RUNPOD_GRAPHQL_URL,
                json={"query": GPU_TYPES_QUERY},
                headers={"Authorization": f"Bearer {api_key}"},
            )
            response.raise_for_status()
            data = response.json()
            if "errors" in data:
                raise RuntimeError(f"RunPod GraphQL errors: {data['errors']}")
            return data["data"]
        except Exception as exc:
            last_error = exc
            if attempt < max_attempts - 1:
                logger.warning("RunPod request failed (attempt %d): %s", attempt + 1, exc)
    raise RuntimeError(f"RunPod fetch failed after {max_attempts} attempts") from last_error


def _normalize_gpu(gpu: dict[str, Any]) -> list[PriceSnapshot]:
    snapshots: list[PriceSnapshot] = []
    gpu_id = gpu["id"]
    display_name = gpu.get("displayName")
    memory_gb = gpu.get("memoryInGb")
    lowest = gpu.get("lowestPrice") or {}

    raw_base = {
        "lowestPrice": lowest,
        "secureCloud": gpu.get("secureCloud"),
        "communityCloud": gpu.get("communityCloud"),
    }

    for instance_type, field_name in PRICE_FIELDS:
        price = gpu.get(field_name)
        if price is None or price <= 0:
            continue
        snapshots.append(
            PriceSnapshot(
                provider="runpod",
                gpu_id=gpu_id,
                display_name=display_name,
                memory_gb=memory_gb,
                instance_type=instance_type,
                price_per_hour=float(price),
                stock_status=lowest.get("stockStatus"),
                raw_json={**raw_base, "priceField": field_name, "price": price},
            )
        )

    return snapshots


def fetch_runpod_prices(api_key: str) -> list[PriceSnapshot]:
    with httpx.Client(timeout=30.0) as client:
        data = _request_with_retry(client, api_key)

    gpu_types = data.get("gpuTypes") or []
    snapshots: list[PriceSnapshot] = []
    for gpu in gpu_types:
        snapshots.extend(_normalize_gpu(gpu))

    logger.info("RunPod: fetched %d price snapshots from %d GPU types", len(snapshots), len(gpu_types))
    return snapshots
