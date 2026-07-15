# P2P Engine

## Executive Summary

P2P Engine e un motore locale e Git-native per trasformare intenzioni,
conversazioni e decisioni in memoria di progetto governata, verificabile e
riutilizzabile da persone e agenti. Il prodotto mantiene separati lo stato
canonico sotto `.p2p/`, gli output derivati per consultazione o handoff e il
codice applicativo del repository.

Lo stato corrente comprende 100 proposte, delle quali 95 formano la base di
autorita impegnata: 94 sono `accepted` e una e `accepted_with_changes`. Il
progetto dispone di 68 Change Set, con il solo `CHANGE-068` ancora attivo in
stato `implementation_ready`, e di quattro Work terminali. La validazione e
pulita, il runtime `0.2.0` e compatibile e il workspace usa lo schema v1 senza
migrazione o recovery pendente.

La direzione centrale e preservare l'intento in Markdown e YAML leggibili,
senza ridurre la memoria a registri lossy. Registri, proiezioni, indice del
contesto decisionale, assessment, specifiche e pubblicazioni sono viste
derivate e ricostruibili. CLI e MCP forniscono le primitive operative; l'owner
mantiene l'autorita su decisioni, scelte, accettazioni, merge e pubblicazione.

Questo documento e una pubblicazione umana curata. Non sostituisce `.p2p/` e
non implica approvazione editoriale: validazione, rendering e review owner sono
stadi distinti della pipeline.

## Project Identity And Vertical Framing

P2P Engine e governato come progetto software. Il verticale attivo
`software_project` e selezionato, bloccato alla versione `1.0.0` e valido. Il
verticale organizza il progetto attorno a obiettivi di sistema, utenti e
attori, confini MVP, workflow, modello dati, integrazioni, requisiti non
funzionali, validazione e decisioni di implementazione.

La definizione ha 19 sezioni richieste. La completezza esplicita e 40/43 unita
(93.02%); la copertura di evidenza owner-declared e 13/19 sezioni (68.42%). I
due valori misurano cose diverse: il primo descrive quanto e definito il
progetto, il secondo quanta definizione e collegata a proposte attive tramite
coverage dichiarata. I 390 match euristici sono suggerimenti esclusi dal
numeratore autorevole.

Sedici sezioni sono complete, due parziali e una e `assumed`. Dodici proposte
compongono il primo batch di coverage confermato dall'owner; le altre 88
restano intenzionalmente legacy e non mappate. Sei sezioni complete non hanno
evidenza di proposta dichiarata: non sono per questo definizioni mancanti.

## Current Project Shape

### Governed Project Memory

La memoria canonica comprende progetto, proposte, contributi, domande,
readiness, artifact state, decisioni, choice, conflitti, precedenti, Change Set,
Work e relazioni verticali. Le mutazioni devono passare dalla CLI o da
primitive MCP esplicitamente write-safe; gli agenti non devono ricostruire o
modificare manualmente i layout sotto `.p2p/`.

Il ciclo proposta-decisione conserva alternative, rischi, assunzioni e
motivazioni. Readiness e rubriche sono advisory: rendono visibili lacune e gate,
ma non sostituiscono il giudizio dell'owner. Riferimenti principali: PROP-002,
PROP-012, PROP-016, PROP-017, PROP-018, PROP-054, PROP-056, PROP-082, PROP-086,
PROP-089 e PROP-096.

### Decision Context And Proposal Neighborhood

La direzione accettata in PROP-100 affronta la perdita informativa tra fonti
canoniche e viste derivate. L'indice corrente e request-scoped, source-linked e
read-only: distingue authority, activation, confidence, completeness,
provenance e freshness; normalizza relazioni tipizzate e applica ranking e
budget spiegabili senza fallback first-N.

L'indice ricostruito contiene 1,353 fonti, 2,944 evidenze, 2,218 record
semantici, 544 nodi e 667 relazioni valide. Non risultano relazioni invalide,
ambigue o non supportate. La completezza resta correttamente `partial` per due
divergenze intenzionali tra stato draft e autorita pending in PROP-063 e
PROP-098. Un eventuale indice persistente o un cambio di storage restano
decisioni future basate su misure, non prerequisiti di questa architettura.

