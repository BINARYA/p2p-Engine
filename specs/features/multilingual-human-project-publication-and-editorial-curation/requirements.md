# Requirements - Multilingual Human Project Publication And Editorial Curation

## Status And Origin

- Status: implementation specification, not yet implemented.
- Governing foundation: the accepted Human Project Publication Pipeline already
  implemented from `PROP-099`.
- This feature corrects the editorial and artifact contracts of that pipeline;
  it does not replace P2P project governance and does not create a new workspace
  schema.
- Workspace schema remains v3. Versions introduced here belong only to derived
  publication profiles, evidence indexes, manifests, models, validators, and
  agent templates.
- Default publication language is English. Other languages are explicit
  coexisting editions of the same project substance, not audience variants.

## Current Behavior To Correct

The current implementation has a sound staged prepare/import/validate/render/
review lifecycle, hash provenance, safe import boundary, optional PDF renderer,
CLI surface, and MCP parity. The following behavior is no longer the intended
product contract:

- `curator-input.md` embeds the complete proposal-oriented export and therefore
  encourages the curator to mirror proposal history instead of understanding
  the project;
- the publication profile resolves language to `project_default` and every
  stage writes one unsuffixed path, so two languages overwrite each other;
- the skill requires visible proposal, decision, Change Set, Work, state, and
  source-of-truth references in the reader document;
- the validator requires the exact English heading `Executive Summary` and a
  visible `.p2p/` authority statement even for a non-English document;
- deterministic validation can pass a proposal dump with only a warning;
- the curator is told to distinguish workflow and governance states that are
  not part of the final reader's concern;
- import accepts a Markdown file but has no structured project model or complete
  evidence-accounting contract;
- the renderer hard-codes `<html lang="it">` and fixed `project.pdf` output;
- the publication service has no deterministic contributor-share input for an
  optional Contributions chapter.

## Product Objective

Transform complete governed project evidence into a coherent, detailed,
standalone document for a reader who:

- does not know P2P Engine's planning method;
- does not initially know P2P's internal planning artifacts or workflow and must
  not need that knowledge to follow the document;
- needs to understand the project, its purpose, structure, behavior, boundaries,
  important uncertainties, and vertical-specific substance;
- is interested in project content rather than the upstream process used to
  produce it.

The target flow is:

```text
complete governed evidence
  -> vertical-aware evidence index
  -> curator-built project model and evidence accounting
  -> reader-oriented autonomous document
  -> deterministic contract validation
  -> language-specific Markdown/PDF edition
  -> optional owner publication review for that edition
```

The complete generated export remains available as audit evidence. It is not
the outline, chapter model, or prose template for the publication.

## Core Principles

1. **Project first:** the publication explains the project, not P2P's workflow.
2. **Vertical aware:** the active vertical determines the questions the
   publication must answer, but does not impose a fixed global chapter list.
3. **Evidence complete:** every indexed evidence unit is accounted for, even
   when it is historical, duplicated, contradictory, process-only, or excluded.
4. **Reader autonomous:** removing internal IDs, paths, hashes, and citations
   must not make the document unintelligible.
5. **One project substance, many languages:** language editions may coexist;
   audience, investor, commercial, technical, or executive variants remain out
   of scope.
6. **Governance internal:** governance authority may select current evidence,
   but governance status is not publication content.
7. **Traceability outside the prose:** provenance and claim-to-evidence links
   live in derived sidecars and manifests by default.
8. **No implicit external knowledge:** the curator may use only the prepared
   packet, referenced repository evidence, and explicit owner input.
9. **Honest automation:** deterministic validators enforce deterministic
   contracts; they do not claim to prove editorial or semantic quality.
10. **Derived-state isolation:** publication artifacts never become canonical
    P2P memory and never alter workspace governance.

## Terminology

- **Publication model:** a structured, curator-authored representation of the
  project's thesis, reader questions, claims, vertical coverage, outline, and
  claim-to-evidence links.
