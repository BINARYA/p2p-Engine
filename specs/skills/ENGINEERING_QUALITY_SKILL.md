# Engineering Quality Skill

## Purpose

This skill guides AI agents when designing, refactoring, or implementing code.

The goal is not to enforce one architectural style, framework, or pattern. The goal is to prevent fragile shortcuts and ensure that every change remains maintainable, testable, extensible, understandable, and safe to evolve by both humans and agents.

Agents must not optimize only for speed of implementation. They must optimize for long-term project quality while keeping the solution as simple as the problem allows.

## Core Principle

Do not write code that merely works now.

Write code that remains understandable, testable, and safe to evolve after many future changes by humans and agents.

A good implementation is not only correct. It is:

- understandable;
- localized;
- tested;
- compatible;
- reversible;
- explicit about side effects;
- aligned with the existing architecture;
- aligned with the framework being used;
- ready for future humans and agents to extend safely.

## Guiding Philosophy

Use freedom on patterns. Enforce discipline on quality.

Agents must not blindly apply MVC, DDD, Clean Architecture, OOP, functional programming, service layers, managers, factories, repositories, adapters, or registries.

Instead, agents must choose the simplest structure that satisfies the following constraints:

- responsibilities are clear;
- side effects are explicit;
- public behavior remains stable;
- code is testable;
- framework conventions are respected;
- extension points are obvious where growth is expected;
- domain logic is not accidentally mixed with presentation or infrastructure;
- future agents can understand where new behavior belongs.

## Framework Compatibility Principle

This skill must not fight the framework.

The engineering quality rules are meta-guidelines. They must be applied inside the conventions of the specific framework, stack, repository, or project.

Agents must not impose a generic architecture if the framework already provides a natural pattern.

Examples:

- Do not force Clean Architecture into a small Django app if Django-native structure is sufficient.
- Do not introduce repositories by default in Django, where the ORM already acts as the persistence abstraction.
- Do not force MVC terminology into frameworks that use different concepts.
- Do not bypass framework validation, routing, lifecycle, security, dependency injection, migrations, or configuration mechanisms.
- Do not create a parallel architecture that makes the framework harder to use.

The correct approach is:

```text
Follow framework conventions first.
Improve structure within those conventions.
Introduce additional architectural layers only when the framework-native structure is no longer sufficient.
Do not fight the framework to satisfy an abstract pattern.
```

## Relationship With Framework-Specific Skills

If a framework-specific skill, repository guideline, or project convention exists, the agent must follow it.

This skill complements framework-specific rules; it does not replace them.

If there is a conflict between this skill and a framework-specific instruction, the agent must:

1. identify the conflict explicitly;
2. prefer the framework/project-specific convention when it concerns normal code organization;
3. preserve Level 1 safety rules such as no validation bypass, no permission bypass, no hidden side effects, no hardcoded environment-specific values, and no unapproved breaking changes;
4. ask for confirmation or produce a design note when the correct precedence is unclear.

Framework-specific conventions are part of the architecture.

## Scope

This skill applies to:

- new feature implementation;
- bug fixes;
- refactoring;
- CLI/API/MCP changes;
- persistence changes;
- validation changes;
- Git/sync behavior;
- permission, consent, or governance behavior;
- test additions;
- architectural cleanup;
- agent-facing tool design;
- framework-based application code.

For trivial changes such as typo fixes, comments, or obvious local renames, use common sense and avoid unnecessary ceremony.

---

# 1. Rule Levels

Not all rules have the same weight. Agents must distinguish between:

- inviolable rules;
- strong defaults;
- contextual design choices.

## 1.1 Level 1 — Inviolable Rules

These rules must not be broken unless there is an explicit owner-approved proposal, change request, or task that authorizes the exception before implementation.

Agents must:

- preserve public behavior unless a breaking change is explicitly approved;
- respect framework and project conventions unless explicitly instructed otherwise;
- not mix domain logic with presentation or infrastructure logic in ways that conflict with the framework/project architecture;
- not bypass validation, permissions, consent, security, or governance checks;
- not mutate state from read-only operations;
- not hide or swallow errors that affect correctness;
- not perform broad refactoring and behavior changes in the same change without prior approval;
- not hardcode local machine, user, repository, credential, or environment-specific values;
- not infer the whole architecture from partial context;
- not duplicate existing logic without checking for reuse;
- not qualify their own broad change retroactively;
- not fix unrelated architectural problems opportunistically;
- not proceed when the design process has too many unresolved answers.

## 1.2 Level 2 — Strong Defaults

These rules should normally be followed. Exceptions are allowed only when the agent explains why.

Agents should:

