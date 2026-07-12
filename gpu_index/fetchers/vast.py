import logging
from collections import defaultdict
from typing import Any

import httpx

from gpu_index.models import PriceSnapshot

logger = logging.getLogger(__name__)

VAST_BUNDLES_URL = "https://console.vast.ai/api/v0/bundles/"

SEARCH_TYPES = [
    ("ondemand", "ondemand"),
    ("bid", "bid"),
]


def _search_offers(
    client: httpx.Client,
    api_key: str,
    instance_type: str,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    payload = {
        "limit": limit,
        "type": instance_type,
        "verified": {"eq": True},
        "rentable": {"eq": True},
        "num_gpus": {"eq": 1},
        "order": [["dph_total", "asc"]],
    }

    response = client.post(
        VAST_BUNDLES_URL,
        json=payload,
        headers={"Authorization": f"Bearer {api_key}"},
    )
    response.raise_for_status()
    data = response.json()
    return data.get("offers") or []


def _request_with_retry(
    api_key: str,
    instance_type: str,
    max_attempts: int = 2,
) -> list[dict[str, Any]]:
    last_error: Exception | None = None
    for attempt in range(max_attempts):
        try:
            with httpx.Client(timeout=30.0) as client:
                return _search_offers(client, api_key, instance_type)
        except Exception as exc:
            last_error = exc
            if attempt < max_attempts - 1:
                logger.warning(
                    "Vast.ai request failed (type=%s, attempt %d): %s",
                    instance_type,
                    attempt + 1,
                    exc,
                )
    raise RuntimeError(
        f"Vast.ai fetch failed for type={instance_type} after {max_attempts} attempts"
    ) from last_error


def _aggregate_offers(
    offers: list[dict[str, Any]],
    instance_type: str,
) -> list[PriceSnapshot]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for offer in offers:
        gpu_name = offer.get("gpu_name")
        if not gpu_name:
            continue
        grouped[gpu_name].append(offer)

    snapshots: list[PriceSnapshot] = []
    for gpu_name, gpu_offers in grouped.items():
        valid = [
            o for o in gpu_offers
            if o.get("dph_total") is not None and o["dph_total"] > 0
        ]
        if not valid:
            continue

        best = min(valid, key=lambda o: o["dph_total"])
        gpu_ram_mb = best.get("gpu_ram")
        memory_gb = gpu_ram_mb / 1024 if gpu_ram_mb else None

        snapshots.append(
            PriceSnapshot(
                provider="vast",
                gpu_id=gpu_name,
                display_name=gpu_name,
                memory_gb=memory_gb,
                instance_type=instance_type,
                price_per_hour=float(best["dph_total"]),
                stock_status=str(len(valid)),
                raw_json={
                    "offer_count": len(valid),
                    "best_offer_id": best.get("id"),
                    "dph_base": best.get("dph_base"),
                    "dph_total": best.get("dph_total"),
                    "reliability": best.get("reliability"),
                    "geolocation": best.get("geolocation"),
                },
            )
        )

    return snapshots


def fetch_vast_prices(api_key: str) -> list[PriceSnapshot]:
    snapshots: list[PriceSnapshot] = []
    for api_type, stored_type in SEARCH_TYPES:
        offers = _request_with_retry(api_key, api_type)
        type_snapshots = _aggregate_offers(offers, stored_type)
        snapshots.extend(type_snapshots)
        logger.info(
            "Vast.ai (%s): %d GPU models from %d offers",
            stored_type,
            len(type_snapshots),
            len(offers),
        )

    return snapshots
