# Security Policy

P2P Engine is currently alpha software installed from source.

## Supported Versions

Only the default branch is actively considered for security fixes during this
early stage.

## Reporting A Vulnerability

Please do not publish exploit details in a public issue.

Report security concerns through GitHub's private vulnerability reporting if it
is enabled for the repository. If it is not enabled, open a minimal public issue
that says you have a security concern and asks for a private contact path, but do
not include sensitive details.

## Scope Notes

P2P Engine stores local project governance state under `.p2p/`. Treat `.p2p/`
contents as project data: review before sharing publicly if proposals, decisions,
or generated context contain sensitive information.

The local MCP server exposes project state to configured MCP clients. Only point
it at projects and clients you trust.
