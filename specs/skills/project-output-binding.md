# Skill - Project Output Binding

Use this skill when asked to bind a generated generic project export, such as
`project.md` and `propose.md`, into local software development specs under
`specs/`.

This is a local development workflow. Do not mutate P2P governance state while
using this skill unless the owner separately asks for P2P operations.

## Required Method

Read:

1. `AGENTS-p2p-dev-specs.md`
2. `specs/methods/project-output-binding.md`
3. the requested `project.md` and `propose.md`
4. existing `specs/steering/*`
5. relevant `specs/features/*`
6. relevant code in `src/`, tests in `tests/`, and docs in `docs/`

## Core Rule

Never mark a task complete from project output alone.

Completion requires evidence from implementation surfaces:

- `src/`
- `tests/`
- `docs/`
- observed CLI behavior, when relevant

## Workflow

1. Classify export content into steering context, feature candidates, current
   export focus, and gaps.
2. Update steering only with stable cross-feature facts.
3. Create or update feature specs under `specs/features/<feature-name>/`.
4. Normalize requirements into testable statements.
5. Bind each requirement to implementation evidence.
6. Mark tasks complete only when evidence proves completion.
7. Create a binding report under `specs/bindings/` for substantial sync work.
8. Report unresolved gaps and owner questions.

## Output Discipline

- Do not copy entire generated exports into specs.
- Do not treat `propose.md` as requirements; it is an instruction prompt.
- Do not create one feature per proposal automatically.
- Do not overwrite existing feature specs without reconciling their current
  requirements, design, and tasks.
- Keep `.p2p/` as input only for this workflow.
