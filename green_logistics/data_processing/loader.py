# -*- coding: utf-8 -*-
"""Data loading and preprocessing for the green logistics solver.

The loader converts the four official attachments into a clean `ProblemData`
object: active customers, soft time windows, green-zone flags, and virtual
service nodes for multi-trip delivery.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from ..constants import (
    DEFAULT_SPLIT_VOLUME_M3,
    DEFAULT_SPLIT_WEIGHT_KG,
    GREEN_ZONE_RADIUS_KM,
)


@dataclass(frozen=True)
class ProblemData:
    """Preprocessed data used by downstream routing algorithms."""

    orders: pd.DataFrame
    coordinates: pd.DataFrame
    distance_matrix: pd.DataFrame
    time_windows: pd.DataFrame
    customer_demands: pd.DataFrame
    service_nodes: pd.DataFrame
    node_to_customer: dict[int, int]
    no_order_customer_ids: list[int]
    green_customer_ids: list[int]
    active_green_customer_ids: list[int]


FILE_CANDIDATES = {
    "orders": ("订单信息.xlsx", "orders.xlsx"),
    "coordinates": ("客户坐标信息.xlsx", "coordinates.xlsx"),
    "distance": ("距离矩阵.xlsx", "distance_matrix.xlsx"),
    "time_windows": ("时间窗.xlsx", "time_windows.xlsx"),
}


def parse_hhmm_to_minutes(value: object) -> int:
    """Parse `HH:MM`-like values into absolute minutes from 00:00."""

    if hasattr(value, "hour") and hasattr(value, "minute"):
        return int(value.hour) * 60 + int(value.minute)

    text = str(value).strip()
    if not text:
        raise ValueError("empty time value")
    if " " in text:
        text = text.split()[-1]
    parts = text.split(":")
    if len(parts) < 2:
        raise ValueError(f"expected HH:MM time value, got {value!r}")
    return int(parts[0]) * 60 + int(parts[1])


def load_problem_data(
    data_dir: str | Path = ".",
    *,
    split_weight_kg: float = DEFAULT_SPLIT_WEIGHT_KG,
    split_volume_m3: float = DEFAULT_SPLIT_VOLUME_M3,
) -> ProblemData:
    """Load, validate, aggregate, and split the official logistics data."""

    paths = _discover_files(Path(data_dir))
    orders = _load_orders(paths["orders"])
    coordinates = _load_coordinates(paths["coordinates"])
    distance_matrix = _load_distance_matrix(paths["distance"])
    time_windows = _load_time_windows(paths["time_windows"])

    _validate_raw_frames(orders, coordinates, distance_matrix, time_windows)

    customer_demands = _aggregate_customer_demands(orders)
    all_customer_ids = sorted(
        coordinates.loc[coordinates["node_id"] != 0, "node_id"].astype(int).tolist()
    )
    active_customer_ids = customer_demands["customer_id"].astype(int).tolist()
    no_order_customer_ids = sorted(set(all_customer_ids) - set(active_customer_ids))

    coordinates = _mark_green_zone(coordinates)
    green_customer_ids = sorted(
        coordinates.loc[
            (coordinates["node_id"] != 0) & coordinates["is_green_zone"], "node_id"
        ]
        .astype(int)
        .tolist()
    )
    active_green_customer_ids = sorted(set(green_customer_ids) & set(active_customer_ids))

    customer_demands = _attach_customer_attributes(
        customer_demands,
        coordinates,
        time_windows,
        split_weight_kg,
        split_volume_m3,
    )
    service_nodes, node_to_customer = _build_service_nodes(customer_demands)

    return ProblemData(
        orders=orders,
        coordinates=coordinates,
        distance_matrix=distance_matrix,
        time_windows=time_windows,
        customer_demands=customer_demands,
        service_nodes=service_nodes,
        node_to_customer=node_to_customer,
        no_order_customer_ids=no_order_customer_ids,
        green_customer_ids=green_customer_ids,
        active_green_customer_ids=active_green_customer_ids,
    )


def _candidate_roots(data_dir: Path) -> list[Path]:
    roots = [data_dir]
    data_child = data_dir / "data"
    if data_child not in roots:
        roots.append(data_child)
    return roots


def _discover_files(data_dir: Path) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for key, candidates in FILE_CANDIDATES.items():
        result[key] = _find_existing_file(_candidate_roots(data_dir), candidates)
    return result


def _find_existing_file(roots: Iterable[Path], candidates: Iterable[str]) -> Path:
    for root in roots:
        for name in candidates:
            path = root / name
            if path.exists():
                return path
    searched = ", ".join(str(root / name) for root in roots for name in candidates)
    raise FileNotFoundError(f"none of the expected data files exist: {searched}")


def _load_orders(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path)
    df = df.iloc[:, :4].copy()
    df.columns = ["order_id", "weight", "volume", "customer_id"]
    df["order_id"] = df["order_id"].astype(int)
    df["customer_id"] = df["customer_id"].astype(int)
    df["weight"] = df["weight"].astype(float)
    df["volume"] = df["volume"].astype(float)
    return df


def _load_coordinates(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path)
    df = df.iloc[:, :4].copy()
    df.columns = ["node_type", "node_id", "x_km", "y_km"]
    df["node_id"] = df["node_id"].astype(int)
    df["x_km"] = df["x_km"].astype(float)
    df["y_km"] = df["y_km"].astype(float)
    return df


def _load_distance_matrix(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, index_col=0)
    df.index = df.index.astype(int)
    df.columns = [int(col) for col in df.columns]
    return df.astype(float)


def _load_time_windows(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path)
    df = df.iloc[:, :3].copy()
    df.columns = ["customer_id", "start_time", "end_time"]
    df["customer_id"] = df["customer_id"].astype(int)
    df["earliest_min"] = df["start_time"].map(parse_hhmm_to_minutes).astype(int)
    df["latest_min"] = df["end_time"].map(parse_hhmm_to_minutes).astype(int)
    df["window_width_min"] = df["latest_min"] - df["earliest_min"]
    return df


def _validate_raw_frames(
    orders: pd.DataFrame,
    coordinates: pd.DataFrame,
    distance_matrix: pd.DataFrame,
    time_windows: pd.DataFrame,
) -> None:
    if orders.shape != (2169, 4):
        raise ValueError(f"expected 2169x4 orders, got {orders.shape}")
    if coordinates.shape[0] != 99:
        raise ValueError(f"expected 99 coordinate rows, got {coordinates.shape[0]}")
    if distance_matrix.shape != (99, 99):
        raise ValueError(f"expected 99x99 distance matrix, got {distance_matrix.shape}")
    if time_windows.shape[0] != 98:
        raise ValueError(f"expected 98 time-window rows, got {time_windows.shape[0]}")
    if set(distance_matrix.index) != set(range(99)):
        raise ValueError("distance matrix index must contain node IDs 0..98")
    if set(distance_matrix.columns) != set(range(99)):
        raise ValueError("distance matrix columns must contain node IDs 0..98")
    if not np.allclose(distance_matrix.values, distance_matrix.values.T):
        raise ValueError("distance matrix must be symmetric")
    if not np.allclose(np.diag(distance_matrix.values), 0.0):
        raise ValueError("distance matrix diagonal must be zero")
    if (orders[["weight", "volume"]] <= 0).any().any():
        raise ValueError("orders must have positive weight and volume")
    if (time_windows["window_width_min"] < 0).any():
        raise ValueError("time windows must end after they start")


def _aggregate_customer_demands(orders: pd.DataFrame) -> pd.DataFrame:
    demand = (
        orders.groupby("customer_id", as_index=False)
        .agg(
            total_weight=("weight", "sum"),
            total_volume=("volume", "sum"),
            order_count=("order_id", "count"),
        )
        .sort_values("customer_id")
        .reset_index(drop=True)
    )
    return demand


def _mark_green_zone(coordinates: pd.DataFrame) -> pd.DataFrame:
    result = coordinates.copy()
    result["distance_from_origin_km"] = np.hypot(result["x_km"], result["y_km"])
    result["is_green_zone"] = result["distance_from_origin_km"] <= GREEN_ZONE_RADIUS_KM
    return result


def _attach_customer_attributes(
    customer_demands: pd.DataFrame,
    coordinates: pd.DataFrame,
    time_windows: pd.DataFrame,
    split_weight_kg: float,
    split_volume_m3: float,
) -> pd.DataFrame:
    enriched = customer_demands.merge(
        coordinates[
            [
                "node_id",
                "x_km",
                "y_km",
                "distance_from_origin_km",
                "is_green_zone",
            ]
        ],
        left_on="customer_id",
        right_on="node_id",
        how="left",
        validate="one_to_one",
    ).drop(columns=["node_id"])
    enriched = enriched.merge(
        time_windows[["customer_id", "earliest_min", "latest_min", "window_width_min"]],
        on="customer_id",
        how="left",
        validate="one_to_one",
    )

    split_ratio = np.maximum(
        enriched["total_weight"] / split_weight_kg,
        enriched["total_volume"] / split_volume_m3,
    )
    enriched["split_count"] = np.ceil(split_ratio).astype(int).clip(lower=1)
    return enriched.sort_values("customer_id").reset_index(drop=True)


def _build_service_nodes(customer_demands: pd.DataFrame) -> tuple[pd.DataFrame, dict[int, int]]:
    rows: list[dict[str, object]] = []
    node_to_customer: dict[int, int] = {}
    next_node_id = 1

    for row in customer_demands.itertuples(index=False):
        split_count = int(row.split_count)
        demand_weight = float(row.total_weight) / split_count
        demand_volume = float(row.total_volume) / split_count
        customer_id = int(row.customer_id)

        for split_index in range(1, split_count + 1):
            rows.append(
                {
                    "node_id": next_node_id,
                    "customer_id": customer_id,
                    "split_index": split_index,
                    "split_count": split_count,
                    "demand_weight": demand_weight,
                    "demand_volume": demand_volume,
                    "earliest_min": int(row.earliest_min),
                    "latest_min": int(row.latest_min),
                    "is_green_zone": bool(row.is_green_zone),
                }
            )
            node_to_customer[next_node_id] = customer_id
            next_node_id += 1

    service_nodes = pd.DataFrame(rows)
    return service_nodes, node_to_customer