### Delivery, Work And Git Collaboration

Le proposte accettate possono alimentare Change Set, task e Work. I lifecycle
distinguono pianificazione, readiness di implementazione, esecuzione, review e
stati terminali. La collaborazione Git gestita copre branch, publish, review,
merge, finalize, cleanup e retire, con `main` come contenitore dello stato
accettato e con operazioni sensibili soggette ad autorita o consent receipt.

Questa superficie deriva soprattutto da PROP-013, PROP-015 e PROP-030 fino a
PROP-043, con gli sviluppi di collaborazione concorrente in PROP-072 e della
parita MCP Work in PROP-092 e PROP-093. I quattro Work presenti sono terminali;
non sono prova che ogni Change Set sia completato.

### CLI, MCP And Agent Boundaries

La CLI e l'interfaccia locale di riferimento. MCP espone letture bounded e un
insieme dichiarato di operazioni di scrittura; non e un IAM hosted, non concede
mutazioni arbitrarie e non trasforma nomi locali di attore in autenticazione
forte. Le azioni esterne o di governance restano capability-limited e, quando
previsto, permission-gated.

Le integrazioni agent sono generate da template di release e gestite tramite
un lifecycle di installazione e aggiornamento. Le skill adapter-specifiche non
sono una fonte alternativa di governance. Riferimenti: PROP-005, PROP-006,
PROP-044 fino a PROP-052, PROP-065, PROP-066, PROP-075, PROP-077, PROP-081,
PROP-088, PROP-092 e PROP-093.

### Specifications, Validation And Derived Outputs

Il lifecycle delle specifiche collega Change Set accettati a specifiche P2P e
handoff downstream, mantenendo distinti input canonici, output generati e
documenti locali di sviluppo sotto `specs/`. Undici Change Set dispongono oggi
di una specifica generata conforme al contratto corrente. Riferimenti:
PROP-026, PROP-027, PROP-028, PROP-029, PROP-064 e PROP-094.

Runtime e workspace schema sono contratti indipendenti. Il repository usa
runtime `0.2.0`, range compatibile `>=0.2.0,<0.3.0` e workspace schema v1. Le
migrazioni sono forward-only, transazionali, preserve-by-default e separate
dalle correzioni semantiche owner-reviewed. Il grafo di freshness ordina la
ricostruzione degli output e non considera un artefatto approvato per la sola
presenza del file.

### Human Project Publication

PROP-099 definisce una sola pubblicazione umana canonica, non varianti per
audience. La pipeline separa export deterministico, profilo, packet del
curatore, Markdown curato, validazione, PDF e review owner. Questa separazione
permette di rigenerare o correggere uno stadio senza modificare lo stato
governato o attribuire approvazioni implicite.

## Current Operating State

| Area | Stato corrente | Interpretazione |
| --- | --- | --- |
| Runtime | `0.2.0`, compatibile | Contratto operativo valido |
| Workspace schema | v1, `layout_current`, aligned | Nessuna migrazione o recovery attiva |
| Verticale | `software_project` 1.0.0, lock valido | Struttura software formalmente attiva |
| Proposte | 100 totali, 95 committed, 2 draft | Draft e storia non sono autorita attiva |
| Change Set | 68 totali, 1 attivo | `CHANGE-068` e `implementation_ready` |
| Work | 4 terminali | Nessun Work attivo |
| Definizione | 40/43, 93.02% | Completezza esplicita delle sezioni |
| Evidenza verticale | 13/19, 68.42% | Solo coverage dichiarata dall'owner |
| Validazione | 0 errori, 0 warning | Stato strutturale pulito |
| Pubblicazione | Markdown validato e PDF draft renderizzato | Review owner mancante; approvazione false |

## Planned And Pending Work

`CHANGE-068`, Human Project Publication Pipeline, e l'unico Change Set attivo.
Il codice e le primitive della pipeline sono utilizzabili, ma lo stato
governato resta `implementation_ready`: il completamento deve avvenire tramite
il lifecycle previsto e non puo essere dedotto dall'esistenza degli output.

