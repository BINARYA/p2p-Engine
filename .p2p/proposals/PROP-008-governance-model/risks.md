# Risks - PROP-008

## R1 - Confondere governance e permessi

Rischio:
Aspettarsi che file YAML impediscano davvero azioni non autorizzate.

Mitigazione:
Documentare chiaramente che il primo MVP e audit/governance, non authorization enforcement.

## R2 - Governance troppo pesante

Rischio:
Bloccare il bootstrap con voti e ruoli prima che il prodotto sia stabile.

Mitigazione:
Default `owner_decides`, voti solo quando serve una scelta esclusiva.

## R3 - Decisioni riproposte ciclicamente

Rischio:
La stessa scelta viene riaperta senza nuove informazioni.

Mitigazione:
Registrare `decision-precedents.yml` con condizioni di riapertura.

## R4 - SWOT usata come decisione

Rischio:
Gli utenti interpretano la SWOT generata dall'AI come decisione.

Mitigazione:
Ogni SWOT deve dichiarare che e decision support, non outcome.
