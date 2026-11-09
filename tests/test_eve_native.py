"""Native parity: compiled kernels must equal the Python oracles.

_replay_cy.score_pairs vs native_replay.py_score, and
_forensic_cy.fault_worst vs the pure-Python sweep inside
resilience.fault_stats. Byte-identical numbers, native speed.
"""

import sys

import pytest

from eve_unleashed import native_replay, resilience
from eve_unleashed.dodeca_recall import SHAPES


def test_native_backends_loaded():
    assert native_replay.BACKEND == "cython", native_replay.fallback_reason()
    assert resilience.ENGINE == "native"
    assert sys._is_gil_enabled() is False


def test_replay_parity():
    pred_rung = [0, 1, 2, -1, 3, 1, 0, 5]
    pred_kind = [0, 1, 1, 2, 1, 0, 2, 1]
    ans_rung = [0, 1, 0, 2, 3, 0, 0, 5]
    ans_ok = [1, 1, 0, 1, 0, 0, 1, 1]
    n_rungs = 6
    expected = native_replay.py_score(
        pred_rung, pred_kind, ans_rung, ans_ok, n_rungs)
    got = native_replay._native_score(
        pred_rung, pred_kind, ans_rung, ans_ok, n_rungs)
    assert tuple(got) == tuple(expected)
    out = native_replay.score_columns(
        pred_rung, pred_kind, ans_rung, ans_ok)
    assert out[-1] == "cython"
    assert out[:-1] == tuple(expected)


def test_forensic_parity_all_solids(monkeypatch):
    assert len(SHAPES) == 7
    for solid in SHAPES:
        expected_native = resilience.fault_stats(solid)
        monkeypatch.setattr(resilience, "_cy", None)
        got_python = resilience.fault_stats(solid)
        for key in ("fault_diameter", "disconnects", "fault_stretch"):
            assert got_python[key] == expected_native[key], (solid, key)
