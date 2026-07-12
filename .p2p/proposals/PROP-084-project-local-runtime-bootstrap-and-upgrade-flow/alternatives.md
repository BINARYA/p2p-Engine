# Alternatives

## How-To Only

Rejected. A how-to without a machine-readable project contract does not give
P2P Engine a stable way to validate compatibility or gate governed writes.

## Installer-Oriented Contract

Rejected. A contract that stores release tags, wheel filenames, digests, source
descriptors, or install commands solves installer verification, not runtime
version alignment.

## Mandatory Script-Based Setup

Rejected. A script is an optional ergonomic layer and introduces a separate
distribution and trust problem. It is not required for this proposal.

## Broad Command Blocking

Rejected. Blocking all commands for legacy projects would disrupt existing
repositories. The accepted scope gates governed writes only when a declared or
required contract cannot be trusted.

## Minimal Contract Plus Project Guide

Accepted. `runtime.yml` provides the source of truth, `P2P-SETUP.md` makes it
visible to collaborators, runtime status validates compatibility, and the
write gate protects governed state mutation.
