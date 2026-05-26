# Execution Plan - PROP-009

## Objective

Rendere operativo il primo modello governance file-based tramite comandi CLI minimi e testati.

## Workstreams

### WS1 - Storage Governance

Implementare metodi filesystem per inizializzare governance, leggere stato governance, registrare voti e registrare precedenti.

### WS2 - CLI Commands

Aggiungere comandi:

- `p2p governance init`
- `p2p governance status`
- `p2p swot prompt`
- `p2p vote record`
- `p2p vote status`
- `p2p precedent record`

### WS3 - Prompt SWOT

Aggiungere renderer prompt-only per produrre una SWOT analysis orientata alla decisione, usando proposal, alternatives, risks, assumptions, votes e governance context.

### WS4 - Verification

Aggiungere test CLI end-to-end e aggiornare README/foundation.

## Validation

- `python -m pytest`
- `python -m compileall src tests`
