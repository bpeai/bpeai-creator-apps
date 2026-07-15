from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field

EquipmentSystem = Literal[
    "mixing",
    "heat_transfer",
    "cell_culture",
    "chromatography",
    "fluid_transfer",
    "filtration",
    "valves_fittings",
]

AppKind = Literal["first_party", "creator"]
AppRuntime = Literal["server"]
AppStatus = Literal["draft", "review", "published", "deprecated"]
AccountTier = Literal["FREE", "INDIVIDUAL", "TEAM", "PROFESSIONAL", "VENDOR", "ADMIN"]


class CreatorAppAuthor(BaseModel):
    creator_id: str
    display_name: str


class CreatorAppManifest(BaseModel):
    id: str
    slug: str
    label: str
    description: str = ""
    equipment_system: EquipmentSystem
    equipment_subtypes: List[str] = Field(default_factory=list)
    author: CreatorAppAuthor
    app_kind: AppKind = "first_party"
    output_schema_version: Literal["equipment_selector_v1"] = "equipment_selector_v1"
    required_inputs: List[str] = Field(default_factory=list)
    route: str
    runtime: AppRuntime = "server"
    min_tier: AccountTier = "INDIVIDUAL"
    status: AppStatus = "published"
    python_entrypoint: str = ""
