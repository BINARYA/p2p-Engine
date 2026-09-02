from __future__ import annotations

from p2p_engine.mcp.catalog.common import tool as _tool


def tool_definitions() -> list[dict[str, object]]:
    return [
        _tool(
            'p2p_project_identity_show',
            'Read the stable storage-neutral project identity and local replica address.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_identity_status',
            'Read identity validity and explicit adoption recovery without mutating project state.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_identity_transitions',
            'Read the frozen identity behavior for move, restore, replica, derive and detach operations.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_identity_copy_check',
            'Classify an observed duplicate UUID/replica pair and require explicit copy intent.',
            {
                'root': {'type': 'string'},
                'observed_project_uuid': {'type': 'string'},
                'observed_replica_id': {'type': 'string'},
                'intent': {
                    'type': 'string',
                    'enum': ['same-instance', 'new-replica', 'read-only', 'derive'],
                },
            },
            ['observed_project_uuid'],
        ),
        _tool(
            'p2p_project_identity_adopt_preview',
            'Preview explicit backup-protected adoption of stable identity for a legacy project.',
            {
                'root': {'type': 'string'},
                'operation_key': {'type': 'string'},
                'actor_id': {'type': 'string'},
                'executor_id': {'type': 'string'},
                'executor_kind': {'type': 'string', 'enum': ['person', 'user', 'agent', 'mcp_client', 'client']},
            },
            ['operation_key', 'actor_id'],
        ),
        _tool(
            'p2p_project_identity_adopt_apply',
            'Consent-gated receipt-backed application of an exact identity-adoption preview.',
            {
                'root': {'type': 'string'},
                'operation_key': {'type': 'string'},
                'preview_token': {'type': 'string'},
                'confirm': {'type': 'boolean'},
                'actor_id': {'type': 'string'},
                'executor_id': {'type': 'string'},
                'executor_kind': {'type': 'string', 'enum': ['person', 'user', 'agent', 'mcp_client', 'client']},
                'consent_id': {'type': 'string'},
            },
            ['operation_key', 'preview_token', 'actor_id', 'consent_id'],
        ),
        _tool(
            'p2p_project_identity_derive_preview',
            'Preview a new independent project UUID with optional historical lineage.',
            {
                'root': {'type': 'string'},
                'operation_key': {'type': 'string'},
                'display_name': {'type': 'string'},
                'retain_lineage': {'type': 'boolean'},
                'lineage_visibility': {'type': 'string', 'enum': ['preserved', 'private']},
                'actor_id': {'type': 'string'},
                'executor_id': {'type': 'string'},
                'executor_kind': {'type': 'string', 'enum': ['person', 'user', 'agent', 'mcp_client', 'client']},
            },
            ['operation_key', 'actor_id'],
        ),
        _tool(
            'p2p_project_identity_derive_apply',
            'Consent-gated receipt-backed application of an exact independent-derivation preview.',
            {
                'root': {'type': 'string'},
                'operation_key': {'type': 'string'},
                'preview_token': {'type': 'string'},
                'confirm': {'type': 'boolean'},
                'display_name': {'type': 'string'},
                'retain_lineage': {'type': 'boolean'},
                'lineage_visibility': {'type': 'string', 'enum': ['preserved', 'private']},
                'actor_id': {'type': 'string'},
                'executor_id': {'type': 'string'},
                'executor_kind': {'type': 'string', 'enum': ['person', 'user', 'agent', 'mcp_client', 'client']},
                'consent_id': {'type': 'string'},
            },
            ['operation_key', 'preview_token', 'actor_id', 'consent_id'],
        ),
        _tool(
            'p2p_project_authority_transfer_eligibility',
            (
                'Read-only eligibility for transferring the same project to WaveKit. '
                'It never creates a session, fences writes, uploads content or changes authority.'
            ),
            {
                'root': {'type': 'string'},
                'server': {'type': 'string'},
                'owner_profile_ref': {'type': 'string'},
                'operation_key': {'type': 'string'},
            },
            ['server', 'owner_profile_ref', 'operation_key'],
        ),
        _tool(
            'p2p_project_authority_transfer_preview',
            (
                'Read-only sanitized authority-transfer preview. Apply is intentionally absent '
                'from MCP and remains an explicitly confirmed owner CLI operation.'
            ),
            {
                'root': {'type': 'string'},
                'server': {'type': 'string'},
                'owner_profile_ref': {'type': 'string'},
                'operation_key': {'type': 'string'},
            },
            ['server', 'owner_profile_ref', 'operation_key'],
        ),
        _tool(
            'p2p_project_authority_transfer_status',
            'Read local transfer state and optionally query the bound WaveKit session.',
            {
                'root': {'type': 'string'},
                'server': {'type': 'string'},
            },
        ),
        _tool(
            'p2p_linked_replica_status',
            (
                'Read the non-secret linked-local binding, access state, revision, cursor and '
                'freshness without exposing credentials or storage internals.'
            ),
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_linked_replica_catch_up',
            (
                'Catch up a linked-local replica from WaveKit through verified canonical '
                'snapshots. Clone, attach, move and copy registration remain owner-run CLI.'
            ),
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_domain_show',
            'Read the free project subject classification and its independent structure source.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_domain_set',
            (
                'Consent-gated classification mutation. Changes only the project domain; '
                'never changes sections, criteria, proposal coverage, or readiness inputs.'
            ),
            {
                'root': {'type': 'string'},
                'key': {'type': 'string'},
                'name': {'type': 'string'},
                'source': {'type': 'string', 'enum': ['local', 'external', 'imported', 'system']},
                'external_ref': {'type': 'string'},
                'actor_id': {'type': 'string'},
                'executor_id': {'type': 'string'},
                'executor_kind': {'type': 'string', 'enum': ['person', 'user', 'agent', 'mcp_client', 'client']},
                'consent_id': {'type': 'string'},
                'operation_key': {'type': 'string'},
            },
            ['key', 'actor_id', 'consent_id', 'operation_key'],
        ),
        _tool(
            'p2p_project_domain_clear',
            (
                'Consent-gated classification mutation. Clears only the project domain and '
                'preserves the complete project structure and readiness inputs.'
            ),
            {
                'root': {'type': 'string'},
                'actor_id': {'type': 'string'},
                'executor_id': {'type': 'string'},
                'executor_kind': {'type': 'string', 'enum': ['person', 'user', 'agent', 'mcp_client', 'client']},
                'consent_id': {'type': 'string'},
                'operation_key': {'type': 'string'},
            },
            ['actor_id', 'consent_id', 'operation_key'],
        ),
        _tool(
            'p2p_project_structure_show',
            'Read the canonical project-owned structure. Origin is provenance only.',
            {
                'root': {'type': 'string'},
                'include_retired': {'type': 'boolean'},
            },
        ),
        _tool(
            'p2p_project_structure_history',
            'Read bounded append-only project-structure event evidence.',
            {
                'root': {'type': 'string'},
                'limit': {'type': 'integer', 'minimum': 1, 'maximum': 100},
            },
        ),
        _tool(
            'p2p_project_structure_export_eligibility',
            (
                'Read-only export eligibility check for turning the active project '
                'structure into a portable vertical. Performs no draft, package, '
                'destination, project-structure or publication writes.'
            ),
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_structure_export_preview',
            (
                'Read-only export preview for the active project structure. Binds '
                'the exact source revision/checksum and export metadata but performs '
                'no draft, package, destination, project-structure or publication writes.'
            ),
            {
                'root': {'type': 'string'},
                'publisher': {'type': 'string'},
                'vertical_id': {'type': 'string'},
                'version': {'type': 'string'},
                'name': {'type': 'string'},
                'license': {'type': 'string'},
                'description': {'type': 'string'},
                'primary_domain': {
                    'type': 'object',
                    'properties': {
                        'key': {'type': 'string'},
                        'name': {'type': 'string'},
                        'source': {
                            'type': 'string',
                            'enum': ['local', 'external', 'imported', 'system'],
                        },
                        'external_ref': {'type': 'string'},
                    },
                    'required': ['key', 'name'],
                },
                'domain_tags': {'type': 'array', 'items': {'type': 'string'}},
                'lineage_mode': {'type': 'string', 'enum': ['derived', 'independent']},
                'parent_coordinate': {'type': 'string'},
                'parent_semantic_checksum': {'type': 'string'},
                'actor_id': {'type': 'string'},
                'executor_id': {'type': 'string'},
            },
            [
                'publisher',
                'vertical_id',
                'version',
                'name',
                'license',
                'primary_domain',
                'lineage_mode',
            ],
        ),
        _tool(
            'p2p_project_structure_replacement_inspect',
            (
                'Read-only inspection of an exact replacement target release. Resolves '
                'only bundled, local or cached releases and performs no acquire, receipt '
                'or project write.'
            ),
            {
                'root': {'type': 'string'},
                'target': {'type': 'string'},
            },
            ['target'],
        ),
        _tool(
            'p2p_project_structure_replacement_preview',
            (
                'Read-only comparison preview for replacing the project-owned structure '
                'from an exact release. Reports stable-ID comparison, readiness and memory '
                'impact without applying, acquiring or writing receipts.'
            ),
            {
                'root': {'type': 'string'},
                'target': {'type': 'string'},
                'expected_structure_revision': {'type': 'integer', 'minimum': 1},
                'expected_memory_revision': {'type': 'string'},
                'plan': {'type': 'object'},
                'actor_id': {'type': 'string'},
                'executor_id': {'type': 'string'},
                'executor_kind': {'type': 'string', 'enum': ['person', 'user', 'agent', 'mcp_client', 'client']},
                'limit': {'type': 'integer', 'minimum': 1, 'maximum': 1000},
            },
            ['target', 'expected_structure_revision', 'expected_memory_revision', 'actor_id'],
        ),
        _tool(
            'p2p_project_structure_merge_compare',
            (
                'Byte-invariant read-only comparison of an exact release or portable '
                'bundle with the current project structure. Computes strict stable-ID '
                'dependency closure and collisions without applying or writing a receipt.'
            ),
            {
                'root': {'type': 'string'},
                'source': {'type': 'string'},
                'selected': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'kind': {'type': 'string', 'enum': ['section', 'field', 'question', 'criterion', 'artifact']},
                            'id': {'type': 'string'},
                            'section_id': {'type': 'string'},
                        },
                        'required': ['kind', 'id'],
                        'additionalProperties': False,
                    },
                },
                'limit': {'type': 'integer', 'minimum': 1, 'maximum': 1000},
            },
            ['source'],
        ),
        _tool(
            'p2p_project_structure_retained_inspect',
            (
                'Read-only inspection of one retained canonical project-structure '
                'revision and its retention evidence. Performs no restore or mutation.'
            ),
            {
                'root': {'type': 'string'},
                'revision': {'type': 'integer', 'minimum': 1},
                'include_structure': {'type': 'boolean'},
            },
            ['revision'],
        ),
        _tool(
            'p2p_project_structure_add_section',
            'Consent-gated receipt-backed addition of one project-owned section.',
            {
                'root': {'type': 'string'},
                'title': {'type': 'string'},
                'section_id': {'type': 'string'},
                'description': {'type': 'string'},
                'required': {'type': 'boolean'},
                'expected_revision': {'type': 'integer', 'minimum': 1},
                'actor_id': {'type': 'string'},
                'executor_id': {'type': 'string'},
                'executor_kind': {'type': 'string', 'enum': ['person', 'user', 'agent', 'mcp_client', 'client']},
                'consent_id': {'type': 'string'},
                'operation_key': {'type': 'string'},
            },
            ['title', 'expected_revision', 'actor_id', 'consent_id', 'operation_key'],
        ),
        _tool(
            'p2p_project_structure_update_metadata',
            'Consent-gated receipt-backed metadata update preserving stable identity.',
            {
                'root': {'type': 'string'},
                'element_kind': {'type': 'string', 'enum': ['section', 'field', 'question', 'criterion', 'artifact']},
                'element_id': {'type': 'string'},
                'section_id': {'type': 'string'},
                'title': {'type': 'string'},
                'description': {'type': 'string'},
                'required': {'type': 'boolean'},
                'enabled': {'type': 'boolean'},
                'priority': {'type': 'string', 'enum': ['high', 'medium', 'low']},
                'keywords': {'type': 'array', 'items': {'type': 'string'}},
                'expected_revision': {'type': 'integer', 'minimum': 1},
                'actor_id': {'type': 'string'},
                'executor_id': {'type': 'string'},
                'executor_kind': {'type': 'string', 'enum': ['person', 'user', 'agent', 'mcp_client', 'client']},
                'consent_id': {'type': 'string'},
                'operation_key': {'type': 'string'},
            },
            ['element_kind', 'element_id', 'expected_revision', 'actor_id', 'consent_id', 'operation_key'],
        ),
        _tool(
            'p2p_project_structure_reorder_sections',
            'Consent-gated receipt-backed exact-set reorder of all active sections.',
            {
                'root': {'type': 'string'},
                'section_ids': {'type': 'array', 'items': {'type': 'string'}},
                'expected_revision': {'type': 'integer', 'minimum': 1},
                'actor_id': {'type': 'string'},
                'executor_id': {'type': 'string'},
                'executor_kind': {'type': 'string', 'enum': ['person', 'user', 'agent', 'mcp_client', 'client']},
                'consent_id': {'type': 'string'},
                'operation_key': {'type': 'string'},
            },
            ['section_ids', 'expected_revision', 'actor_id', 'consent_id', 'operation_key'],
        ),
        _tool(
            'p2p_project_structure_retirement_preview',
            'Preview governed retirement of structure elements and required memory dispositions.',
            {
                'root': {'type': 'string'},
                'targets': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'kind': {'type': 'string', 'enum': ['section', 'field', 'question', 'criterion', 'artifact']},
                            'id': {'type': 'string'},
                            'section_id': {'type': 'string'},
                        },
                        'required': ['kind', 'id'],
                    },
                },
                'expected_structure_revision': {'type': 'integer', 'minimum': 1},
                'expected_memory_revision': {'type': 'string'},
                'plan': {'type': 'object'},
                'actor_id': {'type': 'string'},
                'executor_id': {'type': 'string'},
                'executor_kind': {'type': 'string', 'enum': ['person', 'user', 'agent', 'mcp_client', 'client']},
                'limit': {'type': 'integer', 'minimum': 1, 'maximum': 1000},
            },
            ['targets', 'expected_structure_revision', 'expected_memory_revision', 'actor_id'],
        ),
        _tool(
            'p2p_project_structure_retirement_apply',
            'Consent-gated receipt-backed retirement of structure elements and resolved memory impacts.',
            {
                'root': {'type': 'string'},
                'targets': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'kind': {'type': 'string', 'enum': ['section', 'field', 'question', 'criterion', 'artifact']},
                            'id': {'type': 'string'},
                            'section_id': {'type': 'string'},
                        },
                        'required': ['kind', 'id'],
                    },
                },
                'expected_structure_revision': {'type': 'integer', 'minimum': 1},
                'expected_memory_revision': {'type': 'string'},
                'preview_token': {'type': 'string'},
                'plan': {'type': 'object'},
                'confirm': {'type': 'boolean'},
                'actor_id': {'type': 'string'},
                'executor_id': {'type': 'string'},
                'executor_kind': {'type': 'string', 'enum': ['person', 'user', 'agent', 'mcp_client', 'client']},
                'consent_id': {'type': 'string'},
                'operation_key': {'type': 'string'},
                'limit': {'type': 'integer', 'minimum': 1, 'maximum': 1000},
            },
            [
                'targets',
                'expected_structure_revision',
                'expected_memory_revision',
                'preview_token',
                'actor_id',
                'consent_id',
                'operation_key',
            ],
        ),
        _tool(
            'p2p_project_memory_classification',
            (
                'Read bounded project-memory organization against the canonical project '
                'structure. This is separate from readiness and never mutates state.'
            ),
            {
                'root': {'type': 'string'},
                'limit': {'type': 'integer', 'minimum': 1, 'maximum': 4096},
            },
        ),
        _tool(
            'p2p_canonical_memory_inspect',
            (
                'Read the fail-closed classification of every durable .p2p artifact. '
                'This exposes storage-neutral portability decisions and performs no mutation.'
            ),
            {
                'root': {'type': 'string'},
                'limit': {'type': 'integer', 'minimum': 1, 'maximum': 100000},
            },
        ),
        _tool(
            'p2p_canonical_memory_verify',
            'Verify canonical entities, relations, lineage, identity and managed blobs without writing.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_bundle_export_metadata',
            (
                'Compute deterministic canonical-bundle metadata and archive digest in memory. '
                'No archive or project file is written.'
            ),
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_archive_verify',
            'Verify a canonical bundle or physical backup independently without activating it.',
            {
                'root': {'type': 'string'},
                'source': {'type': 'string'},
            },
            ['source'],
        ),
        _tool(
            'p2p_proposal_scope_show',
            'Read one proposal explicit sections, project-global or unassigned memory scope.',
            {
                'root': {'type': 'string'},
                'proposal_id': {'type': 'string'},
            },
            ['proposal_id'],
        ),
        _tool(
            'p2p_proposal_scope_set',
            (
                'Consent-gated receipt-backed atomic assignment of proposal memory scope. '
                'Requires current memory and structure revisions.'
            ),
            {
                'root': {'type': 'string'},
                'proposal_id': {'type': 'string'},
                'kind': {'type': 'string', 'enum': ['sections', 'project_global', 'unassigned']},
                'section_ids': {'type': 'array', 'items': {'type': 'string'}},
                'expected_memory_revision': {'type': 'string'},
                'expected_structure_revision': {'type': 'integer', 'minimum': 1},
                'actor_id': {'type': 'string'},
                'executor_id': {'type': 'string'},
                'executor_kind': {'type': 'string', 'enum': ['person', 'user', 'agent', 'mcp_client', 'client']},
                'consent_id': {'type': 'string'},
                'operation_key': {'type': 'string'},
            },
            [
                'proposal_id',
                'kind',
                'expected_memory_revision',
                'expected_structure_revision',
                'actor_id',
                'consent_id',
                'operation_key',
            ],
        ),
        _tool(
            'p2p_project_rubrics_init',
            (
                'Write-safe project setup tool: create deterministic project definition rubrics '
                'from the generic or empty starter. Does not change project classification.'
            ),
            {'root': {'type': 'string'},
             'starter': {'type': 'string', 'enum': ['generic', 'empty']},
             'force': {'type': 'boolean'}},
        ),
        _tool(
            'p2p_project_rubrics_show',
            'Read configured project definition maturity rubrics.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_maturity_refresh',
            (
                'Write-safe analysis tool: generate deterministic project definition maturity '
                'from configured rubrics. Does not assess implementation completeness.'
            ),
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_maturity_show',
            'Read stored project definition maturity assessment.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_intake_prompt',
            (
                'Write-safe draft tool: create an intake prompt for a raw idea. Does not apply '
                'recommendations or make governance decisions.'
            ),
            {'root': {'type': 'string'}, 'idea': {'type': 'string'}},
            ['idea'],
        ),
        _tool(
            'p2p_intake_status',
            'List intake records and whether analysis artifacts are populated.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_brief_prompt',
            (
                'Advisory workflow tool: create project brief context and prompt artifacts from '
                'current project state. Does not import or decide.'
            ),
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_brief_show',
            'Show the stored operational project brief if one has been imported.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_choice_discover',
            (
                'Advisory analysis tool: discover choice candidates and blockers without '
                'creating, deciding, blocking, or unblocking choices.'
            ),
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_conflict_status',
            'Read recorded project conflicts without recording new conflicts.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_governance_status',
            'Read governance status without mutating governance artifacts.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_governance_validate',
            'Read-only governance artifact validation with structured diagnostics.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_choice_governance_preflight',
            (
                'Read-only governance preflight for a choice. Returns warnings, blockers, '
                'votes, and deterministic precedent evidence without deciding the choice.'
            ),
            {'root': {'type': 'string'},
             'choice_id': {'type': 'string'},
             'option': {'type': 'string'},
             'actor': {'type': 'string'},
             'precedent_id': {'type': 'string'},
             'tag': {'type': 'string'}},
            ['choice_id', 'option', 'actor'],
        ),
        _tool(
            'p2p_vote_status',
            'Read proposal-local governance vote counts without recording votes.',
            {'root': {'type': 'string'}, 'proposal_id': {'type': 'string'}},
            ['proposal_id'],
        ),
        _tool(
            'p2p_precedent_search',
            (
                'Read deterministic governance precedent matches by explicit precedent id, '
                'proposal id, choice id, or tag. Does not use fuzzy matching or record precedents.'
            ),
            {'root': {'type': 'string'},
             'precedent_id': {'type': 'string'},
             'proposal_id': {'type': 'string'},
             'choice_id': {'type': 'string'},
             'tag': {'type': 'string'}},
        ),
        _tool(
            'p2p_workspace_schema_status',
            'Read workspace schema layout, semantic alignment and recovery status without mutation.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_proposal_vertical_coverage_show',
            (
                'Read transitional pre-rebase vertical coverage without mutation. '
                'This artifact cannot classify project memory or satisfy the decision gate.'
            ),
            {'root': {'type': 'string'}, 'proposal_id': {'type': 'string'}},
            ['proposal_id'],
        ),
        _tool(
            'p2p_proposal_vertical_coverage_suggest',
            (
                'Suggest transitional vertical mappings with heuristic evidence. '
                'Suggestions never create project-memory scope or authoritative state.'
            ),
            {'root': {'type': 'string'}, 'proposal_id': {'type': 'string'}},
            ['proposal_id'],
        ),
        _tool(
            'p2p_project_status',
            'Show deterministic P2P project state status.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_progress',
            'Read independent project definition and declared evidence progress axes without mutation.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_freshness',
            'Read derived-state freshness nodes and ordered rebuild actions without mutation.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_interaction_style_show',
            'Read effective project interaction style values and scale descriptions.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_interaction_style_set',
            (
                'Write-safe project configuration tool: set project interaction style values. '
                'Does not make governance decisions or authorize direct filesystem writes.'
            ),
            {'root': {'type': 'string'},
             'technical_verbosity': {'type': 'integer', 'minimum': 0, 'maximum': 5},
             'formality': {'type': 'integer', 'minimum': 0, 'maximum': 5},
             'assertiveness': {'type': 'integer', 'minimum': 0, 'maximum': 5},
             'actor': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_export',
            (
                'Write-safe deterministic tool: export the visible human-facing project '
                'definition to outputs/latest/project.md. Does not mutate P2P governance state.'
            ),
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_export_status',
            'Read visible project definition export status and review snapshots.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_publish_prepare',
            (
                'Write-safe deterministic tool: prepare one language edition and the shared '
                'publication evidence index under outputs/latest. Does not mutate governance state.'
            ),
            {
                'root': {'type': 'string'},
                'language': {'type': 'string'},
                'output_name': {'type': 'string'},
                'contributions': {'type': 'string', 'enum': ['auto', 'include', 'omit']},
            },
        ),
        _tool(
            'p2p_project_publish_import',
            (
                'Write-safe deterministic tool: atomically import a curated Markdown, project '
                'model, and evidence-accounting candidate for one language edition.'
            ),
            {
                'root': {'type': 'string'},
                'source': {'type': 'string'},
                'model': {'type': 'string'},
                'evidence_accounting': {'type': 'string'},
                'language': {'type': 'string'},
                'output_name': {'type': 'string'},
            },
            ['source'],
        ),
        _tool(
            'p2p_project_publish_validate',
            (
                'Write-safe deterministic tool: validate one publication edition and its '
                'model/evidence bindings.'
            ),
            {
                'root': {'type': 'string'},
                'language': {'type': 'string'},
                'output_name': {'type': 'string'},
            },
        ),
        _tool(
            'p2p_project_publish_render',
            (
                'Write-safe deterministic tool: render one validated publication edition when '
                'the optional PDF capability is installed.'
            ),
            {
                'root': {'type': 'string'},
                'language': {'type': 'string'},
                'output_name': {'type': 'string'},
            },
        ),
        _tool(
            'p2p_project_publish_status',
            'Read one human project publication edition status.',
            {
                'root': {'type': 'string'},
                'language': {'type': 'string'},
                'output_name': {'type': 'string'},
            },
        ),
        _tool(
            'p2p_project_publish_list',
            'List committed publication editions without rebuilding or repairing publication state.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_vertical_list',
            'Read available project vertical packs and active/fallback status.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_vertical_show',
            'Read a project vertical pack, including inherited base-project sections.',
            {'root': {'type': 'string'}, 'vertical_id': {'type': 'string'}},
            ['vertical_id'],
        ),
        _tool(
            'p2p_project_vertical_validate',
            'Read-only validation tool: validate a project vertical ID, vertical.yml path, or pack directory.',
            {'root': {'type': 'string'}, 'target': {'type': 'string'}},
            ['target'],
        ),
        _tool(
            'p2p_project_vertical_select',
            (
                'Write-safe project setup tool: select the active project vertical. '
                'Does not accept, reject, or change proposals.'
            ),
            {'root': {'type': 'string'},
             'vertical_id': {'type': 'string'},
             'actor': {'type': 'string'},
             'profile': {'type': 'string'},
             'modules': {'type': 'array', 'items': {'type': 'string'}}},
            ['vertical_id'],
        ),
        _tool(
            'p2p_project_vertical_lock_show',
            'Read project vertical lock status without repairing or mutating project state.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_vertical_lock_repair',
            (
                'Write-safe project setup tool: repair or create vertical.lock.yml from '
                'active vertical state. Does not make governance decisions.'
            ),
            {'root': {'type': 'string'}, 'actor': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_context',
            'Read JSON-ready project vertical context, lock, rubric, and definition-state summary.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_sections',
            'Read sections for the active or specified project vertical.',
            {'root': {'type': 'string'}, 'vertical_id': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_section_show',
            'Read one section for the active or specified project vertical.',
            {'root': {'type': 'string'}, 'section_id': {'type': 'string'}, 'vertical_id': {'type': 'string'}},
            ['section_id'],
        ),
        _tool(
            'p2p_project_definition_show',
            'Read durable project definition state without mutating project state.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_definition_update',
            (
                'Write-safe project definition tool: apply a structured definition patch file. '
                'Does not edit governance decisions or arbitrary YAML.'
            ),
            {'root': {'type': 'string'}, 'patch': {'type': 'string'}},
            ['patch'],
        ),
        _tool(
            'p2p_next',
            'Show advisory next actions from P2P project state.',
            {'root': {'type': 'string'}, 'top': {'type': 'integer', 'minimum': 1}},
        ),
        _tool(
            'p2p_next_add',
            (
                'Write-safe project planning tool: add a curated next action. Does not decide '
                'governance, publish, merge, or run external provider operations.'
            ),
            {'root': {'type': 'string'},
             'kind': {'type': 'string'},
             'target': {'type': 'string'},
             'reason': {'type': 'string'},
             'command': {'type': 'string'},
             'priority': {'type': 'string'},
             'action_id': {'type': 'string'}},
            ['kind', 'reason'],
        ),
        _tool(
            'p2p_next_complete',
            (
                'Write-safe project planning tool: complete a curated next action and move it '
                'to the next-action audit log.'
            ),
            {'root': {'type': 'string'},
             'action_id': {'type': 'string'},
             'reason': {'type': 'string'}},
            ['action_id', 'reason'],
        ),
        _tool(
            'p2p_next_retire',
            (
                'Write-safe project planning tool: retire a curated next action and move it to '
                'the next-action audit log.'
            ),
            {'root': {'type': 'string'},
             'action_id': {'type': 'string'},
             'reason': {'type': 'string'}},
            ['action_id', 'reason'],
        ),
        _tool(
            'p2p_next_refresh',
            (
                'Write-safe project planning tool: normalize curated next actions and report '
                'generated action count.'
            ),
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_registry_status',
            'Show generated registry availability and freshness checks.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_registry_show',
            'Show a generated P2P registry.',
            {'root': {'type': 'string'}, 'name': {'type': 'string'}},
            ['name'],
        ),
        _tool(
            'p2p_project_memory_status',
            'Show read-only vertical project-memory state and freshness.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_memory_show',
            'Show bounded aggregate or exact-section vertical project memory without refreshing it.',
            {'root': {'type': 'string'},
             'section': {'type': 'string'},
             'include_history': {'type': 'boolean'},
             'limit': {'type': 'integer', 'minimum': 1, 'maximum': 100},
             'cursor': {'type': 'string'}},
        ),
        _tool(
            'p2p_project_show',
            'Show a generated project definition section or feature document.',
            {'root': {'type': 'string'}, 'section': {'type': 'string'}},
            ['section'],
        ),
        _tool(
            'p2p_permissions_show',
            'Read project-declared permission identities and role policy.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_consent_request',
            (
                'Write-safe consent workflow tool: record a pending consent request for an '
                'owner-controlled operation. Does not grant consent and cannot authorize '
                'execution.'
            ),
            {'root': {'type': 'string'},
             'operation': {'type': 'string'},
             'target': {'type': 'string'},
             'actor_id': {'type': 'string'},
             'requested_by': {'type': 'string'},
             'scope': {'type': 'string'},
             'expires_on': {'type': 'string'}},
            ['operation', 'target', 'actor_id'],
        ),
        _tool(
            'p2p_consent_status',
            'List permission-gated consent receipts without creating or consuming them.',
            {'root': {'type': 'string'}},
        ),
        _tool(
            'p2p_consent_show',
            'Show one permission-gated consent receipt without creating or consuming it.',
            {'root': {'type': 'string'}, 'consent_id': {'type': 'string'}},
            ['consent_id'],
        ),
    ]
