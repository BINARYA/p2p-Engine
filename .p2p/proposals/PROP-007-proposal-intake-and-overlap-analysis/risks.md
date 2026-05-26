# Risks - PROP-007

## R1 - Falsi positivi di overlap

Rischio:
Il sistema potrebbe suggerire che una nuova idea e gia coperta quando invece introduce una differenza importante.

Mitigazione:
Usare categorie qualitative (`high`, `medium`, `low`) e richiedere sempre reason testuale.

## R2 - Falsi negativi

Rischio:
Il sistema potrebbe creare nuove proposal duplicate.

Mitigazione:
Il prompt deve sempre includere lista sintetica delle proposal esistenti e criteri di confronto.

## R3 - Triage solo in chat

Rischio:
Codex potrebbe fare una buona analisi ma non salvarla negli artefatti P2P.

Mitigazione:
Introdurre import e artefatti dedicati.

## R4 - Complessita prematura

Rischio:
Inserire embeddings, database o ranking semantico troppo presto.

Mitigazione:
MVP file-based e prompt-only.
