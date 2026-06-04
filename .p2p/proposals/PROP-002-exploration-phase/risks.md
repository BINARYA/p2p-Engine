# Risks - PROP-002

## R1 - Confusione tra explore e digest

Rischio:
`explore` potrebbe essere usato come sinonimo di digest.

Mitigazione:
Documentare chiaramente che explore scopre implicazioni e digest riassume
contributi gia raccolti.

## R2 - Conversazioni non persistite

Rischio:
Le esplorazioni fatte dentro agenti AI restano nella chat e non entrano nel
repository.

Mitigazione:
Richiedere import o salvataggio negli artefatti P2P.

## R3 - Falsificazione della maturity tramite override

Rischio:
Se l'override owner forza direttamente il valore calcolato a 100, il sistema
perde onesta analitica.

Mitigazione:
Separare `computed_score` dalla governance decision. L'override crea un audit
event come `accept_with_override`, preservando score, failed gates e reason.

## R4 - Score percepito come decisione automatica

Rischio:
Utenti o agenti potrebbero interpretare readiness alta come accettazione
automatica, o readiness bassa come rifiuto automatico.

Mitigazione:
Documentare che readiness e lifecycle state sono separati. La readiness supporta
la decisione, ma l'owner mantiene il controllo.

## R5 - Pedanteria eccessiva sulle proposte piccole

Rischio:
Un modello di maturity troppo uniforme potrebbe rallentare correzioni semplici
o trasformare ogni proposta in un esercizio burocratico.

Mitigazione:
Usare tier, soglie e gate diversi. Small proposal ha percorso leggero, ma non
zero-governance.

## R6 - Compensazione impropria del punteggio

Rischio:
Una proposta potrebbe raggiungere uno score totale alto grazie a criteri
secondari, pur avendo lacune essenziali.

Mitigazione:
Introdurre minimum gate per tier. Il total score misura maturita complessiva,
ma i gate impediscono readiness automatica quando mancano criteri essenziali.

## R7 - Testo generico usato per raggiungere lo score

Rischio:
Un agente potrebbe compilare artifact lunghi ma vaghi, ottenendo punteggi alti
senza migliorare davvero la proposta.

Mitigazione:
Collegare ogni criterio a evidenze specifiche e usare artifact quality gate.
Un artifact non puo essere `meaningful` o `ready` senza claim, vincoli,
decisioni, tradeoff o evidenze specifiche della proposal.

## R8 - Score alto ma bassa affidabilita

Rischio:
La proposta potrebbe essere ben scritta ma basata su informazioni non validate,
ipotesi fragili o impatti non verificati.

Mitigazione:
Aggiungere `confidence` e `confidence_reasons`. Per proposal governance-critical,
low confidence impedisce automatic `ready_for_decision`.

## R9 - Classificazione tier incoerente

Rischio:
Agenti diversi potrebbero classificare la stessa proposta in tier diversi,
alterando soglie e gate richiesti.

Mitigazione:
Agent/system suggeriscono il tier, owner conferma. Il sistema segnala downgrade
incoerenti rispetto alle evidenze.

## R10 - Readiness profile non versionato

Rischio:
Uno score senza profilo e versione non e interpretabile nel tempo.

Mitigazione:
Ogni assessment registra `profile_id`, `profile_version` e `computed_at`.

## R11 - Registry scambiato per fonte di verita

Rischio:
Snapshot o registry readiness potrebbero diventare divergenti dagli artifact e
venire trattati come sorgente primaria.

Mitigazione:
Definire registries come cache/snapshot. Source of truth: artifact, profile,
assessment e governance audit record.

## R12 - MCP write trattato come autonomia agente

Rischio:
Se i tool MCP di override o accept-with-override sono esposti senza gate,
l'agente potrebbe superare la readiness o registrare decisioni governance senza
autorita owner.

Mitigazione:
MCP write/governance tools sono parte del modello, ma permission-gated. Gli
agenti possono leggere e spiegare readiness; override e accept richiedono
autorita esplicita.

## R13 - `needs_owner_input` confuso con artifact debole

Rischio:
Un artifact che richiede una scelta owner potrebbe essere classificato come
thin, spingendo l'agente a scrivere altro testo invece di chiedere una decisione.

Mitigazione:
Trattare `needs_owner_input` come stato distinto. `p2p next` deve proporre
azioni come `ask_owner`, `resolve_owner_question` o `confirm_policy`.
