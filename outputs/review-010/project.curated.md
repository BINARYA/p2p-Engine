# P2P Engine

## Executive Summary

P2P Engine e un motore locale, Git-native e file-backed che trasforma
intenzioni, conversazioni e decisioni in memoria di progetto governata,
verificabile e riutilizzabile da persone e agenti. Il prodotto mantiene
separati lo stato canonico sotto `.p2p/`, gli output derivati per consultazione
o handoff e il codice applicativo del repository.

Il repository contiene 102 proposte. La base corrente di autorita attiva ne
comprende 97: 96 sono `accepted` e una e `accepted_with_changes`. Una proposta
e `deferred`, due sono draft e due restano storia esplicita, una `split` e una
`superseded`. Sono presenti 70 Change Set: 67 completati,
`CHANGE-068` e `CHANGE-069` sono `implementation_ready`, mentre `CHANGE-070`
e `in_progress`. I quattro Work manifest presenti sono terminali.

Il runtime installato `0.4.1` e compatibile con il contratto
`>=0.4.0,<0.5.0`. Il workspace usa lo schema v3, e allineato e non presenta
lock o recovery pendenti. Lo schema v3 rende la storia delle decisioni
append-only: una proposta mai attiva puo essere rifiutata, mentre una decisione
precedentemente accettata deve essere revocata o chiusa tramite lineage
tipizzata senza cancellarne l'autorita storica.

La direzione centrale resta preservare intento, motivazioni e provenienza nei
Markdown e YAML governati senza ridurre la memoria a registri lossy. Registri,
proiezioni, decision context, assessment, specifiche, next action ed export
sono viste derivate e ricostruibili. CLI e MCP forniscono primitive operative
controllate; l'owner mantiene l'autorita sulle decisioni di governance,
definizione, delivery e pubblicazione.

Questo documento e una pubblicazione umana curata. Non sostituisce `.p2p/` e
non implica approvazione: preparazione, curatela, import, validazione, rendering
e review owner sono stadi distinti.

## Project Identity And Vertical Framing

P2P Engine e governato come progetto software. Il verticale attivo
`software_project` e valido e organizza il progetto attorno a obiettivi di
sistema, utenti e attori, confini MVP, workflow, modello dati, integrazioni,
requisiti non funzionali, validazione, rischi e decisioni di implementazione.

Il verticale contiene 19 sezioni richieste. La completezza esplicita e 40/43
unita (93.02%); la copertura di evidenza dichiarata dall'owner e 13/19 sezioni
(68.42%). I valori misurano aspetti diversi: il primo descrive quanto il
progetto e definito, il secondo quanta definizione e collegata a proposte
attive attraverso coverage dichiarata. I 433 match euristici sono suggerimenti
e non entrano nel numeratore autorevole.

Tre sezioni richieste restano incomplete: `assumptions`, `decisions` e
`risks_alternatives_decisions`. Le assunzioni `A001` e `A002` richiedono ancora
validazione owner. La domanda `PRQ-7070e7a631b1df44` resta `to_answer` per
`risks_alternatives_decisions`; non contiene una risposta ne una patch
applicata. Questi sono gap di input, non difetti della migrazione.

## Current Project Shape

### Governed Project Memory And Decision Lifecycle

La memoria canonica comprende identita del progetto, proposte, contributi,
domande, readiness, decision event, choice, conflitti, precedenti, Change Set,
Work, permessi e relazioni verticali. Le mutazioni passano dalla CLI o da
primitive MCP esplicitamente write-safe; gli agenti non devono ricostruire o
modificare manualmente il layout sotto `.p2p/`.

`PROP-102` introduce un ledger decisionale versionato per proposta. Il ledger
e la fonte semantica della storia; lo stato in `proposal.md` e il documento
decisionale leggibile sono proiezioni compatibili. Preview e apply sono
separati, legati a source head, token, operation key e autorita owner. Retry,
concorrenza, recovery e repair hanno contratti espliciti.

Revoca, supersession, split, merge e reinstatement preservano gli intervalli di
autorita. `PROP-007` e registrata come split verso `PROP-017` e `PROP-025`;
`PROP-008` e superseded da `PROP-091`. Restano recuperabili come storia
ever-active, ma non fanno parte dei vincoli attivi. La migrazione v2-v3 e stata
applicata in modo transazionale e tutte le autorita legacy residue sono state
curate dall'owner; non rimangono proposte `unknown_legacy`.

### Project Readiness Convergence

`PROP-101` rende la readiness un workflow governato, non soltanto un report.
Le domande di progetto hanno identita, revisione, stato, applicabilita e
provenienza. Le risposte possono generare candidate patch, ma la definizione
cambia soltanto tramite preview anti-stale e conferma owner.

L'assessment deterministico corrente e 68/100 (`needs_review`, confidence
alta), mentre la rubric maturity e 100/100 (`well_defined`). Sono misure con
basi diverse e non devono essere fuse in una percentuale unica. I gap
strutturali e gli input owner rimangono visibili anche quando le rubriche
considerano il progetto ben trattato.

