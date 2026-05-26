# Clarifications — PROP-001

## Q1. Should the first CLI invoke AI directly?

No. The first CLI should generate prompt files only.

## Q2. Should the first CLI be Git-native?

Yes. It should work inside a Git repository and be ready for proposal branches, but it should not depend on GitHub.

## Q3. Should proposal branch creation be automatic?

Default branch creation is desirable, but it can be implemented after the basic file workflow is stable. The CLI should leave room for a `--no-branch` flag.

## Q4. What is the first implementation language?

Python with Typer.

## Q5. What is the first successful dogfooding milestone?

`PROP-002` can be created and managed with the newly built CLI instead of manual file creation.

