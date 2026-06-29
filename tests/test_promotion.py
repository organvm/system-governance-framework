"""Tests for the promotion state machine."""

from unittest.mock import MagicMock, patch

import src.promotion as promotion_mod
from src.promotion import VALID_TRANSITIONS, can_promote, promote


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


class TestCanPromoteUnknownStates:
    """Cover the `return False` guard in can_promote (line 85)."""

    def test_invalid_current_state(self):
        assert can_promote("INVALID", "SKELETON") is False

    def test_invalid_target_state(self):
        assert can_promote("PLANNED", "INVALID") is False

    def test_both_states_invalid(self):
        assert can_promote("NONEXISTENT", "ALSO_MISSING") is False


def _engine_patches(check_fn=None, get_valid_fn=None):
    """Return three patch context managers that simulate organvm_engine being present."""
    if check_fn is None:
        check_fn = MagicMock(return_value=(True, "ok"))
    if get_valid_fn is None:
        get_valid_fn = MagicMock(return_value=[])
    return (
        patch.object(promotion_mod, "_HAS_ENGINE_STATE_MACHINE", True),
        patch.object(promotion_mod, "_engine_check_transition", check_fn, create=True),
        patch.object(promotion_mod, "_engine_get_valid_transitions", get_valid_fn, create=True),
    )


class TestEngineAllowed:
    """Cover _engine_allowed (lines 63-79) by mocking the engine functions."""

    def test_canonical_mapping_target_found(self):
        """_engine_allowed returns True when engine's valid targets include the canonical target."""
        get_valid = MagicMock(return_value=["CANDIDATE"])  # PROTOTYPE → CANDIDATE
        check_fn = MagicMock(return_value=(False, "no"))
        p1, p2, p3 = _engine_patches(check_fn, get_valid)
        with p1, p2, p3:
            # SKELETON → LOCAL (canonical), PROTOTYPE → CANDIDATE
            # get_valid("LOCAL") returns ["CANDIDATE"] → True
            result = promotion_mod._engine_allowed("SKELETON", "PROTOTYPE")
            assert result is True
            get_valid.assert_called_once_with("LOCAL")

    def test_canonical_mapping_target_not_found(self):
        """_engine_allowed returns False when canonical target absent from engine results."""
        get_valid = MagicMock(return_value=["OTHER_STATE"])
        check_fn = MagicMock(return_value=(False, "no"))
        p1, p2, p3 = _engine_patches(check_fn, get_valid)
        with p1, p2, p3:
            result = promotion_mod._engine_allowed("SKELETON", "PRODUCTION")
            # PRODUCTION → GRADUATED; "GRADUATED" not in {"OTHER_STATE"}
            assert result is False

    def test_archived_to_production_legacy_fallback(self):
        """ARCHIVED → PRODUCTION is preserved even when the engine reports no valid targets."""
        get_valid = MagicMock(return_value=[])
        check_fn = MagicMock(return_value=(False, "no"))
        p1, p2, p3 = _engine_patches(check_fn, get_valid)
        with p1, p2, p3:
            result = promotion_mod._engine_allowed("ARCHIVED", "PRODUCTION")
            assert result is True

    def test_archived_to_other_state_returns_false(self):
        """ARCHIVED → anything other than PRODUCTION: engine empty → False."""
        get_valid = MagicMock(return_value=[])
        check_fn = MagicMock(return_value=(False, "no"))
        p1, p2, p3 = _engine_patches(check_fn, get_valid)
        with p1, p2, p3:
            result = promotion_mod._engine_allowed("ARCHIVED", "SKELETON")
            assert result is False

    def test_unmapped_states_use_check_transition(self):
        """When both states have no canonical mapping, engine_check_transition is called."""
        check_fn = MagicMock(return_value=(True, "ok"))
        get_valid = MagicMock(return_value=[])
        p1, p2, p3 = _engine_patches(check_fn, get_valid)
        with p1, p2, p3:
            # Neither "CUSTOM_A" nor "CUSTOM_B" appear in _LEGACY_TO_CANONICAL,
            # so current_canonical == current and target_canonical == target.
            result = promotion_mod._engine_allowed("CUSTOM_A", "CUSTOM_B")
            check_fn.assert_called_once_with("CUSTOM_A", "CUSTOM_B")
            assert result is True

    def test_unmapped_states_check_transition_returns_false(self):
        check_fn = MagicMock(return_value=(False, "nope"))
        get_valid = MagicMock(return_value=[])
        p1, p2, p3 = _engine_patches(check_fn, get_valid)
        with p1, p2, p3:
            result = promotion_mod._engine_allowed("CUSTOM_A", "CUSTOM_B")
            assert result is False


