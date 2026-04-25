# -*- coding: utf-8 -*-
"""Explicit data variants for green logistics scheduling problems."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path

import numpy as np

from .constants import VEHICLE_TYPES
from .data_processing import load_problem_data
from .data_processing.loader import ProblemData, _build_service_nodes


class SplitMode(str, Enum):
    """Supported virtual service-node split modes."""

    DEFAULT = "default_split"
    GREEN_E2_ADAPTIVE = "green_e2_adaptive"


@dataclass(frozen=True)
class ProblemVariant:
    """A loaded problem variant plus split-audit metadata."""

    name: str
    split_mode: SplitMode
    data: ProblemData
    default_service_node_count: int
    service_node_count: int
    green_service_node_count: int
    notes: tuple[str, ...]


def load_problem_variant(
    data_dir: str | Path = ".",
    split_mode: SplitMode | str = SplitMode.DEFAULT,
) -> ProblemVariant:
    """Load official data under an explicit service-node split mode."""

    mode = SplitMode(split_mode)
    base = load_problem_data(data_dir)
    if mode is SplitMode.DEFAULT:
        return ProblemVariant(
            name=mode.value,
            split_mode=mode,
            data=base,
            default_service_node_count=len(base.service_nodes),
            service_node_count=len(base.service_nodes),
            green_service_node_count=int(base.service_nodes["is_green_zone"].sum()),
            notes=("Matches load_problem_data exactly.",),
        )

    return _build_green_e2_adaptive_variant(base, mode)


def _build_green_e2_adaptive_variant(base: ProblemData, mode: SplitMode) -> ProblemVariant:
    e2 = VEHICLE_TYPES["E2"]
    demands = base.customer_demands.copy()
    green_mask = demands["is_green_zone"].astype(bool)
    green_ratio = np.maximum(
        demands.loc[green_mask, "total_weight"].astype(float) / e2.max_weight_kg,
        demands.loc[green_mask, "total_volume"].astype(float) / e2.max_volume_m3,
    )
    demands.loc[green_mask, "split_count"] = np.ceil(green_ratio).astype(int).clip(lower=1)
    demands["split_count"] = demands["split_count"].astype(int)

    service_nodes, node_to_customer = _build_service_nodes(demands)
    data = replace(
        base,
        customer_demands=demands.reset_index(drop=True),
        service_nodes=service_nodes,
        node_to_customer=node_to_customer,
    )
    return ProblemVariant(
        name=mode.value,
        split_mode=mode,
        data=data,
        default_service_node_count=len(base.service_nodes),
        service_node_count=len(service_nodes),
        green_service_node_count=int(service_nodes["is_green_zone"].sum()),
        notes=(
            "Non-green customer split counts match default.",
            "Green customers are split by E2 capacity for Problem 2 candidate routing.",
        ),
    )
