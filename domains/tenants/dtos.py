from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TenantDTO:
    id: str
    name: str
    slug: str
    is_active: bool = True
    schema_name: str = ""


@dataclass
class TenantConfigDTO:
    id: str
    tenant_id: str
    sla_hours_low: int = 72
    sla_hours_medium: int = 24
    sla_hours_high: int = 4
    classification_threshold: float = 0.4
    max_tickets_per_agent: int = 20