- **Evidence index:** a deterministic complete catalog of evidence available to
  the curator, grouped by active vertical and editorial role.
- **Evidence accounting:** the curator's disposition for every indexed evidence
  unit and its relationship to publication-model claims.
- **Edition:** one language-specific rendering of the shared project substance.
- **Output name:** a safe user-selected base name, default `project`.
- **Language tag:** a normalized BCP 47 language tag, default `en`.
- **Edition key:** `<output-name>-<path-language>`, for example `project-en`,
  `project-it`, or `outputxyz-en`.
- **Reader document:** the final language-specific Markdown/PDF; it excludes
  P2P workflow narration and internal traceability syntax.
- **Publication review:** an optional approval of one rendered edition. It is
  derived publication state, not project governance authority.

## Exact Artifact Contract

Shared source artifacts:

```text
outputs/latest/project.md
outputs/latest/publication-evidence.yml
outputs/latest/publications.yml
```

Per-edition prepared and imported artifacts:

```text
outputs/latest/publications/<edition-key>/profile.yml
outputs/latest/publications/<edition-key>/curator-input.md
outputs/latest/publications/<edition-key>/manifest.yml
outputs/latest/publications/<edition-key>/project-model.yml
outputs/latest/publications/<edition-key>/evidence-accounting.yml
outputs/latest/publications/<edition-key>/validation.yml
outputs/latest/publications/<edition-key>/review.yml
outputs/latest/<edition-key>.md
outputs/latest/<edition-key>.pdf
```

Exact curator candidate paths:

```text
drafts/project-publication/<edition-key>.md
drafts/project-publication/<edition-key>.model.yml
drafts/project-publication/<edition-key>.evidence.yml
```

For example, `--output-name outputxyz --language en` produces
`outputs/latest/outputxyz-en.md` and `outputs/latest/outputxyz-en.pdf`. Preparing
or rendering `outputxyz-it` must not modify the English edition.

## Scope

### In Scope

- versioned publication edition identity and path contracts;
- English default and selectable normalized language tags;
- simultaneous language editions with independent lifecycle state;
- complete vertical-aware evidence indexing without fixed-count truncation;
- a structured publication model and complete evidence accounting;
- revised modular `p2p-project-curator` release templates and generated adapter
  resources;
- exact candidate paths and atomic multi-artifact import;
- deterministic contribution-share calculation for an optional Contributions
  chapter;
- language-aware rendering and edition-scoped review;
- CLI, MCP, facade, documentation, package, and compatibility updates;
- explicit treatment of legacy unsuffixed publication artifacts;
- tests, forward evaluations, provenance, performance limits, and final
  repository alignment analysis.

### Out Of Scope

- workspace schema v4 or a `.p2p` migration;
- changing proposal, decision, Change Set, Work, or project-readiness semantics;
- using publication output as governance evidence;
- deterministic machine translation;
- model-provider execution inside the CLI;
- audience-specific, investor, commercial, executive, or role-specific
  publication variants;
- branded themes beyond the existing neutral renderer;
- inferring implementation status from proposal acceptance, Change Set state,
  source-code presence, or missing evidence;
- measuring contributor effort, quality, merit, ownership, authorship rights,
  or intellectual property;
- silently approving a translated or regenerated edition because another
  edition was approved;
- deleting legacy publication files automatically.

## Functional Requirements

### A - Edition Identity, Language, And Paths

- A-R001: THE default publication language SHALL be `en`.
- A-R002: EVERY publication command that targets an edition SHALL accept a
  language tag and output name, with defaults `en` and `project`.
- A-R003: LANGUAGE normalization SHALL trim whitespace, replace `_` with `-`,
  normalize BCP 47 casing, map `eng` to `en` and `ita` to `it`, reject path
  separators and invalid tags, and expose both canonical and path-safe forms.
