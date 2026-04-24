# -*- coding: utf-8 -*-
"""Backward-compatible data-loader import path.

New code should import from `green_logistics.data_processing`. This wrapper is
kept so earlier notebooks, tests, and sub-dialogues do not break.
"""

from __future__ import annotations

from .data_processing import ProblemData, load_problem_data, parse_hhmm_to_minutes

__all__ = ["ProblemData", "load_problem_data", "parse_hhmm_to_minutes"]