### Decision Context And Proposal Neighborhood

`PROP-100` affronta la perdita informativa tra fonti canoniche e viste
derivate. L'indice request-scoped distingue authority, activation, confidence,
completeness, provenance e freshness; normalizza relazioni tipizzate e usa
ranking e budget spiegabili invece di un fallback first-N.

Il build corrente comprende 1.486 fonti, 3.249 evidenze, 2.495 record
semantici, 716 nodi e 1.019 relazioni valide, senza diagnostiche. Il fingerprint
semantico e
`98d5d382182932c0a8b710b4412d4ac3e95c727a84b882aa4a0954fb52661a8c`.
Le decisioni storiche restano recuperabili come motivazioni e alternative, ma
non sono presentate come autorita corrente.

### Delivery, Work And Git Collaboration

Le proposte accettate possono alimentare Change Set, task e Work. I lifecycle
distinguono pianificazione, readiness di implementazione, esecuzione, review e
stati terminali. La collaborazione Git gestita copre branch, publish, review,
merge, finalize, cleanup e retire; le operazioni sensibili restano soggette ad
autorita o consent receipt.

Questa superficie deriva soprattutto da `PROP-013`, `PROP-015` e
`PROP-030`-`PROP-043`, con collaborazione concorrente in `PROP-072` e parita MCP
Work in `PROP-092` e `PROP-093`. I quattro Work presenti sono terminali, ma
questo non prova che ogni Change Set sia completato.

### CLI, MCP And Agent Boundaries

La CLI e la superficie locale di riferimento. MCP offre letture bounded e un
insieme dichiarato di operazioni write-safe; non concede mutazioni arbitrarie
e non trasforma un nome locale di attore in autenticazione forte. Le decisioni
owner-controlled restano separate dall'esecuzione tecnica dell'agente.

Le integrazioni agent sono generate dai template di release e gestite tramite
il relativo lifecycle. Le skill adapter-specifiche non sono una fonte
alternativa di governance. Riferimenti principali: `PROP-005`, `PROP-006`,
`PROP-044`-`PROP-052`, `PROP-065`, `PROP-066`, `PROP-075`, `PROP-077`,
`PROP-081`, `PROP-088`, `PROP-092` e `PROP-093`.

### Specifications, Validation And Derived Outputs

Il lifecycle delle specifiche collega Change Set accettati a specifiche P2P e
handoff downstream, mantenendo distinti input canonici, output generati e
documenti locali di sviluppo sotto `specs/`. La specifica di `CHANGE-070` e
semanticamente corrente. Dodici specifiche storiche restano
`unknown_origin`: sono evidenza legacy esplicita e non devono essere
sovrascritte solo per eliminare il diagnostico.

Registri e proiezioni sono correnti: 102 proposte, 102 decisioni, 70 Change
Set, due choice, 140 relazioni, 2.459 artifact record e 102 readiness record.
La proiezione attiva comprende 97 proposte. La validazione strutturale del
workspace non riporta errori, warning o informazioni.

Il sorgente locale contiene una correzione post-release che riusa lo stesso
snapshot di freshness nelle next action e nell'assessment, evitando
ricostruzioni duplicate nella stessa richiesta. Le regressioni mirate, la
suite pubblica, la suite completa e il package smoke sono verdi. Una singola
costruzione completa del grafo resta tuttavia costosa e richiede un successivo
intervento prestazionale separato.

### Human Project Publication

`PROP-099` definisce una sola pubblicazione umana canonica, non varianti per
audience. La pipeline separa export deterministico, profilo, packet del
curatore, Markdown curato, validazione, PDF e review owner. Uno stadio puo
essere rigenerato senza modificare decisioni governate o attribuire
approvazioni implicite.

## Current Operating State

| Area | Stato corrente | Interpretazione |
| --- | --- | --- |
| Runtime | `0.4.1`, compatibile | Contratto `>=0.4.0,<0.5.0` valido |
| Workspace schema | v3, current e aligned | Nessuna migrazione o recovery attiva |
| Verticale | `software_project`, lock valido | Struttura software formalmente attiva |
| Proposte | 102 totali, 97 attive, 2 draft | Split e superseded sono storia, non autorita corrente |
| Change Set | 70 totali, 3 attivi | `CHANGE-068`, `CHANGE-069`, `CHANGE-070` |
| Work | 4 terminali | Nessun Work attivo |
| Definizione | 40/43, 93.02% | Tre sezioni richieste non complete |
| Evidenza verticale | 13/19, 68.42% | Solo coverage dichiarata dall'owner |
| Assessment | 68/100, `needs_review` | Diagnostica operativa, distinta dalla maturity |
| Maturity | 100/100, `well_defined` | Copertura delle rubriche, non completion |
| Decision context | 716 nodi, 1.019 relazioni | Request-scoped, senza diagnostiche |
| Software spec | `CHANGE-070` current, 12 legacy | Nessuna riscrittura automatica delle fonti ignote |
| Validazione | 0 errori, 0 warning | Workspace strutturalmente valido |
| Pubblicazione | Curatela in corso | Review owner mancante; approvazione false |