- A-R004: OUTPUT names SHALL match a documented ASCII slug contract, SHALL NOT
  contain path separators, extensions, `.`/`..` segments, control characters,
  or reserved publication metadata names, and SHALL be at most 64 characters.
- A-R005: EDITION identity SHALL be the immutable pair `(output_name,
  canonical_language)` and its path key SHALL be deterministic.
- A-R006: TWO different edition identities SHALL never resolve to the same
  writable artifact path.
- A-R007: PREPARE, import, validate, render, review, and status SHALL operate on
  one explicit edition; list/status-all MAY aggregate editions without mutating
  them.
- A-R008: PREPARING or writing one edition SHALL NOT invalidate another edition
  unless a shared source/evidence fingerprint changed.
- A-R009: THE publication catalog SHALL list all known editions in stable order
  and bind each key to language, output name, manifest path, and current stage
  summary.
- A-R010: LANGUAGE selection SHALL NOT create a new audience or purpose variant;
  every edition SHALL represent the same project scope and editorial model
  contract.

### B - Complete Evidence And Vertical-Aware Project Model

- B-R001: PREPARE SHALL generate a deterministic, versioned
  `publication-evidence.yml` from a request-consistent project snapshot.
- B-R002: THE evidence source catalog SHALL include all governed source classes
  that can affect project publication, including project definition, active
  vertical and section metadata, vertical project memory, active cross-cutting
  evidence, historical/superseded context, risks, assumptions, open project
  questions, recorded contributions, and process-only records needed for
  completeness accounting.
- B-R003: THE evidence index SHALL assign stable semantic evidence IDs and SHALL
  preserve source path, physical or semantic hash, authority class, vertical
  section IDs where known, evidence kind, editorial eligibility, and either the
  complete normalized semantic payload or an explicit complete source locator.
  A generated summary/snippet SHALL NOT be the sole evidence representation.
- B-R004: THE index SHALL distinguish active project evidence, cross-cutting
  active evidence, historical context, unresolved contradictory evidence,
  duplicated evidence, insufficient evidence, and process-only metadata.
- B-R005: ACTIVE evidence without declared vertical coverage SHALL be retained
  as cross-cutting/unmapped evidence and SHALL NOT be silently discarded.
- B-R006: HISTORICAL, revoked, superseded, deferred, or otherwise non-current
  material SHALL remain available for curator reasoning but SHALL NOT be stated
  as current project substance.
- B-R007: PROCESS-ONLY metadata SHALL be deterministically pre-disposed as
  process-only and SHALL NOT require the curator to reproduce it in reader prose.
- B-R008: THE evidence index SHALL not use a first-N proposal limit. If reading
  is paged, pagination SHALL be stable, complete, and report total/remaining
  counts.
- B-R009: THE complete source export SHALL remain available by path and hash but
  SHALL NOT be embedded wholesale in the curator packet.
- B-R010: THE curator packet SHALL identify the active vertical, vertical
  version, required sections, project definition state, evidence-index path and
  hash, complete-export path and hash, and exact candidate output paths.
- B-R011: THE publication model SHALL contain one project thesis, explicit
  reader questions, vertical framing, claim records, adaptive outline records,
  relevant uncertainties, and evidence links.
- B-R012: EVERY material publication-model claim SHALL reference one or more
  indexed evidence IDs or be marked as explicit owner-supplied input with
  provenance.
- B-R013: EVERY indexed evidence ID SHALL have exactly one accounting
  disposition: `used`, `supporting_context`, `historical`, `duplicate`,
  `contradictory`, `insufficient`, `not_applicable`, or `process_only`.
- B-R014: USED evidence SHALL reference at least one model claim; excluded
  evidence SHALL include a concise reason.
- B-R015: THE model and evidence accounting SHALL bind to the edition key,
  packet hash, evidence-index hash, source-export hash, and source fingerprint.
