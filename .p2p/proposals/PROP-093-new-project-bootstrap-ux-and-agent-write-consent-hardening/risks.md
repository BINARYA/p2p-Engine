# Risks

- The implementation could become too broad if scaffold, contributions, rendering, init, MCP hints, docs, and hygiene are delivered as one Change Set. Mitigation: implement slices 093-A through 093-E with independent verification.
- Compatibility mistakes could break projects initialized by the current release. Mitigation: keep legacy metadata optional, derive artifact catalogs lazily, preserve existing narrative files, and maintain current CLI/MCP output by default.
- Agent detection can be wrong or unavailable. Mitigation: install `generic` always, add a detected adapter only when reliable, and fallback to `all` with a concise warning when detection is unavailable.
- The `all` fallback preserves compatibility but keeps some file-footprint noise. Mitigation: make the created-file summary and later integration lifecycle commands explicit.
- Agent uninstall could delete shared files or human edits. Mitigation: remove only managed, unchanged, non-shared files and report drift instead of deleting it.
- Generated/read-only headers on narrative artifacts could become noisy. Mitigation: apply them only where they prevent manual-edit ambiguity and keep owner-facing full views readable.
- Adding contribution or question types without a rendering model could create a second ambiguous input layer. Mitigation: add types only with renderer/synthesis behavior or use a clear categorized contribution model.
- The full proposal view could become overwhelming. Mitigation: keep existing compact output stable and expose richer detail through `--full`, `render`, or an equivalent additive surface.
- Artifact catalog state could become stale when files change. Mitigation: derive legacy status when needed and keep write/import/render operations responsible for refreshing logical state.
- The routing playbook could make agents over-process simple requests. Mitigation: keep chat-only exploration as a first-class route and preserve the exception for exact owner-requested artifacts.
- `stable_documentation` could be misread as P2P owning all durable repository docs. Mitigation: document it as a write class requiring preview/classification, not as a governance ownership claim.
- Mentioning `--root` could be misread as recommending sibling repositories. Mitigation: document decision root as independent from repository topology and keep sibling repository support explicitly out of scope.
- Decision-root and MCP hint hardening could be treated as optional hygiene. Mitigation: classify them as core operational work because agents need them to apply the semantic model in the right workspace.
- Vertical language could blur core and software-specific behavior. Mitigation: use "explicit vertical primitives" in core docs and route software-spec requests to PROP-094 rather than making `specs` a generic P2P primitive.
- `.gitignore` handling could overwrite owner repository policy. Mitigation: append or offer changes non-destructively, never ignore `.p2p/`, and separate hygiene from governed P2P state in summaries.
