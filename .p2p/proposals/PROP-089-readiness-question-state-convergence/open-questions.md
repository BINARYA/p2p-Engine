# Open Questions - PROP-089

- Should high-priority unresolved structured questions be the only default hard
  blocker for `owner_questions_resolution`?
  Recommended answer: yes.
- Should medium/low unresolved questions lower confidence instead of creating a
  failed gate?
  Recommended answer: yes, unless a future policy marks them blocking.
- Should `open-questions.md` remain part of readiness evidence when
  `questions.yml` exists?
  Recommended answer: yes as human-readable evidence, but not as lifecycle
  authority.
- Should `questions apply` automatically update group state when all questions
  in the group are resolved?
  Recommended answer: yes, but as a compatibility-safe enhancement with tests.

