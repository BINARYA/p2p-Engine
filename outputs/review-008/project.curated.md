# P2P Engine

## Executive Summary

P2P Engine e un motore locale e Git-native che trasforma intenzioni,
conversazioni e decisioni in memoria di progetto governata, verificabile e
riutilizzabile da persone e agenti. Il prodotto mantiene separati lo stato
canonico sotto `.p2p/`, gli output derivati per consultazione o handoff e il
codice applicativo del repository.

Lo stato corrente comprende 101 proposte. La base di autorita impegnata ne
contiene 96: 95 sono `accepted` e una e `accepted_with_changes`. Il progetto
dispone di 69 Change Set, 67 completati e due ancora
`implementation_ready` (`CHANGE-068` e `CHANGE-069`), e di quattro Work
terminali. Il runtime pubblicato `0.3.1` e compatibile con il contratto
`>=0.3.0,<0.4.0`; il workspace e stato migrato allo schema v2 e non presenta
lock o recovery pendenti.

La direzione centrale e preservare l'intento in Markdown e YAML leggibili,
senza ridurre la memoria a registri lossy. Registri, proiezioni, indice del
contesto decisionale, assessment, specifiche e pubblicazioni sono viste
derivate e ricostruibili. CLI e MCP forniscono le primitive operative; l'owner
mantiene l'autorita sulle decisioni, incluse risposte di progetto, modifiche
alla definizione, accettazioni, merge e approvazione editoriale.

Questo documento e una pubblicazione umana curata. Non sostituisce `.p2p/` e
non implica approvazione: import, validazione, rendering e review owner sono
stadi distinti della pipeline.

## Project Identity And Vertical Framing

P2P Engine e governato come progetto software. Il verticale attivo
`software_project` e selezionato, bloccato alla versione `1.0.0` e valido. Il
verticale organizza il progetto attorno a obiettivi di sistema, utenti e
attori, confini MVP, workflow, modello dati, integrazioni, requisiti non
funzionali, validazione, rischi e decisioni di implementazione.

La definizione ha 19 sezioni richieste. La completezza esplicita e 40/43 unita
(93.02%); la copertura di evidenza owner-declared e 13/19 sezioni (68.42%). I
due valori misurano aspetti diversi: il primo descrive quanto e definito il
progetto, il secondo quanta definizione e collegata a proposte attive tramite
coverage dichiarata. I match euristici restano suggerimenti esclusi dal
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

### Project Readiness Convergence

PROP-101 estende la readiness da diagnostica a workflow governato. Lo schema v2
introduce una memoria canonica delle domande di progetto con identita stabile,
revisione, applicabilita, transizioni e provenienza. Le risposte possono
produrre candidate patch, ma l'applicazione riusa preview token, controllo
anti-stale e conferma owner della definizione.

Nel workspace corrente risultano tre sezioni richieste incomplete:
`assumptions`, `decisions` e `risks_alternatives_decisions`. La migrazione ha
creato una sola domanda applicabile, `PRQ-7070e7a631b1df44`, per l'ultima
sezione. La domanda e ancora `to_answer`; non contiene risposte o applicazioni.
Per `assumptions` e `decisions` il sistema registra `no_safe_question`, evitando
di inventare input owner. Le assunzioni `A001` e `A002` restano da validare.

### Decision Context And Proposal Neighborhood

PROP-100 affronta la perdita informativa tra fonti canoniche e viste derivate.
L'indice corrente e request-scoped, source-linked e read-only: distingue
authority, activation, confidence, completeness, provenance e freshness;
normalizza relazioni tipizzate e applica ranking e budget spiegabili senza
fallback first-N.

Il build diagnostico corrente contiene 1,369 fonti, 3,187 evidenze, 2,327
record semantici, 588 nodi e 800 relazioni valide. Non risultano relazioni
invalide, ambigue o non supportate. Le due sole diagnostiche di fonte sono le
divergenze intenzionali tra stato draft e autorita pending in PROP-063 e
PROP-098. La domanda di progetto senza risposta e indicizzata come stato di
sistema inattivo, non come decisione accettata.

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
documenti locali di sviluppo sotto `specs/`. Dodici Change Set dispongono di
una specifica generata conforme al contratto corrente. Il confronto isolato
con candidate appena generate non rileva differenze nei file richiesti,
incluse le specifiche di `CHANGE-068` e `CHANGE-069`.

Runtime e workspace schema sono contratti indipendenti. Il runtime `0.3.1`
mantiene la lettura compatibile dello schema v1 e fornisce la migrazione
forward-only allo schema v2. La migrazione applicata e transazionale,
preserve-by-default, idempotente e separata dalle correzioni semantiche
owner-reviewed. Ha preservato 179 artefatti legacy sconosciuti, creato lo store
canonico delle domande e lasciato invariata la definizione del progetto.

Il grafo di freshness ordina la ricostruzione degli output e non considera un
artefatto approvato per la sola presenza del file. Assessment, maturity e
software specs conservano alcuni fallback legacy basati su contenuto o mtime;
nel caso delle specifiche il confronto delle candidate e l'evidenza semantica
che nessun file richiesto deve essere riscritto.

### Human Project Publication

PROP-099 definisce una sola pubblicazione umana canonica, non varianti per
audience. La pipeline separa export deterministico, profilo, packet del
curatore, Markdown curato, validazione, PDF e review owner. Questa separazione
permette di rigenerare uno stadio senza modificare lo stato governato o
attribuire approvazioni implicite.

