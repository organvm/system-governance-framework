"""Tests for the configuration loader."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

import src.config as config_mod
from src.config import (
    ConfigError,
    _deep_merge,
    config_to_repo_state,
    load_governance_config,
    load_preset,
    load_schema,
)


class TestLoadPreset:
    def test_loads_minimal(self):
        config = load_preset("minimal")
        assert config["framework"]["preset"] == "minimal"

    def test_loads_standard(self):
        config = load_preset("standard")
        assert config["framework"]["preset"] == "standard"

    def test_loads_enterprise(self):
        config = load_preset("enterprise")
        assert config["framework"]["preset"] == "enterprise"

    def test_rejects_unknown_preset(self):
        with pytest.raises(ConfigError, match="Unknown preset"):
            load_preset("mythical")


class TestDeepMerge:
    def test_simple_override(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        base = {"features": {"ci": {"enabled": True, "coverage": False}}}
        override = {"features": {"ci": {"coverage": True}}}
        result = _deep_merge(base, override)
        assert result["features"]["ci"]["enabled"] is True
        assert result["features"]["ci"]["coverage"] is True

    def test_does_not_mutate_base(self):
        base = {"a": {"b": 1}}
        override = {"a": {"b": 2}}
        _deep_merge(base, override)
        assert base["a"]["b"] == 1


class TestLoadGovernanceConfig:
    def _write_config(self, tmpdir: Path, content: dict) -> Path:
        path = tmpdir / "governance.yml"
        with open(path, "w") as f:
            yaml.dump(content, f)
        return path

    def test_loads_with_preset_resolution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_config(Path(tmpdir), {
                "framework": {"version": "3.0.0", "preset": "minimal"},
            })
            config = load_governance_config(path)
            assert config["framework"]["preset"] == "minimal"
            # Should have preset defaults merged in
            assert "features" in config

    def test_user_overrides_preset(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_config(Path(tmpdir), {
                "framework": {"version": "3.0.0", "preset": "minimal"},
                "features": {"ci": {"test-coverage": True}},
            })
            config = load_governance_config(path)
            # User override should win
            assert config["features"]["ci"]["test-coverage"] is True

    def test_defaults_to_standard_preset(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_config(Path(tmpdir), {
                "framework": {"version": "3.0.0"},
            })
            config = load_governance_config(path)
            # Should default to standard
            assert config["features"]["security"]["codeql"] is True

    def test_rejects_missing_version(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_config(Path(tmpdir), {
                "framework": {"preset": "minimal"},
            })
            with pytest.raises(ConfigError, match="version"):
                load_governance_config(path)

    def test_rejects_missing_file(self):
        with pytest.raises(ConfigError, match="not found"):
            load_governance_config("/nonexistent/governance.yml")

    def test_rejects_non_mapping(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "governance.yml"
            with open(path, "w") as f:
                f.write("- just a list\n")
            with pytest.raises(ConfigError, match="mapping"):
                load_governance_config(path)


class TestConfigToRepoState:
    def test_minimal_preset_state(self):
        config = load_preset("minimal")
        state = config_to_repo_state(config)
        assert state["preset"] == "minimal"
        assert state["ci_enabled"] is True
        assert state["test_coverage_enabled"] is False
        assert state["codeql_enabled"] is False

    def test_standard_preset_state(self):
        config = load_preset("standard")
        state = config_to_repo_state(config)
        assert state["preset"] == "standard"
        assert state["security_enabled"] is True
        assert state["codeql_enabled"] is True

    def test_enterprise_preset_state(self):
        config = load_preset("enterprise")
        state = config_to_repo_state(config)
        assert state["preset"] == "enterprise"
        assert state["codeql_enabled"] is True
        assert state["semgrep_enabled"] is True
        assert state["compliance_enabled"] is True


class TestLoadPresetMissingFile:
    def test_raises_when_preset_file_absent(self):
        """load_preset raises ConfigError when the preset YAML file doesn't exist on disk."""
        with tempfile.TemporaryDirectory() as tmpdir, \
             patch.object(config_mod, "PRESETS_DIR", Path(tmpdir)):
            with pytest.raises(ConfigError, match="Preset file not found"):
                load_preset("minimal")


class TestLoadSchema:
    def test_loads_schema_successfully(self):
        schema = load_schema()
        assert isinstance(schema, dict)
        assert "$schema" in schema or "type" in schema

    def test_raises_when_schema_file_absent(self):
        with patch.object(config_mod, "SCHEMA_PATH", Path("/nonexistent/schema.json")):
            with pytest.raises(ConfigError, match="Schema file not found"):
                load_schema()


class TestLoadGovernanceConfigFrameworkType:
    def test_rejects_non_mapping_framework(self):
        """load_governance_config raises when 'framework' key is not a dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "governance.yml"
            path.write_text("framework: just_a_string\n")
            with pytest.raises(ConfigError, match="mapping"):
                load_governance_config(path)