- avoid hardcoded absolute paths;
- derive paths from injected or configured roots;
- prefer explicit dependencies over hidden global state;
- prefer atomic writes for persisted project state;
- prefer typed statuses/enums over free-form strings;
- prefer framework-native extension points before custom abstractions;
- prefer registries/maps for families expected to grow;
- prefer small, reversible changes;
- prefer diagnostic errors with actionable recovery guidance;
- prefer tests that verify observable behavior rather than implementation details;
- prefer reuse or extraction over duplication;
- prefer small design notes when architectural uncertainty exists.

## 1.3 Level 3 — Contextual Design Choices

These are not mandatory patterns. The agent must choose based on the problem and on the framework conventions.

Examples:

- OOP vs functions;
- service layer vs simple module function;
- registry vs direct conditional logic;
- facade vs direct service usage;
- adapter abstraction vs direct library call;
- template system vs simple string rendering;
- custom exception classes vs structured `ValueError`;
- dataclasses vs plain dictionaries;
- dependency injection vs simple explicit parameters;
- repository layer vs framework ORM/query API;
- framework-native model methods vs separate domain services.

The agent must not apply patterns mechanically. The chosen structure must be justified by responsibility boundaries, expected growth, framework idioms, testability, and compatibility needs.

---

# 2. Framework Convention Rule

Before designing or changing code inside a framework-based project, the agent must identify the framework and the existing project conventions.

The agent must ask:

- What framework is being used?
- What are the framework-native responsibilities?
- Where does this project currently place similar behavior?
- Is there a framework-specific skill, guide, or convention file?
- Would a generic pattern conflict with expected framework usage?
- Is an additional layer justified by complexity, reuse, testing, side effects, or cross-module workflow?

## 2.1 Do Not Fight the Framework

Agents must not introduce generic architecture that makes framework-native development harder.

Bad:

```text
Introduce repositories, use cases, DTOs, entities, ports, and adapters for a simple Django CRUD view without a clear need.
```

Good:

```text
Use Django models, forms/serializers, views, managers/querysets, and tests. Add a service only when the workflow becomes multi-step or has side effects.
```

## 2.2 Introduce Extra Layers Only When Justified

Extra layers are appropriate when they solve a real problem, such as:

- complex multi-step business workflows;
- repeated logic across views/API/tasks/admin;
- side effects such as emails, external APIs, payments, Git operations, file writes;
- operations spanning multiple models or bounded contexts;
- code that must be reused by CLI, API, jobs, or tests;
- framework-native files becoming too large or mixed;
- need for clear permission, validation, audit, or lifecycle boundaries.

Extra layers are not appropriate merely because the agent prefers a pattern.

## 2.3 Framework-Specific Skills Have Priority for Framework Idioms

If a Django, FastAPI, NestJS, Angular, Rails, Laravel, React, or other framework-specific skill exists, the agent should use it to understand framework idioms.

This engineering skill remains responsible for:

- scope discipline;
- compatibility;
- testability;
- side effect clarity;
- error quality;
- no duplication;
- no partial-context architecture;
- no safety or governance bypass.

---

# 3. Django-Specific Guidance

When working in Django, respect Django's native architecture.

Use:

- `models.py` for models, constraints, simple domain behavior, and ORM-level invariants;
- model methods for behavior tightly coupled to a single model instance;
- custom managers and querysets for reusable query logic;
- `forms.py` for HTML/form input validation and form-specific behavior;
- `serializers.py` for API validation and representation boundaries, when using Django REST Framework or similar;
- `views.py` / viewsets for request orchestration, not heavy business workflows;
- `admin.py` for admin configuration and admin-specific behavior;
- `urls.py` for routing;
- `migrations/` for schema changes;
- `tasks.py` for asynchronous/background work;
- `signals.py` sparingly, only when implicit decoupling is truly needed;
- `services.py` or a dedicated service module for multi-step workflows, side effects, integrations, or operations involving multiple models;
- `selectors.py` or query modules only when query logic becomes complex or reused;
- settings/configuration instead of hardcoded environment-specific values.

## 3.1 Do Not Add Repositories by Default in Django

Django's ORM is already a persistence abstraction.

Do not introduce a repository layer by default.

A repository-like layer may be justified only when:

- persistence must be isolated from a non-Django external dependency;
- multiple storage backends must be supported;
- testing requires substituting a complex external integration;
- the project already uses such a pattern consistently;
- the owner or architecture guidelines explicitly require it.

## 3.2 Keep Views Thin Enough

Django views can orchestrate request handling, but should not accumulate heavy business workflows.

If a view starts to:

- update multiple models;
- call external systems;
- send notifications;
- manage lifecycle transitions;
- create audit records;
- contain complex branching;
- duplicate behavior used elsewhere;

move the workflow into a service or dedicated application function.

## 3.3 Use Signals Sparingly

Signals can hide side effects.

Use signals only when implicit decoupling is intentionally desired and documented.