- B-R016: THE model SHALL be structurally independent of proposal chronology and
  SHALL organize content around the active vertical and the project's own
  concepts.
- B-R017: VERTICAL required sections SHALL act as completeness questions, not as
  mandatory publication headings; the model SHALL record how every applicable
  required section is covered, combined, deferred for missing evidence, or not
  applicable.
- B-R018: A project with no active valid vertical SHALL use an explicit generic
  project model and SHALL record that vertical guidance was unavailable.

### C - Editorial Curation Contract

- C-R001: THE curator SHALL treat the evidence index, referenced source
  artifacts, active vertical, and explicit owner input as the complete allowed
  knowledge boundary.
- C-R002: THE curator SHALL NOT introduce facts, brands, products, repositories,
  organizations, or domain assumptions from implicit memory or adjacent
  projects.
- C-R003: THE curator SHALL inspect and account for every evidence-index entry
  before finalizing the model; reading order MAY be progressive and
  vertical-grouped.
- C-R004: THE curator SHALL build the project model before writing the reader
  document.
- C-R005: THE reader document SHALL explain the project as an autonomous work,
  not as a summary of proposals or artifacts.
- C-R006: THE reader document SHALL use the selected language consistently,
  except for project names, code, domain terms, or quotations that legitimately
  remain in another language.
- C-R007: HEADINGS and chapter order SHALL be adaptive to the project and active
  vertical. No fixed nineteen-section, proposal-by-proposal, or governance
  outline is allowed.
- C-R008: THE document SHALL be sufficiently detailed for a reader to understand
  purpose, value, shape, behavior, boundaries, significant risks/assumptions,
  and vertical-specific content supported by evidence.
- C-R009: THE document SHALL NOT teach or narrate P2P workflow, proposal states,
  decision events, readiness calculations, Change Set lifecycle, Work lifecycle,
  source fingerprints, import stages, or publication pipeline mechanics merely
  as the upstream process that produced the project. If one of these concepts is
  itself part of the project's subject matter, the document MAY explain it as a
  project capability using reader-oriented definitions and supporting evidence.
- C-R010: INTERNAL IDs, artifact paths, hashes, and traceability notes SHALL be
  absent from the normal reader body. A future explicit technical appendix is
  not enabled by default and is not required by this feature.
- C-R011: GOVERNANCE state SHALL be used only to select and classify evidence;
  it SHALL NOT be presented as a project feature, chapter, timeline, or status
  table. This restriction applies to upstream provenance; it does not erase a
  governance capability when governance is explicitly part of the project being
  documented.
- C-R012: IMPLEMENTATION state SHALL be stated only when explicit domain evidence
  supports it. Acceptance, missing implementation evidence, Change Set state,
  or source-code presence alone SHALL NOT establish implementation state.
- C-R013: MATERIAL unresolved contradictions or uncertainties SHALL be expressed
  in reader language as project uncertainties only when they affect project
  comprehension; their workflow history SHALL remain in sidecars.
- C-R014: THE final document SHALL pass a citation-erasure/autonomy review: its
  meaning and structure must survive removal of technical traceability data.
- C-R015: THE skill SHALL use progressive disclosure: a concise `SKILL.md` and
  one-level `references/` resources for workflow, model/evidence contracts,
  vertical interpretation, and editorial rubric.
- C-R016: RELEASE template sources SHALL own every generated curator resource;
  `.agents/`, `.codex/`, and embedded adapter instructions remain generated
  outputs managed through the agent lifecycle.
- C-R017: THE curator SHALL write only the exact candidate triplet declared by
  the packet and SHALL NOT write directly to canonical `outputs/latest` edition
  paths.
- C-R018: THE curator SHALL complete an editorial self-assessment against the
  versioned rubric without representing that assessment as deterministic proof.

### D - Contributions Chapter

- D-R001: THE profile SHALL support `contributions: auto|include|omit`, default
  `auto`.
