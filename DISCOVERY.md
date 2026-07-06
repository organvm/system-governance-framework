# Discovery: system-governance-framework

**Discovered:** 2026-06-23 | **Verdict:** REAL VALUE — promote to ranked tier

## Value Thesis

`system-governance-framework` is the importable policy engine for ORGANVM's 145-repo, 10-organ estate. Its Python library (`src/`) ships a `GovernanceValidator` with 8 built-in rules, a pluggable `Rule` dataclass for extending policy without forking, and a `promote()`/`can_promote()` state machine (PLANNED → SKELETON → PROTOTYPE → PRODUCTION → ARCHIVED) that already bridges to `organvm_engine`'s canonical state machine when present — making it the single source of truth for lifecycle transitions across the estate. The config layer adds a JSON Schema Draft-07 contract (`config/schema.json`) for fleet-wide `governance.yml` validation across three preset tiers (minimal, standard, enterprise), and a curl-pipe installer (`scripts/install-framework.sh`) that onboards any new repo in under a minute. Crucially, the library is already `pip install`-ready (`pyproject.toml` is fully configured) but is not yet wired into ORGAN-IV's orchestration tooling — closing that gap would give the conductor fleet-wide governance audits (`validate_many()` over all 145 repos), policy-gated promotions, and a machine-verifiable compliance contract for every repo in the system.

## Best First Task

Wire `GovernanceValidator.validate_many()` into a `conductor audit governance` command that pulls repo state from the fleet registry and runs the full rule suite, surfacing governance failures across all 145 repos in a single pass with pass/fail/warning counts per organ.