Do not use signals merely to avoid calling a service explicitly.

## 3.4 Django Rule of Thumb

```text
Use Django-native structure first.
Add services/selectors only when the native structure becomes insufficient.
Do not impose Clean Architecture by default.
Do not put everything in views or signals.
```

---

# 4. Partial Context Rule

Agents often operate with an incomplete view of the codebase. They must not infer the whole architecture from a small set of files.

Before implementing non-trivial changes, the agent must inspect enough context to answer:

- which framework or stack is being used;
- which layer owns the responsibility;
- which public contracts may be affected;
- which side effects exist;
- whether similar logic already exists;
- which tests cover the area;
- which persisted artifacts may change;
- which external interfaces may observe the change.

If the agent cannot answer these points with sufficient confidence, it must not proceed with broad implementation.

It should instead do one of the following:

- inspect more relevant files;
- inspect relevant tests;
- inspect framework/project guidelines;
- run tests if available;
- search for similar existing logic;
- produce a design note;
- ask for owner confirmation if the uncertainty affects architecture, compatibility, persistence, permissions, or public behavior.

Do not design architecture from partial context.

## Practical Rule

When context is incomplete, the agent must reduce scope, inspect more code, or produce a design note.

It must not compensate for missing context with architectural assumptions.

---

# 5. Qualified Change Rule

A broad change that mixes refactoring and behavior modification is allowed only when it is qualified.

Qualified means:

- explicitly approved by the owner before implementation; or
- explicitly described in an accepted proposal/change request before implementation.

It is not enough for the agent to justify the broad change after deciding to do it.

Bad:

```text
I refactored the service and changed validation because it seemed necessary.
```

Good:

```text
The owner-approved change request explicitly allows extracting the service and changing validation semantics in the same change set.
```

If approval is missing, split the work:

1. structural refactor preserving behavior;
2. behavior change with dedicated tests.

The agent cannot qualify its own broad change retroactively.

---

# 6. Existing Logic Discovery Rule

Before implementing new logic, the agent must check whether equivalent or similar logic already exists.

The agent should search for:

- existing functions;
- existing services/managers;
- existing validators;
- existing constants/enums;
- existing serializers/parsers;
- existing framework-native extension points;
- existing CLI handlers;
- existing API/MCP handlers;
- existing tests that imply expected behavior;
- existing documentation that defines intended behavior.

Unintentional duplication is immediate technical debt.

If similar logic exists, prefer reuse, extension, or extraction over rewriting.

If reuse is not appropriate, explain why.

Bad:

```text
Add a new YAML parser because this function needs YAML.
```

Good:

```text
Reuse the existing YAML read/write helper. If it is insufficient, extend it with tests.
```

---

# 7. Design Process Before Coding

Before coding, the agent must answer:

1. What behavior is being added, removed, changed, or preserved?
2. Is this change structural, behavioral, or both?
3. Which framework/project convention applies?
4. Which layer owns this responsibility: domain, application, adapter, presentation, or test?
5. Which public contracts must remain stable?
6. What side effects exist?
7. Is this the smallest reversible change?
8. Is an extension point really needed now, or would it be speculative?
9. What existing logic must be reused or respected?
10. What tests will prove correctness and prevent behavior drift?
11. Does the change require a structured implementation summary?
12. Is there any owner, governance, security, permission, or consent implication?

## Design Process Exit Condition

The design process is not a checklist to fill mechanically. It is a readiness gate.

If more than two design questions remain unanswered, the agent must not implement the change directly.

Instead, it must produce a design note that states:

- what is known;
- what is unknown;
- what framework or stack is involved;
- what files were inspected;
- what tests were inspected;
- what risks exist;
- what decision or confirmation is needed;
- the smallest safe next step.

The agent may proceed only with a small, clearly safe, reversible change that does not depend on the unresolved questions.

---

# 8. Atomic Change Rule

A high-quality change should normally do one thing.

Prefer one change set for one responsibility:

- refactor structure without changing behavior;
- add behavior without broad restructuring;
- fix a bug without unrelated cleanup;
- update documentation without hidden runtime changes;
- add tests without unrelated formatting changes;
- adapt to framework conventions without changing unrelated behavior.

If a change mixes refactoring and behavior modification, the agent must explicitly state:

- what behavior changed;
- what structure changed;
- why they must be done together;
- who approved the combined scope;
- which tests prove no unintended behavior drift occurred.

Bad:

```text
Refactor proposal system, change validation behavior, update CLI output, and add a new MCP tool.
```

Good:

```text
Extract ConsentService behind P2PWorkspace without changing CLI/MCP behavior.
```

Then, separately:

```text
Add a new consent validation rule with dedicated tests.
```

---

# 9. Smallest Reversible Change

When uncertain, the agent must choose the smallest change that makes progress and can be reverted safely.

