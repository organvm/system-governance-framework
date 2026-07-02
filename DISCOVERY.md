# Value Discovery: organvm/system-governance-framework

**Discovery date:** 2026-06-23
**Status:** PROMOTED — real, deployable value found

## Value Thesis

`organvm/system-governance-framework` is the only tested, pip-ready Python governance rules engine in the estate and therefore the canonical source of truth for repo lifecycle enforcement across all ~89 active repos and 10 organs. Its three concrete assets — `GovernanceValidator` (an extensible rule runner that accepts any `dict`-shaped repo state), `VALID_TRANSITIONS` state machine with a compatibility adapter to `organvm_engine`, and `config/schema.json` (a preset-aware JSON Schema covering CI, security, compliance, and dependabot) — provide an authoritative, already-tested enforcement layer that no other repo duplicates. The latent value is large and immediately realizable: packaging and publishing the library to a Python package index (PyPI or a private organvm index) would let every organ's CI pipeline import `from system_governance_framework.validator import GovernanceValidator` to gate promotions and enforce cross-organ dependency hygiene today, without vendoring or copying. **Single best first task: configure PyPI publishing in CI** (`pyproject.toml` is already correctly structured; add a `publish` workflow that fires on version tags).
