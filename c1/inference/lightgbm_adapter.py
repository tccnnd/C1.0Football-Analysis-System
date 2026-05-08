from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .schema import InferenceComponent, InferenceInput


@dataclass(slots=True)
class LightGBMAvailability:
    available: bool
    reason: str


class C1LightGBMAdapter:
    def get_availability(self) -> LightGBMAvailability:
        return LightGBMAvailability(available=False, reason="not_implemented_phase4")

    def infer(self, inference_input: InferenceInput) -> InferenceComponent:
        availability = self.get_availability()
        return InferenceComponent(
            name="lightgbm",
            probabilities={"home": 0.0, "draw": 0.0, "away": 0.0},
            metadata={
                "available": availability.available,
                "reason": availability.reason,
                "match_id": inference_input.match_id,
            },
        )

