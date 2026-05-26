# Risks - PROP-006

## R1 - Overengineering

Rischio:
Replicare troppa complessita di Spec Kit/OpenSpec prima che P2P abbia bisogno reale di molti agent.

Mitigazione:
Implementare solo registry minimo e due target iniziali: `codex` e `generic`.

## R2 - Agent-specific drift

Rischio:
Ogni agent richiede convenzioni diverse e i template divergono rapidamente.

Mitigazione:
Separare core workflow P2P da template specifici e aggiungere test snapshot sui file generati.

## R3 - Source of truth confusa

Rischio:
Gli agenti potrebbero iniziare a modificare file o prendere decisioni senza passare da CLI/artefatti P2P.

Mitigazione:
Ogni template deve ribadire che CLI/core e `.p2p/` sono la fonte di verita.

## R4 - Install/uninstall fragile

Rischio:
Rimuovere o aggiornare file agentici potrebbe cancellare modifiche manuali.

Mitigazione:
Tracciare manifest e hash dei file generati prima di implementare uninstall distruttivo.