- D-R002: CONTRIBUTOR shares SHALL be computed deterministically from explicitly
  recorded contribution records associated with current authoritative project
  evidence; historical/process-only records SHALL be excluded.
- D-R003: AUTHOR identity SHALL use the recorded author after Unicode NFC and
  whitespace normalization. The system SHALL NOT silently merge distinct names
  by case, alias, email, or guessed identity.
- D-R004: MISSING/blank authors SHALL be grouped as `Unattributed` and retained
  in the denominator.
- D-R005: PERCENTAGES SHALL use record counts and a deterministic largest-
  remainder basis-point allocation so displayed shares total exactly 100.00%.
- D-R006: TIES SHALL sort by normalized display name after descending count.
- D-R007: THE contribution summary SHALL include count, percentage, denominator,
  source fingerprint, scope statement, and an explicit limitation that the
  metric is not effort, quality, merit, ownership, code authorship, or IP.
- D-R008: `auto` SHALL include the chapter only when at least one attributed
  contribution exists; otherwise the chapter SHALL be omitted with an internal
  advisory.
- D-R009: `include` with no attributed records SHALL fail preparation or
  validation with a clear insufficient-data diagnostic; `omit` SHALL never add
  the chapter.
- D-R010: WHEN present, the chapter SHALL be titled naturally in the selected
  language and SHALL contain project contributor shares only, without proposal
  or governance breakdowns.

### E - Import, Provenance, And Freshness

- E-R001: IMPORT SHALL consume a Markdown candidate, publication-model YAML, and
  evidence-accounting YAML for exactly one prepared edition.
- E-R002: THE default candidate paths SHALL be those declared in the packet;
  explicit alternative source paths SHALL remain inside the repository, outside
  `.p2p/`, outside canonical edition targets, and be reported in provenance.
- E-R003: IMPORT SHALL require UTF-8 Markdown, duplicate-key-safe YAML, supported
  model/accounting versions, exact edition binding, and current packet/source/
  evidence/profile hashes.
- E-R004: IMPORT SHALL reject missing evidence IDs, unknown evidence IDs,
  duplicate dispositions, used evidence without claims, claims without evidence,
  and an edition language/output-name mismatch.
- E-R005: IMPORT SHALL stage all target files, write each file atomically, and
  commit the edition manifest last. A failed import SHALL leave the prior current
  edition readable or the new edition explicitly incomplete, never partially
  current.
- E-R006: THE edition manifest SHALL bind every stage to content hashes,
  contract versions, edition identity, source fingerprint, evidence-index hash,
  packet hash, profile hash, model hash, and accounting hash.
- E-R007: SHARED source/evidence change SHALL stale every dependent edition;
  edition profile/model/Markdown changes SHALL stale only that edition's later
  stages.
- E-R008: MANUAL modification of imported Markdown, model, accounting,
  validation, PDF, or review SHALL be detected by hash and reported without
  silently overwriting the file during a read.
- E-R009: REPEATING prepare or import with byte-equivalent inputs SHALL be
  idempotent and SHALL avoid unnecessary rewrites where current atomic-write
  conventions permit.
- E-R010: STATUS SHALL distinguish missing, ready, stale, invalid,
  legacy-contract, and interrupted/incomplete stages with explicit reasons.
- E-R011: THE publication source fingerprint SHALL reuse request-scoped project
  snapshots and current vertical-memory/registry manifests where possible; it
  SHALL NOT reintroduce proposal-count-squared or repeated full-workspace reads.
- E-R012: PUBLICATION artifacts SHALL remain derived and SHALL never be read as
  project governance or vertical-definition authority.

### F - Deterministic Validation And Editorial Evaluation

- F-R001: VALIDATION SHALL verify the edition path, language/profile binding,
  manifest chain, model schema, evidence-accounting completeness, contribution
  summary, Markdown hash, and supported contract versions.