## Current Operating State

| Area | Stato corrente | Interpretazione |
| --- | --- | --- |
| Runtime | `0.3.1`, compatibile | Contratto `>=0.3.0,<0.4.0` valido |
| Workspace schema | v2, current e aligned | Nessuna migrazione o recovery attiva |
| Verticale | `software_project` 1.0.0, lock valido | Struttura software formalmente attiva |
| Proposte | 101 totali, 96 committed, 2 draft | Draft e storia non sono autorita attiva |
| Change Set | 69 totali, 2 attivi | `CHANGE-068` e `CHANGE-069` sono `implementation_ready` |
| Work | 4 terminali | Nessun Work attivo |
| Definizione | 40/43, 93.02% | Tre sezioni richieste non complete |
| Evidenza verticale | 13/19, 68.42% | Solo coverage dichiarata dall'owner |
| Domande di progetto | 1 `to_answer`, 2 `no_safe_question` | Nessuna risposta o patch applicata |
| Validazione strutturale | 0 errori, 0 warning | Ultimo controllo del workspace pulito |
| Pubblicazione | Export, packet, curato, validation e PDF correnti | Review owner mancante; approvazione false |

## Planned And Pending Work

`CHANGE-068`, Human Project Publication Pipeline, e `CHANGE-069`, Project
Readiness Convergence Workflow, sono i due Change Set attivi. Le implementazioni
sono presenti nel runtime pubblicato e le rispettive specifiche sono correnti,
ma lo stato governato resta `implementation_ready`: il completamento richiede
il normale lifecycle owner-controlled e non puo essere dedotto dal codice o
dagli output esistenti.

La migrazione dello schema, il confronto con la baseline e la registrazione dei
limiti diagnostici residui sono completati. Il nuovo ciclo di pubblicazione e
stato preparato, curato, validato e renderizzato; la review owner resta fuori
dalla migrazione e dall'automazione agent.

Due proposte sono ancora pending owner decision:

- PROP-063, `Public Documentation Gap Closure`, e draft con readiness bassa e
  propone tutorial, glossario e chiusura dei gap della documentazione pubblica.
- PROP-098, `Test Impact and Validation Routing`, e draft e propone routing
  deterministico dei test in base alle aree modificate e al rischio.

Le prossime azioni di definizione sono governate separatamente: rispondere o
deferire `PRQ-7070e7a631b1df44`, validare `A001` e `A002`, e decidere se le sei
lacune di evidenza facoltativa richiedano ulteriore coverage dichiarata.

## Risks, Assumptions And Open Questions

I rischi principali sono la confusione tra fonti canoniche e viste derivate, la
staleness dopo mutazioni, l'uso di euristiche come se fossero autorita, le
scritture multi-file parziali, il source drift tra preview e apply e
l'attribuzione implicita di approvazione ad artefatti generati. Le mitigazioni
sono provenance e freshness esplicite, transazioni atomiche con rollback,
preimage checks, policy di authority condivise, budget bounded e stage owner o
curator separati.

Restano quattro limiti operativi visibili:

- le 88 proposte non mappate sono storia valida, ma non coverage verticale
  dichiarata;
- le due divergenze draft/pending mantengono l'indice parziale per scelta, non
  per errore del parser;
- assessment, maturity e aggregazione software-spec usano ancora fallback
  legacy espliciti, anche quando il confronto dei contenuti e corrente;
- il fallback delle next action evidenzia `CHANGE-068` ma non il secondo Change
  Set attivo, `CHANGE-069`, mentre i gap di readiness sono correttamente
  prioritizzati.

Due assunzioni sono ancora `to_validate`: il progetto continua a disporre di un
filesystem locale scrivibile con Git come audit substrate, e un owner
responsabile resta disponibile per decisioni e curatela semantica. E invece
validata l'assunzione che registri e indici deterministici possano essere
ricostruiti dalle fonti governate.

Le decisioni owner aperte riguardano PROP-063, PROP-098, la domanda
`PRQ-7070e7a631b1df44`, le due assunzioni, l'eventuale chiusura governata di
`CHANGE-068` e `CHANGE-069` e la review finale della pubblicazione. Cache
persistente del decision context, database, migrazioni remote di flotte e
automazione delle fasi curator/owner restano alternative rinviate.

## Source Of Truth And Publication Status

`.p2p/` remains authoritative for project identity, proposals, decisions,
readiness, project questions, choices, Change Sets, Work, permissions, vertical
definition and governance state. `outputs/latest/project.md` is a deterministic
generated export. This curated document is a derived human-readable
publication draft.

La validazione del Markdown e il rendering PDF non costituiscono review. Lo
stato `approved_for_publication` deve restare falso finche l'owner non registra
esplicitamente un esito attraverso la primitiva dedicata.

## Traceability Notes

Il packet di curatela e `outputs/latest/curator-input.md`. Il source export
`outputs/latest/project.md` ha sha256
`cec40affb6b4a98b902f5a38c99b1c24e8d58b6cbd9a68a14956295ebd47fd9b`;
il fingerprint P2P del packet e
`fd764a2d4611014e45d9fa1079e8e766f3f2c36591209eedd2a7a586d878176f`.
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
PROP-086, PROP-089, PROP-096, PROP-101), decision context (PROP-100) e
pubblicazione umana (PROP-099).
