# PROP-052 - MCP Proposal Contribution Tool

## Status

`accepted`

## Problem

Agents can create new draft proposals through MCP, but cannot safely attach new information to an existing proposal. This encourages proposal proliferation when a comment, criterion, objection, or suggestion should be recorded as a contribution instead.

## Context

The La scatola perfetta test produced multiple related draft proposals. P2P already has a controlled CLI contribution command and core method. Exposing that primitive through MCP is safer than letting agents create separate proposals for every related idea.

## Goals

- Allow MCP clients to add typed contributions to existing proposals without making governance decisions.

## Non-Goals

- Pending.

## Proposal

Add MCP tool p2p_proposal_contribution_add. It appends a typed contribution to a proposal using the existing core contribution model. It may record suggestion, objective, constraint, risk, objection, alternative proposal, and similar contribution types. It must not accept/reject/defer proposals, merge proposals, decide choices, or alter decision files.

## Acceptance Criteria

- MCP exposes p2p_proposal_contribution_add; the tool appends to contributions.yml and returns the new contribution; tests cover adding a contribution and verify decision status remains pending and governance tools remain absent.

## Decision

Pending.
