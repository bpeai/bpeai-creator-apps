from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field, model_validator

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
PortKind = Literal["value", "artifact"]
PortCardinality = Literal["one", "many"]


class CreatorAppAuthor(BaseModel):
    creator_id: str
    display_name: str


class CreatorAppPort(BaseModel):
    """A typed input or output exposed to the EI workflow runtime."""

    id: str
    label: str
    schema_ref: str
    data_type: str = "any"
    required: bool = True
    cardinality: PortCardinality = "one"
    kind: PortKind = "value"


class CreatorAppManifest(BaseModel):
    id: str
    slug: str
    label: str
    description: str = ""
    equipment_system: EquipmentSystem
    knowledge_pack: str = ""
    equipment_subtypes: List[str] = Field(default_factory=list)
    author: CreatorAppAuthor
    app_kind: AppKind = "first_party"
    template_family: str = "equipment_evaluator"
    output_schema_version: Literal["equipment_selector_v1"] = "equipment_selector_v1"
    required_inputs: List[str] = Field(default_factory=list)
    input_ports: List[CreatorAppPort] = Field(default_factory=list)
    output_ports: List[CreatorAppPort] = Field(default_factory=list)
    route: str
    runtime: AppRuntime = "server"
    min_tier: AccountTier = "INDIVIDUAL"
    status: AppStatus = "published"
    python_entrypoint: str = ""

    @model_validator(mode="after")
    def _bridge_legacy_required_inputs(self) -> "CreatorAppManifest":
        """Keep old manifests usable while making their inputs discoverable."""
        if not self.input_ports and self.required_inputs:
            self.input_ports = [
                CreatorAppPort(
                    id=input_id,
                    label=input_id.replace("_", " ").title(),
                    schema_ref="https://bpeai.com/schemas/value/json/v1",
                )
                for input_id in self.required_inputs
            ]
        if not self.required_inputs and self.input_ports:
            self.required_inputs = [port.id for port in self.input_ports if port.required]
        return self