- F-R002: MARKDOWN contract errors SHALL include missing/empty document,
  incorrect H1 count, unclosed fences, invalid encoding, unsafe paths, and
  internal proposal/decision/Change Set/Work traceability IDs in reader prose.
- F-R003: THE validator SHALL NOT require an exact English heading for a
  non-English edition and SHALL NOT require a visible `.p2p/` source-of-truth
  statement in the reader document.
- F-R004: LANGUAGE mismatch, weak vertical framing, probable workflow narration,
  placeholder text, fixed proposal chronology, suspicious contribution figures,
  and chapter imbalance SHALL be warnings/advisories unless a deterministic
  contract violation exists.
- F-R005: VALIDATOR findings SHALL retain `error`, `warning`, and `advisory`
  severities, stable codes, paths, and line locations where practical.
- F-R006: ONLY deterministic `error` findings SHALL block render.
- F-R007: THE validator SHALL describe semantic/editorial checks as heuristics;
  it SHALL NOT claim to prove factual completeness, prose quality, translation
  quality, or vertical adequacy.
- F-R008: A separate versioned editorial rubric SHALL evaluate project autonomy,
  vertical coherence, evidence use, unsupported claims, governance-noise
  absence, language consistency, contribution accuracy, structure, and reader
  usefulness.
- F-R009: FEATURE acceptance SHALL include forward evaluations on at least a
  software project, a board-game project, and a custom/unknown vertical project.
- F-R010: FORWARD evaluations SHALL include an isolation fixture containing an
  unrelated recognizable brand/project name and SHALL fail if the curated model
  imports that external context without evidence.

### G - Rendering, Review, Interfaces, And Compatibility

- G-R001: RENDER SHALL consume only a passed current validation for the selected
  edition and SHALL write `outputs/latest/<edition-key>.pdf` atomically.
- G-R002: RENDERED HTML SHALL set the canonical selected language in `lang`, use
  the model's project title, and preserve neutral renderer behavior.
- G-R003: RENDERING one edition SHALL NOT read, overwrite, approve, or stale
  another edition.
- G-R004: PUBLICATION review SHALL bind to one edition's current Markdown, PDF,
  validation, model, and evidence-accounting hashes.
- G-R005: APPROVAL SHALL be edition-specific. Approval of English SHALL NOT
  approve Italian or a regenerated English document.
- G-R006: REVIEW SHALL remain owner-controlled publication state and SHALL NOT be
  represented as P2P project governance authority.
- G-R007: CLI prepare/import/validate/render/review/status SHALL expose
  `--language` and `--output-name`; prepare SHALL expose `--contributions`.
- G-R008: CLI SHALL add a read-only edition list/status-all surface with stable
  ordering and machine-readable JSON.
- G-R009: MCP publication tools SHALL accept equivalent `language`,
  `output_name`, and contribution-policy fields; write-safe operations SHALL
  remain derived-output operations.
- G-R010: OWNER publication review SHALL remain unavailable through MCP unless a
  separate explicit owner-authority design is approved.
- G-R011: WORKSPACE facades and service APIs called without edition arguments
  SHALL default to `(project, en)` for source compatibility.
- G-R012: CURRENT workspace schema v3 SHALL remain valid and SHALL require no
  workspace migration for this feature.
- G-R013: DERIVED publication contracts SHALL advance independently to explicit
  version 2 identities; the number `2` SHALL never be reported as workspace
  schema version.
- G-R014: EXISTING unsuffixed publication artifacts SHALL be detected and
  reported as `legacy-contract`; they SHALL NOT be silently treated as a current
  v2 edition or carry approval into a new edition.
- G-R015: FOR one documented compatibility window, successful writes to the
  default `(project, en)` edition MAY refresh `project.curated.md` and
  `project.pdf` as recorded derived aliases. The new suffixed edition remains
  authoritative for publication status and aliases SHALL never be inputs.