class TestCanPromoteWithEngine:
    """Cover can_promote's engine branch (line 90)."""

    def test_engine_present_legacy_valid(self):
        """Engine present but legacy table already says yes → True without engine call."""
        get_valid = MagicMock(return_value=[])
        check_fn = MagicMock(return_value=(False, "no"))
        p1, p2, p3 = _engine_patches(check_fn, get_valid)
        with p1, p2, p3:
            assert promotion_mod.can_promote("SKELETON", "PROTOTYPE") is True

    def test_engine_present_both_say_no(self):
        """Engine present; legacy and engine both reject the transition → False."""
        get_valid = MagicMock(return_value=[])
        check_fn = MagicMock(return_value=(False, "no"))
        p1, p2, p3 = _engine_patches(check_fn, get_valid)
        with p1, p2, p3:
            # PLANNED → PRODUCTION: not in legacy; engine get_valid returns nothing
            assert promotion_mod.can_promote("PLANNED", "PRODUCTION") is False

    def test_engine_present_engine_says_yes(self):
        """Engine present; legacy says no but engine approves → True."""
        # SKELETON → PRODUCTION: not in legacy table; engine says GRADUATED is valid from LOCAL
        get_valid = MagicMock(return_value=["GRADUATED"])
        check_fn = MagicMock(return_value=(False, "no"))
        p1, p2, p3 = _engine_patches(check_fn, get_valid)
        with p1, p2, p3:
            assert promotion_mod.can_promote("SKELETON", "PRODUCTION") is True


class TestPromoteWithEngine:
    """Cover the engine-present branches in promote() including line 108."""

    def test_promote_success_with_engine(self):
        """promote() succeeds via can_promote when engine is present."""
        get_valid = MagicMock(return_value=["CANDIDATE"])
        check_fn = MagicMock(return_value=(True, "ok"))
        p1, p2, p3 = _engine_patches(check_fn, get_valid)
        with p1, p2, p3:
            result = promotion_mod.promote("SKELETON", "PROTOTYPE", "my-repo")
            assert result.success is True
            assert "SKELETON → PROTOTYPE" in result.message

    def test_promote_failure_message_includes_legacy_allowed(self):
        """On failure with engine present, allowed set comes from legacy transitions."""
        get_valid = MagicMock(return_value=[])
        check_fn = MagicMock(return_value=(False, "no"))
        p1, p2, p3 = _engine_patches(check_fn, get_valid)
        with p1, p2, p3:
            result = promotion_mod.promote("PLANNED", "PRODUCTION")
            assert result.success is False
            assert "SKELETON" in result.message  # PLANNED's only legacy target

    def test_promote_line108_engine_fallback_for_empty_allowed(self):
        """Line 108: when legacy allowed set is empty and engine is present, engine provides allowed list."""
        get_valid = MagicMock(return_value=["CANDIDATE"])
        check_fn = MagicMock(return_value=(False, "no"))
        p1, p2, p3 = _engine_patches(check_fn, get_valid)
        # Patch PLANNED to have no legacy transitions so allowed == set()
        with p1, p2, p3, patch.dict(promotion_mod.VALID_TRANSITIONS, {"PLANNED": set()}):
            result = promotion_mod.promote("PLANNED", "ARCHIVED")
            assert result.success is False
            # get_valid should have been called (once by _engine_allowed, once by line 108)
            assert get_valid.call_count >= 1
