# Open Questions

No owner-blocking questions remain for PROP-084.

Implementation must make one bounded technical choice before coding: where to
place the reusable governed-write preflight so representative mutating paths are
covered without scattering runtime checks through unrelated command handlers.

Implementation must also confirm whether an existing project-level marker can
identify projects that require `runtime.yml`. If no marker exists, missing files
must be treated as `legacy_undeclared` until such a marker is introduced.
