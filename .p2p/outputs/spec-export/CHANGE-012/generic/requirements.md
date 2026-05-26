# Requirements

## Functional Requirements

### R001 - Deterministic Spec Generation

The CLI must provide `p2p spec refresh --change CHANGE-XXX` to generate a P2P-native software spec for the selected Change Set.

The command must:

- read the Change Set metadata and source references;
- include accepted proposal context from the Change Set source;
- include implementation, spec, and export targets when available;
- write the required spec artifacts under `.p2p/outputs/software-spec/CHANGE-XXX/`;
- preserve provenance to the source Change Set, proposals, decisions, and source files;
- avoid inventing requirements not supported by accepted P2P artifacts.

### R002 - Spec Status

The CLI must provide `p2p spec status` to list generated software specs and their current availability.

The command must show at least:

- Change Set id;
- spec generation/import state;
- Change Set title when available.

### R003 - Spec Show

The CLI must provide `p2p spec show CHANGE-XXX` to inspect the generated or imported spec for a Change Set.

The command must print the human-facing `index.md` artifact for the selected Change Set.

### R004 - Refinement Prompt

The CLI must provide `p2p spec prompt --change CHANGE-XXX` to generate a refinement prompt from the deterministic spec and source context.

The prompt must:

- explain the governance boundary;
- list the exact required output artifacts;
- include enough deterministic spec context to support refinement;
- instruct the refiner to mark missing information as open questions instead of inventing unsupported requirements.

### R005 - Refined Spec Import

The CLI must provide `p2p spec import CHANGE-XXX spec-output/` to import a refined spec directory.

The command must:

- verify that all required artifact files are present;
- parse YAML artifacts before import;
- validate required YAML top-level keys;
- fail without replacing the official spec when validation fails;
- copy the validated refined artifacts into `.p2p/outputs/software-spec/CHANGE-XXX/`.

### R006 - Skill And Test Coverage

The P2P skill must document the spec refresh, prompt, and import workflow. Tests must cover deterministic generation, prompt creation, status/show, and import validation.

## Non-Goals / Exclusions

- Do not implement OpenSpec export in this MVP.
- Do not implement Spec Kit export in this MVP.
- Do not invoke AI directly from the CLI.
- Do not create automatic Git commits, branches, tags, or merges.
- Do not treat raw proposal discussion as implementation requirements without accepted scope.

## Constraints

- The Change Set is the operational unit for spec generation.
- Generated specs must remain deterministic from P2P artifacts.
- Refined imports may improve structure and clarity, but must not expand scope beyond accepted sources.
- Import validation is structural; it does not decide project governance or approve new requirements.

## Open Questions

- Should future exporter-specific fields live in the P2P-native spec or only in OpenSpec/Spec Kit exporter layers?
- Should imported specs preserve a separate imported timestamp or author metadata beyond the existing provenance file?
- Should `p2p spec show` eventually support selecting individual artifacts instead of always showing `index.md`?