- G-R016: NON-default editions SHALL never create or update unsuffixed aliases.
- G-R017: AGENT install/update/doctor/uninstall SHALL own the revised skill and
  all reference resources for supported adapters without deleting unrelated
  adapter files.
- G-R018: DOCUMENTATION SHALL explain the reader-document boundary, default and
  selected language behavior, exact paths, candidate workflow, contribution
  metric, legacy handling, and edition-specific approval.
- G-R019: PACKAGE and installed-artifact tests SHALL prove release templates,
  reference resources, CLI/MCP schemas, optional PDF behavior, and Python 3.11
  compatibility from wheel and sdist.
- G-R020: FINAL repository alignment SHALL be a separate owner-confirmed gate
  that refreshes generated agent files and publication outputs only after source
  implementation and installed-artifact verification pass.

## Non-Functional Requirements

- N001: Deterministic prepare, import, validation, status, list, and provenance
  operations SHALL work without network access.
- N002: Shared and per-edition YAML SHALL use the repository's safe loader and
  atomic writer contracts.
- N003: Ordering SHALL be stable under reversed filesystem enumeration and
  process restart.
- N004: Read operations SHALL be byte-invariant and SHALL not refresh outputs.
- N005: Edition writes SHALL remain inside declared `outputs/` or `drafts/`
  contracts and SHALL reject symlink/path traversal escapes.
- N006: Service, CLI, MCP, renderer, validation, and template concerns SHALL
  remain separated; `P2PWorkspace` and command handlers SHALL stay thin.
- N007: The common publication read/status path SHALL share request-scoped reads
  and SHALL have a measured performance budget against 100, 1,000, and 10,000
  proposal fixtures.
- N008: The evidence index SHALL be deterministic and byte-equivalent for the
  same semantic source state regardless of source enumeration order.
- N009: The feature SHALL preserve optional PDF dependencies and SHALL not add a
  mandatory model, translation, language-detection, or database dependency.
- N010: Errors SHALL identify edition key, failing stage, corrective command,
  and whether existing files were preserved.
- N011: New public payloads SHALL be JSON-serializable with stable field names
  and explicit contract versions.
- N012: Source, installed wheel, and installed sdist behavior SHALL agree.
- N013: Tests SHALL run on Python 3.11 and the current development Python.
- N014: No task SHALL commit, tag, push, publish a package, or migrate the live
  workspace without a separate owner instruction.

## Edge Cases And Required Diagnostics

- X001: Invalid or empty language tags fail before any write.
- X002: `en`, `EN`, `eng`, and `en_US` normalize deterministically; equivalent
  identities cannot create duplicate catalog entries.
- X003: Output-name traversal, hidden paths, extensions, reserved names, and
  overlong names fail before directory creation.
- X004: Preparing English then Italian, and Italian then English, yields the
  same independent edition states.
- X005: A changed shared evidence index marks both editions stale; changing only
  the Italian Markdown leaves English current.
- X006: Missing or invalid vertical state produces a generic model diagnostic,
  not invented vertical content.
- X007: Active unmapped evidence appears in the index and requires accounting.
- X008: Revoked/superseded evidence cannot satisfy a current project claim
  unless explicitly classified as historical context.
- X009: An evidence-accounting file with 99% coverage fails import.
- X010: A model claim referencing an unknown or process-only evidence ID fails
  import. Process-only entries must retain the `process_only` disposition and
  cannot support reader-facing claims.
- X011: Candidate Markdown written directly to the canonical output path is
  rejected as an import source.
- X012: Interrupted three-artifact import leaves the previous manifest current
  or the edition incomplete; no mixed revision is reported ready.
- X013: Manual edits after validation stale render and review only for that
  edition.
- X014: Unsupported future model/evidence/manifest versions are read-only and
  reported, not downgraded.
- X015: `contributions=include` with no attributed records fails clearly;
  `auto` omits the chapter and `omit` ignores available contribution data.
- X016: Two recorded author spellings remain separate and emit an identity-
  quality advisory rather than being guessed as one person.
