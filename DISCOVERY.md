# Discovery: organvm/system-governance-framework

**Discovered:** 2026-06-22 | **Verdict:** REAL VALUE — promoted to ranked tier

## Value Thesis

`system-governance-framework` is the policy engine of the ORGANVM estate, and its latent value lies in two concrete, immediately deployable assets that are already fully built. First, a working Python SDK (`src/rules.py`, `src/validator.py`, `src/promotion.py`) that exposes a `GovernanceValidator` class with eight built-in rules, a composable `Rule` dataclass for custom checks, and a `promote()` / `can_promote()` state machine covering the full `PLANNED → SKELETON → PROTOTYPE → PRODUCTION → ARCHIVED` lifecycle — the same lifecycle that `conductor wip promote` enforces manually today. Second, a Framework-as-Code GitHub Actions layer: a reusable `reusable-ci.yml` workflow callable across any of the 145 ORGANVM repos via a single `uses:` line, a JSON-schema-validated `governance.yml` config with three presets (minimal / standard / enterprise), an auto-detecting install script, and composite actions for language detection and config loading — all version-pinned and upgradeable without touching each consumer. The estate currently has 107 CI workflows across 89 active repos that are diverging; this framework already solves that with one version bump. The Python SDK already bridges to `organvm_engine.governance.state_machine` via a compatibility adapter, meaning it is designed to slot directly into the conductor layer — the wiring is one import away.

## Highest Latent Value

The reusable GitHub Actions framework plus the Python promotion state machine together constitute a **fleet-wide governance runtime** that can standardize CI, enforce promotion criteria, and produce machine-auditable compliance evidence across all eight organs without per-repo maintenance.

## Single Best First Task

Publish the Python package (the `pyproject.toml` is already configured) and add a fleet-validate CLI entry point that calls `GovernanceValidator.validate_many()` against a list of repos via the GitHub API — enabling `conductor` to run a single command that audits governance compliance across the full 145-repo estate in one pass.
