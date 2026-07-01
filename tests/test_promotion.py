"""Tests for the promotion state machine."""

import importlib
import sys
import types

import pytest

import src.promotion as promotion_module
from src.promotion import VALID_TRANSITIONS, can_promote, promote


@pytest.fixture
def promotion_with_engine():
    """Reload promotion.py with a fake canonical engine state machine."""
    calls = {"check": [], "valid": []}

    def check_transition(current: str, target: str) -> tuple[bool, str]:
        calls["check"].append((current, target))
        return target == "CANONICAL_TARGET", "checked by canonical engine"

    def get_valid_transitions(current: str) -> list[str]:
        calls["valid"].append(current)
        return {
            "INCUBATOR": ["CANDIDATE"],
            "ARCHIVED": [],
            "GRADUATED": [],
            "ENGINE_ONLY": ["LOCAL"],
        }.get(current, [])

    engine_pkg = types.ModuleType("organvm_engine")
    governance_pkg = types.ModuleType("organvm_engine.governance")
    state_machine = types.ModuleType("organvm_engine.governance.state_machine")
    state_machine.check_transition = check_transition
    state_machine.get_valid_transitions = get_valid_transitions
    engine_pkg.governance = governance_pkg
    governance_pkg.state_machine = state_machine

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setitem(sys.modules, "organvm_engine", engine_pkg)
        monkeypatch.setitem(sys.modules, "organvm_engine.governance", governance_pkg)
        monkeypatch.setitem(
            sys.modules,
            "organvm_engine.governance.state_machine",
            state_machine,
        )
        yield importlib.reload(promotion_module), calls

    importlib.reload(promotion_module)


class TestCanPromote:
    def test_planned_to_skeleton(self):
        assert can_promote("PLANNED", "SKELETON") is True

    def test_skeleton_to_prototype(self):
        assert can_promote("SKELETON", "PROTOTYPE") is True

    def test_prototype_to_production(self):
        assert can_promote("PROTOTYPE", "PRODUCTION") is True

    def test_production_to_archived(self):
        assert can_promote("PRODUCTION", "ARCHIVED") is True

    def test_cannot_skip_states(self):
        assert can_promote("PLANNED", "PRODUCTION") is False

    def test_cannot_go_backwards_planned(self):
        assert can_promote("PROTOTYPE", "PLANNED") is False

    def test_unarchive_allowed(self):
        assert can_promote("ARCHIVED", "PRODUCTION") is True

    def test_design_only_to_prototype(self):
        assert can_promote("DESIGN_ONLY", "PROTOTYPE") is True

    def test_rejects_unknown_states(self):
        assert can_promote("INVALID", "SKELETON") is False
        assert can_promote("SKELETON", "INVALID") is False


class TestPromote:
    def test_successful_promotion(self):
        result = promote("SKELETON", "PROTOTYPE", "test-repo")
        assert result.success is True
        assert "SKELETON → PROTOTYPE" in result.message

    def test_failed_promotion(self):
        result = promote("PLANNED", "PRODUCTION", "test-repo")
        assert result.success is False
        assert "Cannot promote" in result.message

    def test_unknown_state(self):
        result = promote("INVALID", "SKELETON")
        assert result.success is False
        assert "Unknown state" in result.message

    def test_unknown_target(self):
        result = promote("SKELETON", "INVALID")
        assert result.success is False
        assert "Unknown target" in result.message


class TestStateMachine:
    def test_all_states_have_transitions(self):
        for state in VALID_TRANSITIONS:
            assert len(VALID_TRANSITIONS[state]) >= 1

    def test_no_self_transitions(self):
        for state, targets in VALID_TRANSITIONS.items():
            assert state not in targets

    def test_full_lifecycle(self):
        path = ["PLANNED", "SKELETON", "PROTOTYPE", "PRODUCTION", "ARCHIVED"]
        for i in range(len(path) - 1):
            assert can_promote(path[i], path[i + 1]), f"{path[i]} → {path[i+1]} should be valid"


class TestEngineCompatibility:
    def test_accepts_engine_transition_for_legacy_state_names(self, promotion_with_engine):
        promotion, calls = promotion_with_engine

        assert promotion.can_promote("PLANNED", "PROTOTYPE") is True
        assert ("INCUBATOR",) == tuple(calls["valid"])

    def test_delegates_unmapped_state_names_to_engine(self, promotion_with_engine):
        promotion, calls = promotion_with_engine

        assert promotion._engine_allowed("CANONICAL_SOURCE", "CANONICAL_TARGET") is True
        assert calls["check"] == [("CANONICAL_SOURCE", "CANONICAL_TARGET")]

    def test_preserves_legacy_unarchive_when_engine_treats_archived_as_terminal(
        self,
        promotion_with_engine,
    ):
        promotion, _ = promotion_with_engine

        assert promotion._engine_allowed("ARCHIVED", "PRODUCTION") is True

    def test_rejects_transition_when_legacy_and_engine_disallow(self, promotion_with_engine):
        promotion, _ = promotion_with_engine

        assert promotion.can_promote("PRODUCTION", "SKELETON") is False

    def test_failed_engine_only_state_reports_canonical_allowed_targets(
        self,
        promotion_with_engine,
    ):
        promotion, _ = promotion_with_engine

        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(promotion, "ALL_STATES", promotion.ALL_STATES | {"ENGINE_ONLY"})
            monkeypatch.setitem(
                promotion._LEGACY_TO_CANONICAL,
                "ENGINE_ONLY",
                "ENGINE_ONLY",
            )

            result = promotion.promote("ENGINE_ONLY", "PRODUCTION")

        assert result.success is False
        assert "Allowed: ['LOCAL']" in result.message