## Planned And Pending Work

`CHANGE-068` implementa la Human Project Publication Pipeline da `PROP-099`.
`CHANGE-069` implementa il Project Readiness Convergence Workflow da
`PROP-101`. Entrambi restano `implementation_ready`. `CHANGE-070` implementa
il Proposal Decision Revision and Revocation Lifecycle da `PROP-102` ed e
`in_progress`. Codice e test non possono cambiare automaticamente questi stati:
la loro chiusura richiede il normale lifecycle owner-controlled.

Il core di `PROP-102`, la release v3-capable e la migrazione del repository
sono completati. Restano da consolidare le correzioni locali emerse
nell'allineamento, registrare l'evidenza finale e decidere il successivo
rilascio senza sovrapporlo alla decisione sul Change Set.

Due proposte sono ancora pending owner decision:

- `PROP-063`, Public Documentation Gap Closure, resta draft;
- `PROP-098`, Test Impact and Validation Routing, resta draft.

Le prossime azioni di definizione sono governate separatamente: rispondere o
deferire `PRQ-7070e7a631b1df44`, validare `A001` e `A002` e decidere se i gap
facoltativi di evidenza richiedano altra coverage dichiarata.

## Risks, Assumptions And Open Questions

I rischi principali sono la confusione tra fonti canoniche e viste derivate,
la staleness dopo mutazioni, l'uso di euristiche come autorita, le scritture
multi-file parziali, il source drift tra preview e apply e l'attribuzione
implicita di approvazione agli output. Le mitigazioni sono provenance e
freshness esplicite, transazioni atomiche, preimage check, policy condivise,
payload bounded e stage owner o curator separati.

Restano quattro limiti operativi:

- le dodici software spec `unknown_origin` richiedono provenienza o review e
  non possono essere normalizzate automaticamente;
- il decision context resta request-scoped e non dispone di uno snapshot
  persistente, per scelta dell'attuale contratto;
- le operazioni che enumerano tutte le sorgenti richiedono diversi minuti
  nonostante il riuso dello snapshot nella singola richiesta;
- la pubblicazione puo essere preparata, curata, validata e renderizzata senza
  essere approvata: la review resta un atto separato dell'owner.

Le assunzioni `A001` e `A002` restano `to_validate`. Le decisioni owner aperte
riguardano `PROP-063`, `PROP-098`, la domanda di progetto, le due assunzioni,
la chiusura dei tre Change Set attivi e la review della pubblicazione. Cache
persistente del decision context, database e compattazione tematica della
memoria restano direzioni future, non capacita implicite del runtime corrente.

## Source Of Truth And Publication Status

`.p2p/` remains authoritative for project identity, proposals, decision event,
readiness, project questions, choice, Change Set, Work, permissions, vertical
definition and governance state. `outputs/latest/project.md` is a deterministic
generated export. This curated document is a derived human-readable
publication draft.

La validazione del Markdown e il rendering PDF non costituiscono review. Lo
stato `approved_for_publication` deve restare falso finche l'owner non registra
esplicitamente un esito attraverso la primitiva dedicata.

## Traceability Notes

Il packet di curatela e `outputs/latest/curator-input.md`. Il source export
`outputs/latest/project.md` ha SHA-256
`ad48e9cce8d6334972458ec8beccb9cd13393b428df9bb54c90580164b9bede0`;
il fingerprint P2P del packet e
`6a04a21c67b9a20ccded33718e2e646386d909d9d239940358265423800f8a1b`.
Il profilo applicato e `neutral-v1-standard`, audience mixed, depth standard,
struttura verticale adaptive e nessuna appendice.

Le capacita principali sono tracciate ai seguenti gruppi: fondazione e memoria
(`PROP-001`, `PROP-002`, `PROP-009`, `PROP-010`, `PROP-012`, `PROP-016`);
intake e decision flow (`PROP-017`-`PROP-025`, `PROP-102`); specifiche
(`PROP-026`-`PROP-029`, `PROP-064`, `PROP-094`); Work e Git
(`PROP-030`-`PROP-043`, `PROP-072`); MCP e agenti (`PROP-044`-`PROP-052`,
`PROP-065`, `PROP-066`, `PROP-075`, `PROP-077`, `PROP-081`, `PROP-088`,
`PROP-092`, `PROP-093`); verticali e definizione (`PROP-071`, `PROP-083`,
`PROP-085`, `PROP-090`); runtime e release (`PROP-058`, `PROP-061`, `PROP-062`,
`PROP-067`-`PROP-070`, `PROP-073`, `PROP-074`, `PROP-078`, `PROP-080`,
`PROP-095`, `PROP-097`); readiness e qualita (`PROP-054`, `PROP-056`,
`PROP-057`, `PROP-060`, `PROP-082`, `PROP-086`, `PROP-089`, `PROP-096`,
`PROP-101`); decision context (`PROP-100`) e pubblicazione (`PROP-099`).
