from dataclasses import dataclass, field
from typing import Any


@dataclass
class GpuModel:
    provider: str
    gpu_id: str
    display_name: str | None = None
    memory_gb: float | None = None


@dataclass
class PriceSnapshot:
    provider: str
    gpu_id: str
    instance_type: str
    price_per_hour: float
    stock_status: str | None = None
    raw_json: dict[str, Any] = field(default_factory=dict)
    display_name: str | None = None
    memory_gb: float | None = None