The agent must not perform speculative large refactors “while already touching the file”.

If the ideal architecture is unclear:

- implement the minimum correct behavior;
- keep the change localized;
- follow framework conventions;
- add tests;
- leave an explicit TODO, follow-up note, issue, or proposal candidate;
- avoid creating abstractions that are not yet justified.

This rule is the counterbalance to both underengineering and overengineering.

Bad:

```text
The consent logic is messy, so redesign all permissions, consent, MCP tools, and CLI commands in one pass.
```

Good:

```text
Extract the existing consent grant/request/show/validate behavior into ConsentService while preserving public behavior. Leave future permission policy redesign as a follow-up.
```

---

# 10. Existing Architecture Disagreement Rule

The agent may discover pre-existing architectural problems while working, such as:

- oversized files;
- mixed responsibilities;
- duplicated logic;
- weak abstractions;
- inconsistent naming;
- missing tests;
- circular dependencies;
- fragile persistence logic;
- unclear error model;
- outdated documentation;
- framework conventions used inconsistently.

If the issue is outside the current scope, the agent must not fix it opportunistically.

It should record it as a follow-up, design note, TODO, issue, or proposal candidate.

Do not perform unrelated cleanup just because the file is already open.

Bad:

```text
While adding consent validation, I also reorganized proposal parsing and renamed registry helpers.
```

Good:

```text
While adding consent validation, I noticed duplicated proposal parsing. I left it unchanged and recorded it as a follow-up refactoring candidate.
```

---

# 11. No Opportunistic Cleanup Rule

Cleanup is allowed only when it is directly necessary for the current change or explicitly requested.

Allowed:

- rename a local variable touched by the change;
- extract duplicated code needed by the current change;
- add a missing test for behavior being modified;
- improve an error message in the touched path;
- remove dead code directly made obsolete by the current change;
- align a touched function with an already established framework/project convention.

Not allowed without explicit scope:

- broad formatting changes;
- unrelated renames;
- moving unrelated modules;
- changing public output;
- changing schemas;
- rewriting adjacent logic;
- replacing working patterns with preferred patterns;
- introducing a non-framework-native architecture without approval;
- modifying tests unrelated to the behavior under change.

The agent must not “improve the world” during a scoped task.

---

# 12. Responsibility Separation

Code should generally be organized by responsibility, while respecting framework conventions.

Generic responsibility model:

```text
domain/
  Business concepts, lifecycle rules, statuses, IDs.

application/
  Use cases, services, workflows, orchestration.

adapters/
  Filesystem, Git, database, HTTP, YAML, Markdown, external systems.

presentation/
  CLI output, API output, MCP payloads, UI-specific formatting.

tests/
  Observable behavior, regression protection, compatibility contracts.
```

Framework-native structures may use different names.

For example, in Django:

```text
models.py      domain/data model and ORM invariants
views.py       request orchestration
serializers.py API representation/validation
forms.py       form representation/validation
services.py    multi-step workflows or side effects
tasks.py       async/background work
```

The principle is responsibility separation, not a fixed folder layout.

Domain logic must not be accidentally hidden inside CLI, MCP handlers, storage adapters, or output formatting code. Framework-native placement is acceptable when it is idiomatic and maintainable.

## Examples

Bad:

```text
cli.py decides whether a proposal can be accepted.
```

Good:

```text
ProposalService decides whether a proposal can be accepted.
cli.py calls ProposalService and prints the result.
```

Bad:

```text
Django view contains a long multi-model workflow with notifications and audit writes.
```

Good:

```text
Django view validates the request and calls a service that performs the workflow.
```

---

# 13. Public Behavior Compatibility

Refactoring must preserve existing public behavior unless a breaking change is explicitly approved.

Do not silently change:

- CLI command names;
- CLI option names;
- CLI output relied on by tests or agents;
- API endpoints;
- API response shapes;
- MCP tool names;
- MCP input schemas;
- MCP payload structure;
- persisted file layout;
- database schema;
- migration behavior;
- YAML schema;
- Markdown section structure relied on by code;
- lifecycle semantics;
- permission/consent behavior;
- validation behavior;
- registry refresh behavior;
- Git/sync behavior;
- framework-specific public contracts such as URL names, serializer fields, admin behavior, or signal behavior.

Breaking changes require an explicit proposal or owner-approved change request.

---

# 14. Side Effect Discipline

Function and method names must reflect their side effects.

Read-only operations such as:

- `show`;
- `list`;
- `validate`;
- `status`;
- `context`;
- `inspect`;
- `preview`;
- `selector` or query-only functions.

must not mutate state.

Write operations such as:

- `create`;
- `refresh`;
- `import`;
- `update`;
- `accept`;
- `reject`;
- `merge`;
- `publish`;
- `cleanup`;
- `save`;
- `apply`;
- `dispatch`.

