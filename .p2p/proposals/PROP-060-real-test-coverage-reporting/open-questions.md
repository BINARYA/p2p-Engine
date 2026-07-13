# Open Questions - PROP-060

No blocking owner questions remain for the current proposal scope.

Closed questions:

- Alternatives considered: no coverage tooling, advisory terminal diagnostic, immediate mandatory threshold.
- Preferred alternative: advisory terminal diagnostic.
- Main tradeoff: visibility without enforcement.
- Main risk: coverage percentage may be misread as a global quality score or routing mechanism.
- Main assumption: maintainers want occasional diagnostics, not default per-change coverage runs.
- Scope decision: deterministic test impact routing belongs to `PROP-098`; project evidence coverage is outside `PROP-060`.

Future non-blocking question:

- After a baseline exists, maintainers may decide whether a narrow threshold is useful for selected modules or release validation.
