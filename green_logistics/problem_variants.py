# -*- coding: utf-8 -*-
"""Explicit data variants for green logistics scheduling problems."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from math import ceil
from pathlib import Path

import numpy as np
import pandas as pd

from .constants import VEHICLE_TYPES
from .data_processing import load_problem_data
from .data_processing.loader import ProblemData, _build_service_nodes


class SplitMode(str, Enum):
    """Supported virtual service-node split modes."""

    DEFAULT = "default_split"
    GREEN_E2_ADAPTIVE = "green_e2_adaptive"
    GREEN_HOTSPOT_PARTIAL = "green_hotspot_partial"


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

    if mode is SplitMode.GREEN_E2_ADAPTIVE:
        return _build_green_e2_adaptive_variant(base, mode)
    return _build_green_hotspot_partial_variant(base, mode)


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


def _build_green_hotspot_partial_variant(base: ProblemData, mode: SplitMode) -> ProblemVariant:
    hotspot_e2_chunks = {6: 1, 7: 1, 8: 2, 11: 1}
    demands = base.customer_demands.copy()
    service_nodes, node_to_customer, split_counts = _build_hotspot_partial_service_nodes(
        demands,
        hotspot_e2_chunks=hotspot_e2_chunks,
    )
    demands["split_count"] = demands["customer_id"].astype(int).map(split_counts).astype(int)
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
            "Non-hotspot customer split counts match default.",
            "Green hotspot customers receive a few E2-sized chunks plus E1-sized residual chunks.",
            f"Hotspot E2 chunks: {hotspot_e2_chunks}.",
        ),
    )


def _build_hotspot_partial_service_nodes(
    demands: pd.DataFrame,
    *,
    hotspot_e2_chunks: dict[int, int],
) -> tuple[pd.DataFrame, dict[int, int], dict[int, int]]:
    rows: list[dict[str, object]] = []
    node_to_customer: dict[int, int] = {}
    split_counts: dict[int, int] = {}
    next_node_id = 1

    for row in demands.itertuples(index=False):
        customer_id = int(row.customer_id)
        total_weight = float(row.total_weight)
        total_volume = float(row.total_volume)
        if bool(row.is_green_zone) and customer_id in hotspot_e2_chunks:
            chunks = _hotspot_partial_chunks(
                total_weight,
                total_volume,
                e2_chunk_count=hotspot_e2_chunks[customer_id],
            )
        else:
            split_count = int(row.split_count)
            chunks = [(total_weight / split_count, total_volume / split_count)] * split_count

        split_counts[customer_id] = len(chunks)
        for split_index, (weight, volume) in enumerate(chunks, start=1):
            rows.append(
                {
                    "node_id": next_node_id,
                    "customer_id": customer_id,
                    "split_index": split_index,
                    "split_count": len(chunks),
                    "demand_weight": float(weight),
                    "demand_volume": float(volume),
                    "earliest_min": int(row.earliest_min),
                    "latest_min": int(row.latest_min),
                    "is_green_zone": bool(row.is_green_zone),
                }
            )
            node_to_customer[next_node_id] = customer_id
            next_node_id += 1

    return pd.DataFrame(rows), node_to_customer, split_counts


def _hotspot_partial_chunks(
    total_weight: float,
    total_volume: float,
    *,
    e2_chunk_count: int,
) -> list[tuple[float, float]]:
    e1 = VEHICLE_TYPES["E1"]
    e2 = VEHICLE_TYPES["E2"]
    remaining_weight = float(total_weight)
    remaining_volume = float(total_volume)
    chunks: list[tuple[float, float]] = []

    for _ in range(max(0, int(e2_chunk_count))):
        if remaining_weight <= 1e-9 and remaining_volume <= 1e-9:
            break
        scale = min(
            1.0,
            e2.max_weight_kg / remaining_weight if remaining_weight > 1e-9 else 1.0,
            e2.max_volume_m3 / remaining_volume if remaining_volume > 1e-9 else 1.0,
        )
        chunk_weight = remaining_weight * scale
        chunk_volume = remaining_volume * scale
        chunks.append((chunk_weight, chunk_volume))
        remaining_weight -= chunk_weight
        remaining_volume -= chunk_volume

    if remaining_weight > 1e-9 or remaining_volume > 1e-9:
        residual_count = int(ceil(max(remaining_weight / e1.max_weight_kg, remaining_volume / e1.max_volume_m3)))
        residual_count = max(1, residual_count)
        for _ in range(residual_count):
            chunks.append((remaining_weight / residual_count, remaining_volume / residual_count))

    return chunks