must make their side effects clear and must be tested.

If a function both reads and writes, its name and documentation must make that explicit.

Framework lifecycle hooks, signals, callbacks, and middleware must be treated as side-effect-sensitive code.

---

# 15. Explicit Dependencies

Avoid hidden dependency on:

- global state;
- current working directory;
- ambient environment;
- mutable module globals;
- local machine configuration;
- implicit user identity;
- implicit branch or remote;
- current date/time without an injected clock when determinism matters;
- implicit framework settings when explicit configuration would be clearer.

Prefer injecting or explicitly accessing dependencies such as:

- project root;
- filesystem store;
- Git client;
- clock;
- configuration;
- logger;
- registry;
- permission policy;
- output renderer;
- framework settings;
- request/user context where appropriate.

Bad:

```python
root = Path.cwd()
```

inside deep application logic.

Good:

```python
def create_proposal(root: Path, title: str) -> Proposal:
    ...
```

Better for larger boundaries:

```python
class ProposalService:
    def __init__(self, store: FileSystemStore) -> None:
        self.store = store
```

Framework-specific note:

Using framework-provided settings, request objects, dependency injection, ORM sessions, or app context is acceptable when it is idiomatic. Do not hide cross-cutting behavior in globals merely for convenience.

---

# 16. Path and Environment Handling

Never hardcode paths that depend on a local machine, user, environment, or repository location.

Bad:

```python
path = "/home/user/project/.p2p/project.yml"
```

Good:

```python
path = workspace_root / ".p2p" / "project.yml"
```

Runtime-resolved absolute paths are acceptable when derived from an injected or configured root.

The real rule is:

Do not codify in source code paths that depend on the developer machine, runtime user, repository checkout location, container location, private environment, or deployment-specific assumptions.

Framework-specific note:

In Django, use `settings`, storage backends, `BASE_DIR`, configured media/static storage, or dependency injection patterns instead of hardcoded paths.

---

# 17. Extensibility Without Overengineering

Use extensible structures when a family will grow.

When adding behavior to a family that is likely to grow, avoid long chains of `if/elif`.

Prefer:

- registries;
- strategy maps;
- adapter maps;
- command maps;
- declarative specs;
- plugin-like structures;
- framework-native extension points.

Good candidates:

- MCP tools;
- CLI command families;
- export targets;
- domain templates;
- validators;
- prompt renderers;
- storage backends;
- Git providers;
- agent profiles;
- API serializers;
- framework plugins/extensions;
- task handlers.

Bad:

```python
if name == "tool_a":
    ...
elif name == "tool_b":
    ...
elif name == "tool_c":
    ...
```

Better:

```python
TOOLS = {
    "tool_a": ToolSpec(...),
    "tool_b": ToolSpec(...),
    "tool_c": ToolSpec(...),
}
```

But do not create extensibility points speculatively.

If there is only one implementation and no near-term expectation of growth, a simple function may be better.

---

# 18. Pattern Selection Guide

Use simple functions when:

- logic is pure;
- no state is needed;
- no dependency injection is needed;
- behavior is unlikely to grow into multiple variants;
- framework conventions favor a simple function.

Use classes/services when:

- behavior coordinates multiple operations;
- dependencies must be injected;
- state or configuration is needed;
- a domain boundary needs to be explicit;
- the service will be reused by CLI, MCP, API, background jobs, or tests;
- framework-native handlers/views are becoming too heavy.

Use a facade when:

- external callers need a stable entry point;
- internals are being refactored;
- compatibility is more important than exposing the cleanest internal model immediately.

Use registries/maps when:

- new variants will be added over time;
- behavior is selected by name/type/target/provider;
- schema, handler, safety rules, and documentation should stay aligned.

Use adapters when:

- code talks to filesystem, Git, database, HTTP, external tools, operating system APIs, or environment-specific behavior;
- the framework does not already provide a sufficient abstraction.

Use custom exceptions when:

- errors need stable codes;
- machine-readable handling is required;
- multiple callers need to distinguish failure modes;
- recovery guidance is important.

Avoid abstract base classes unless:

- multiple implementations already exist;
- the interface is stable;
- tests benefit from substituting implementations.

Do not introduce a pattern because it is fashionable. Introduce it because the current responsibility needs it.

---

# 19. Facade and Internal Managers

When a public class or module is already used by CLI, MCP, tests, or external callers, prefer preserving it as a facade while moving behavior behind it.

Example:

```python
class P2PWorkspace:
    def __init__(self, root):
        self.store = FileSystemStore(root)
        self.consent = ConsentService(self.store)
        self.proposals = ProposalService(self.store)
        self.registries = RegistryService(self.store)

    def consent_grant(self, *args, **kwargs):
        return self.consent.grant(*args, **kwargs)

    def create_proposal_with_details(self, *args, **kwargs):
        return self.proposals.create_with_details(*args, **kwargs)
```

