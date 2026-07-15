# Assumptions

- **A001, code-audit resolved:** the current single-target definition apply cannot directly provide atomic convergence; pure definition rendering/validation must be reused inside a new coordinated multi-target apply.
- **A002, owner-confirmed:** project-level questions require durable state separate from generated review output.
- **A003, validated by current implementation:** vertical sections have stable ids and the active vertical has a versioned lock, while revision reconciliation still requires a new contract.
- **A004, owner-confirmed:** proposal questions and project questions have different scopes and remain distinct.
- **A005, validated by current architecture:** file-backed Markdown and YAML remain sufficient; no database is required.
- **A006, owner-confirmed:** schema-v1 workspaces remain backward-compatible and explicitly migratable to schema v2; v1-valid operations remain available.
- **A007, code-audit resolved:** registering v1-to-v2 metadata is insufficient because the current planner is specialized for legacy-to-v1 bootstrap; transition handlers are required.
- **A008, to validate in feature design:** candidate workspace overlays can compose multiple adjacent transition handlers while preserving source access accounting and recovery.
- **A009, to validate in feature design:** managed next actions can consume one additional convergence source without breaking curated/generated deduplication.
- **A010, owner-confirmed:** convergence apply performs only validated atomic canonical writes; rebuild, curation, publication and owner review remain separate.
- **A011, constraint:** heuristic vertical matches remain suggestions and never become declared evidence through convergence.
- **A012, owner-confirmed:** declared locked-vertical questions have precedence; deterministic fallback requires sufficient metadata, otherwise `no_safe_question` is emitted.
- **A013, owner-confirmed:** convergence uses the six-class Q004 ordering and exposes its rationale.
- **A014, owner-confirmed:** deferred or muted questions can converge interview state but never satisfy definition completion or evidence coverage.
- **A015, technical contract:** exact retry of an already committed apply is distinguishable from divergent replay through persisted apply references and final hashes.
- **A016, technical contract:** project-question evidence remains inactive in decision context until applied definition becomes the semantic authority.
- **A017, to validate in feature design:** freshness can distinguish question-only changes from definition-apply changes without introducing a second persisted authority.
- **A018, scope assumption:** the current repository pilot validates orchestration but does not define universal migration, question or priority policy.