La migrazione effettiva del workspace ha completato allineamento di runtime e
schema, verticale e definizione, correzione delle relazioni storiche, primo
batch di coverage e ricostruzione degli output fino al PDF draft validato.
Restano i controlli finali di M5 e la comparazione con la baseline. La review di
pubblicazione resta deliberatamente fuori dalla migrazione automatica.

Due proposte sono ancora pending owner decision:

- PROP-063, `Public Documentation Gap Closure`, e draft con readiness bassa e
  propone tutorial, glossario e chiusura dei gap della documentazione pubblica.
- PROP-098, `Test Impact and Validation Routing`, e draft e propone routing
  deterministico dei test in base alle aree modificate e al rischio.

PROP-100 non e piu lavoro pending: e una direzione architetturale accettata e
costituisce la base dell'indice decisionale corrente.

## Risks, Assumptions And Open Questions

I rischi principali sono la confusione tra fonti canoniche e viste derivate, la
staleness dopo mutazioni, l'uso di euristiche come se fossero autorita, le
scritture multi-file parziali, il source drift tra preview e apply e
l'attribuzione implicita di approvazione ad artefatti generati. Le mitigazioni
sono provenance e freshness esplicite, transazioni atomiche con rollback,
preimage checks, policy di authority condivise, budget bounded e stage owner o
curator separati.

Restano inoltre tre rischi operativi visibili:

- le 88 proposte non mappate sono storia valida, ma non coverage verticale
  dichiarata;
- le due divergenze draft/pending mantengono l'indice parziale per scelta, non
  per errore del parser;
- assessment e maturity legacy usano ancora un fallback esplicito basato su
  contenuto e mtime, mentre progress espone i due assi autorevoli separati.

Due assunzioni sono ancora `to_validate`: il progetto continua a disporre di un
filesystem locale scrivibile con Git come audit substrate, e un owner
responsabile resta disponibile per decisioni e curatela semantica. E invece
validata l'assunzione che registri e indici deterministici possano essere
ricostruiti dalle fonti governate.

Le decisioni owner ancora aperte riguardano PROP-063, PROP-098, l'eventuale
chiusura governata di CHANGE-068 e la review finale della pubblicazione. Cache
persistente del decision context, database, migrazioni remote di flotte e
automazione delle fasi curator/owner restano alternative rinviate.

## Source Of Truth And Publication Status

`.p2p/` remains authoritative for project identity, proposals, decisions,
readiness, choices, Change Sets, Work, permissions, vertical definition and
governance state. `outputs/latest/project.md` is a deterministic generated
export. This curated document is a derived human-readable publication draft.

La validazione del Markdown e il rendering PDF non costituiscono review. Lo
stato `approved_for_publication` deve restare falso finche l'owner non registra
esplicitamente un esito attraverso la primitiva dedicata.

## Traceability Notes

Il packet di curatela e `outputs/latest/curator-input.md`. Il source export
`outputs/latest/project.md` ha sha256
`671c6355d8863fc0e05afd264d941b89aa470d281e189523ceca7f2c0536027e`;
il fingerprint P2P del packet e
`8b3c645679a359a99b96108a90701d2146544e146a59d5cc24b22810269f5054`.
Il profilo applicato e `neutral-v1-standard`, audience mixed, depth standard,
struttura verticale adaptive e nessuna appendice.

Le capacita principali sono tracciate ai seguenti gruppi: fondazione e memoria
(PROP-001, PROP-002, PROP-009, PROP-010, PROP-012, PROP-016), intake e decision
flow (PROP-017 fino a PROP-025), specifiche (PROP-026 fino a PROP-029, PROP-064,
PROP-094), Work e Git (PROP-030 fino a PROP-043, PROP-072), MCP e agenti
(PROP-044 fino a PROP-052, PROP-065, PROP-066, PROP-075, PROP-077, PROP-081,
PROP-088, PROP-092, PROP-093), verticali e definizione (PROP-071, PROP-083,
PROP-085, PROP-090), runtime e release (PROP-058, PROP-061, PROP-062, PROP-067
fino a PROP-070, PROP-073, PROP-074, PROP-078, PROP-080, PROP-095, PROP-097),
readiness e qualita (PROP-054, PROP-056, PROP-057, PROP-060, PROP-082,
PROP-086, PROP-089, PROP-096), decision context (PROP-100) e pubblicazione
umana (PROP-099).