This preserves compatibility while improving internal structure.

Do not expose a new public API just because the internal architecture improved. Public API redesign requires explicit approval.

Framework-specific note:

If the framework already provides the public integration boundary, such as Django views, DRF viewsets, FastAPI routers, NestJS controllers/providers, or Angular services/components, preserve those public boundaries and improve internals behind them.

---

# 20. File Persistence and Atomicity

For persisted project state, avoid scattered raw writes.

Bad:

```python
path.write_text(yaml.safe_dump(data))
```

Good:

```python
store.write_yaml(path, data)
```

Better:

```python
store.write_yaml_atomic(path, data)
```

For critical state:

- use centralized read/write helpers;
- use atomic writes where possible;
- use locks where concurrent writers may exist;
- avoid partial writes;
- avoid duplicated serialization logic;
- preserve formatting expectations where externally visible;
- test the persisted artifact.

When a project is file-based and agent-facing, persistence is part of the public contract.

Framework-specific note:

For database-backed frameworks, use framework-native transactions where appropriate, such as Django `transaction.atomic()`. Do not replace framework transaction mechanisms with custom ad hoc logic.

---

# 21. Error Contract

Errors have two audiences:

- humans;
- agents/systems.

The code should respect both contracts.

## 21.1 Human-Facing Errors

Used in CLI output, documentation, web UI messages, API messages, and recovery messages.

They should be:

- readable;
- specific;
- non-technical where possible;
- action-oriented.

Example:

```text
Consent receipt not found: CONSENT-003.
Run `p2p consent status` to list available receipts.
```

## 21.2 Machine-Facing Errors

Used internally, in MCP payloads, API payloads, tests, logs, validation, or automation.

They should include stable fields where possible:

- error code;
- operation;
- artifact id;
- path;
- current state;
- requested state;
- suggested command;
- recoverability.

Example shape:

```yaml
error:
  code: P2P_CONSENT_NOT_FOUND
  operation: proposal_publish
  artifact: CONSENT-003
  recoverable: true
  suggested_command: p2p consent status
```

The agent should not replace structured diagnostic information with prose only when the caller is MCP, API, validation, or another machine-facing interface.

## 21.3 Error Quality Rule

Bad:

```python
raise ValueError("Invalid state")
```

Good:

```python
raise ValueError(
    "Invalid proposal lifecycle transition: accepted -> draft for PROP-001. "
    "Create a new proposal or use a supported transition."
)
```

Errors should explain:

- what failed;
- which artifact or operation failed;
- why it failed;
- what can be done next, when possible.

Framework-specific note:

Respect framework error mechanisms. In Django/DRF, use validation errors, permission errors, HTTP responses, or exception handlers consistently with the project conventions.

---

# 22. Test Requirements

Every meaningful change must include tests that protect observable behavior.

Depending on the area touched, include tests for:

- CLI behavior;
- API behavior;
- MCP behavior;
- persisted artifacts;
- database behavior;
- migrations;
- validation;
- lifecycle transitions;
- Git/sync behavior;
- permission/consent behavior;
- authentication/authorization;
- backward compatibility;
- schema compatibility;
- error handling;
- idempotency where applicable.

Refactoring is complete only when tests prove that behavior did not drift.

## 22.1 Test Behavior, Not Implementation Details

Prefer tests that verify externally observable contracts:

- command output;
- HTTP responses;
- returned payloads;
- written files;
- database state;
- validation findings;
- lifecycle state;
- error messages or error codes;
- Git branch/commit/remote behavior.

Avoid tests that overfit private implementation details unless the implementation detail is itself a deliberate contract.

## 22.2 Idempotency Tests

For refresh/generation operations, test that running the operation more than once does not create unintended drift.

Examples:

- registry refresh;
- assessment refresh;
- agent instruction refresh;
- generated context;
- deterministic exports;
- migration-safe setup;
- idempotent management commands.

---

# 23. Expected Output From Agent

The agent must not produce boilerplate reports for every trivial change.

A structured implementation summary is required when the change:

- touches more than one architectural layer;
- changes public behavior;
- changes CLI output;
- changes API behavior;
- changes MCP tools or payloads;
- changes persisted layout or schema;
- changes database schema/migrations;
- changes validation behavior;
- changes Git/sync behavior;
- changes permission, consent, security, or governance semantics;
- performs a refactoring;
- introduces a new dependency;
- changes error semantics;
- adapts or overrides framework conventions.

For small local fixes, a concise summary and test result is enough.

## 23.1 Required Summary for Non-Trivial Changes

```text
Design choice:
Framework/project convention considered:
Compatibility impact:
Behavior changes:
Files changed:
Tests added/updated:
Risks:
Follow-up:
```