- X017: Rounded contributor shares total exactly 100.00%, including
  `Unattributed`.
- X018: A non-English edition is not failed because its summary heading is not
  `Executive Summary`.
- X019: A document containing `PROP-001` or `CHANGE-001` in normal reader prose
  fails the no-internal-traceability contract.
- X020: A P2P Engine product publication may describe `.p2p`, proposals,
  decisions, or lifecycle concepts as supported product capabilities when the
  evidence requires them; the validator distinguishes that subject matter from
  upstream source-of-truth boilerplate, internal IDs, and governance status
  dumps.
- X021: Rendering without WeasyPrint preserves all non-PDF stages and reports
  the optional capability.
- X022: Review of one language cannot approve another language with identical
  source evidence.
- X023: Legacy unsuffixed approval remains legacy and false for every new v2
  edition until explicitly reviewed.
- X024: Agent update adds or refreshes all skill references atomically; doctor
  reports partial or drifted resource sets.

## Acceptance Criteria

- AC001: Default prepare resolves edition `project-en`; explicit Italian prepare
  resolves `project-it`; both coexist byte-for-byte after either execution order.
- AC002: `outputxyz-en.md` and `outputxyz-en.pdf` are produced for output name
  `outputxyz` without modifying `project-en`.
- AC003: The packet no longer embeds the full `project.md` export and declares
  complete source/evidence paths, hashes, vertical context, and exact candidates.
- AC004: The evidence index accounts for all selected source classes, includes
  active unmapped evidence, never substitutes lossy summaries for evidence, and
  is deterministic under reversed enumeration.
- AC005: Import refuses incomplete or inconsistent model/evidence accounting and
  accepts a complete candidate triplet atomically.
- AC006: The final Markdown is understandable without proposal IDs, governance
  states, artifact paths, hashes, or P2P workflow explanations.
- AC007: The curator skill builds a project model before prose, adapts structure
  to the vertical, and uses no implicit adjacent-project knowledge.
- AC008: Software, board-game, and custom-vertical forward evaluations all meet
  the editorial rubric threshold recorded in implementation evidence.
- AC009: English is the default; at least English and Italian end-to-end fixtures
  validate and render independently.
- AC010: The validator accepts localized headings, rejects internal workflow IDs
  in reader prose, and does not require a visible `.p2p` authority statement.
- AC011: Contribution percentages are deterministic, total 100.00%, include
  unattributed records, and are labeled as shares of recorded contributions.
- AC012: No implementation, governance, or contributor-quality claim is inferred
  from source absence or lifecycle state.
- AC013: Source/evidence drift stales all dependent editions; edition-local drift
  stales only the selected edition.
- AC014: Renderer HTML language and output path match the selected edition.
- AC015: Review and `approved_for_publication` are edition-specific and remain
  derived publication state.
- AC016: CLI text/JSON and MCP payloads expose matching edition semantics and
  stable error codes.
- AC017: Agent install/update/doctor/uninstall manage the concise skill and all
  one-level reference resources with drift tests.
- AC018: Existing publication service callers without new arguments default to
  English and do not require workspace migration.
- AC019: Legacy unsuffixed artifacts are reported accurately and never silently
  approve a new edition.
- AC020: Focused, CLI, MCP, agent, publication, renderer, full, Python 3.11,
  wheel, and sdist suites pass with recorded import provenance.
- AC021: Performance evidence proves publication status and prepare do not
  regress into repeated full-workspace or proposal-count-squared work.
- AC022: Documentation and help contain the exact paths and commands required to
  prepare, curate, import, validate, render, list, status, and review an edition.
- AC023: The requirement -> design -> task -> test matrix is updated after every
  slice and contains no uncovered requirement at the final gate.
- AC024: Final repository alignment is previewed separately, owner-confirmed,
  executed through supported commands, and records which generated artifacts
  changed.
