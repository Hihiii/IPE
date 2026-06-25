from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER_MODULE_MAP = ROOT / "config" / "master-module-map.yaml"

PHASES = [
    "phase_0_config_resolution",
    "phase_1_intent_analysis",
    "phase_2_composition_and_cinematography",
    "phase_3_scene_blueprint",
    "phase_3_1_prompt_package",
    "phase_4_self_review",
    "phase_4_1_cleanup",
    "phase_4_2_z_image_renderer",
    "phase_4_3_delivery_package",
    "phase_5_final_output",
]

PROMPT_PACK_FIELDS = (
    "z_image_positive_prompt",
    "z_image_negative_prompt",
    "suggest_resolution",
)