For refactoring changes, the agent must explicitly state whether public behavior was preserved.

---

# 24. Pre-Implementation Context Checklist

Before implementing a non-trivial change, the agent must confirm:

```text
[ ] I identified the framework/stack and relevant project conventions.
[ ] I inspected the owner module of the behavior.
[ ] I inspected at least one caller.
[ ] I inspected relevant tests.
[ ] I searched for similar existing logic.
[ ] I know whether public CLI/API/MCP/schema behavior is affected.
[ ] I know whether persisted artifacts or database schema are affected.
[ ] I know whether the change is structural, behavioral, or both.
[ ] I know the smallest reversible implementation path.
[ ] I know whether owner/governance/security/consent semantics are affected.
```

If this checklist cannot be satisfied, the agent must stop and produce a design note or ask for confirmation.

---

# 25. Forbidden Shortcuts

Agents must not:

- infer architecture from partial context;
- ignore framework/project-specific conventions;
- impose generic architecture against framework idioms;
- duplicate existing logic without checking for reuse;
- qualify their own broad change after the fact;
- mix refactoring and behavior change without prior approval;
- fix unrelated architectural problems opportunistically;
- perform cleanup outside the current scope;
- proceed when the design process has too many unresolved answers;
- hide uncertainty behind confident implementation;
- add unrelated behavior to existing large files;
- bypass validation to make tests pass;
- bypass framework security/permission mechanisms;
- hardcode local paths, users, branches, remotes, credentials, or environment-specific values;
- swallow errors without diagnostics;
- introduce broad `except Exception` blocks without controlled error reporting;
- mutate persisted state from read-only commands;
- change public output casually;
- duplicate parsing or serialization logic across modules;
- create new dependencies without justification;
- implement security, permission, governance, or consent bypasses;
- perform large refactors without incremental tests;
- replace existing working architecture only because the agent prefers another pattern.

---

# 26. Design Note Template

When the agent cannot safely implement because context is insufficient, framework convention is unclear, or scope is too broad, it should produce a design note.

```md
# Design Note — <title>

## Requested change

## Framework / stack context

## Known context

## Files inspected

## Tests inspected

## Existing related logic

## Relevant framework/project conventions

## Unknowns

## Risks

## Public contracts possibly affected

## Recommended smallest reversible next step

## Owner confirmation needed

```

A design note is not a failure. It is the correct output when implementation would otherwise rely on unsafe assumptions.

---

# 27. Follow-Up Reporting

When discovering out-of-scope issues, the agent should report them as follow-ups.

Use this format:

```md
## Follow-up candidate

Area:
Observed issue:
Framework/project convention involved:
Why it matters:
Why it was not changed now:
Suggested next step:
```

Do not fix the issue unless it is part of the current approved scope.

---

# 28. Code Quality Heuristics

A change is likely too broad if:

- it touches many unrelated modules;
- tests fail in unrelated areas;
- it changes output snapshots unexpectedly;
- it modifies persistence format without a migration note;
- it modifies database schema without migration/testing strategy;
- it updates docs to justify behavior that was not approved;
- it combines renaming, moving, and behavior changes;
- it requires the agent to say “while I was there”;
- it introduces abstractions not used by the current feature;
- it creates new files whose responsibilities overlap existing files;
- it replaces framework-native patterns with custom architecture without a clear reason.

A change is likely well-scoped if:

- its purpose can be stated in one sentence;
- its affected layer is clear;
- it respects framework/project conventions;
- its tests map directly to the behavior;
- public behavior is preserved or explicitly changed;
- follow-up improvements are noted but not bundled;
- rollback is straightforward.

---

# 29. p2p Engine Specific Addendum

This section applies when working on p2p Engine.

## 29.1 Architectural Direction

`P2PWorkspace` should remain a stable public facade for compatibility with CLI, MCP, tests, and existing usage.

However, new domain or application behavior should not be added directly to `P2PWorkspace` unless it is only a delegating compatibility method.

Preferred direction:

```text
CLI / MCP / external callers
        |
        v
P2PWorkspace facade
        |
        +--> ConsentService
        +--> PermissionService
        +--> ProposalService
        +--> ChoiceService
        +--> ChangeSetService
        +--> RegistryService
        +--> AssessmentService
        +--> WorkService
        +--> SpecService
        +--> SyncService
        |
        v
Filesystem / Git / YAML / Markdown adapters
```

## 29.2 Files That Should Not Accumulate New Core Logic

Do not add new domain/application logic directly into:

- `src/p2p_engine/cli.py`;
- `src/p2p_engine/storage/filesystem.py`;
- `src/p2p_engine/mcp/tools.py`.

These may remain compatibility/facade layers while internals are extracted.

## 29.3 Preferred Refactoring Strategy

Use manager/service extraction behind stable facade.

Preferred sequence:

1. create/update architectural development guidelines;
2. extract consent/permissions service first;
3. extract proposal service;
4. extract registry service;
5. extract assessment/readiness service;
6. extract Git/sync service with richer Git results;
7. split CLI after services exist;
8. replace MCP tool dispatcher with declarative tool registry;
9. introduce atomic file store and workspace transaction if concurrency becomes relevant.

## 29.4 Compatibility Contracts

Do not break without explicit proposal:

- CLI commands;
- CLI output relied on by tests/agents;
- MCP tool names;
- MCP payloads;
- `.p2p` layout;
- YAML/Markdown schemas;
- proposal lifecycle;
- change lifecycle;
- work lifecycle;
- consent/permission-gated semantics;
- owner-controlled governance;
- validation findings;
- registry refresh behavior;
- Git/sync behavior.

## 29.5 Owner-Controlled Actions

Do not implement shortcuts that allow agents to bypass owner control for:

- proposal accept/reject/defer;
- choice decide;
- branch publish;
- merge;
- finalize;
- cleanup;
- work accept/finalize/cleanup;
- consent grant/revoke;
- raw Git operations that affect managed state.

Permission-gated flows must remain explicit and auditable.

## 29.6 First Extraction Candidate

The safest first extraction is consent/permissions.

Reason:

- clear boundary;
- critical for agent safety;
- lower CLI output risk than a CLI-first split;
- good candidate for establishing the service extraction pattern.

## 29.7 Refactoring Rule

For p2p Engine, prefer:

```text
Extract behavior behind `P2PWorkspace` while preserving public behavior.
```

Do not redesign public APIs unless explicitly approved.

---

# 30. Framework Adaptation Examples

## 30.1 Django

Use Django-native organization first.

Add extra services only when views/models/serializers would otherwise become overloaded.

Do not introduce repositories by default.

## 30.2 FastAPI

Use routers for HTTP boundaries, Pydantic models for request/response contracts, dependency injection for runtime dependencies, and services for workflows that exceed request orchestration.

Do not put heavy business workflows directly into route functions.

## 30.3 NestJS

Respect NestJS modules, providers, controllers, guards, pipes, interceptors, and dependency injection.

Do not bypass the module/provider system with global ad hoc imports.

## 30.4 Angular

Respect Angular components, services, modules/standalone components, routing, signals/observables according to project conventions.

Do not put shared business or API logic directly into components when a service is appropriate.

## 30.5 General Rule

Framework-specific idioms come first. Engineering quality principles shape how code is written inside those idioms.

---

# 31. Recommended Agent Instruction Header

This text can be placed at the top of an agent-facing instruction file.

```md
When modifying this repository, preserve public behavior and improve internal structure.

Respect the framework and project conventions first. Do not impose generic architecture that conflicts with framework-native patterns.

Do not add new domain or application logic to monolithic compatibility files.

Prefer small, tested, reversible changes that move behavior toward explicit responsibilities, typed domain models where useful, safe adapters, and agent-safe interfaces.

When context is incomplete, reduce scope, inspect more code, or produce a design note. Do not compensate for missing context with architectural assumptions.
```

---

# 32. Quick Checklist

Before coding:

```text
[ ] Do I know the framework/stack and project conventions?
[ ] Do I have enough context?
[ ] Did I search for existing similar logic?
[ ] Is the change structural, behavioral, or both?
[ ] Is the change small and reversible?
[ ] Am I preserving public contracts?
[ ] Am I respecting framework-native patterns?
[ ] Am I avoiding opportunistic cleanup?
[ ] Are side effects explicit?
[ ] Are dependencies explicit?
[ ] Are tests planned?
[ ] Is owner approval needed?
```

Before finishing:

```text
[ ] Tests were added or updated.
[ ] Public behavior was preserved or explicitly changed.
[ ] Framework/project conventions were respected.
[ ] Persisted artifacts were checked if affected.
[ ] Database schema/migrations were checked if affected.
[ ] CLI/API/MCP contracts were checked if affected.
[ ] Validation behavior was checked if affected.
[ ] Consent/governance/security behavior was checked if affected.
[ ] Follow-up issues were reported but not bundled.
[ ] The implementation summary is appropriate for the change size.
```

---

# 33. Final Quality Bar

A change is acceptable only if:

- it solves the requested problem;
- it respects framework and project conventions;
- it does not rely on partial-context assumptions;
- it does not duplicate existing logic unnecessarily;
- it does not hide behavior drift;
- it does not mix unrelated responsibilities;
- it does not bypass safety, security, framework validation, or governance;
- it does not introduce avoidable future confusion;
- it leaves the codebase easier, not harder, for the next human or agent to work on.