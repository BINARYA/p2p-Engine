# Inventario delle primitive CLI

## Scopo

Questa e' una fotografia descrittiva della CLI P2P Engine disponibile nel
checkout analizzato. Serve a capire quali primitive esistono e in quale ambito
operano. Non propone una futura organizzazione della CLI e non afferma che ogni
comando appartenga necessariamente al perimetro desiderato del prodotto.
Integra la
[`codebase-architecture-review.md`](codebase-architecture-review.md)
con il dettaglio della superficie CLI, senza duplicarne l'analisi dei moduli e
dei flussi interni.

Snapshot:

```text
commit: fbda301f293bfd0333f1ad9ccdf49d440400a048
tag: v0.4.5
data: 2026-07-23
comandi foglia: 241
gruppi Typer complessivi: 55
gruppi di primo livello: 30
comandi diretti sulla root: 6
```

L'inventario e' stato estratto dal registro Typer costruito da
[`cli.py`](../../src/p2p_engine/cli.py) e dai moduli in
[`cli_commands/`](../../src/p2p_engine/cli_commands/). Il comando
`p2p <percorso> --help` resta l'autorita per la firma completa e i default.

## Legenda

La colonna `Effetto` descrive l'effetto principale osservato:

| Codice | Significato |
| --- | --- |
| `R` | Lettura, diagnostica o validazione senza scrittura persistente. |
| `P` | Preview o candidato senza applicazione dello stato. |
| `C` | Scrittura dello stato persistente gestito dal progetto. |
| `D` | Generazione o aggiornamento di una vista, prompt, spec o export derivato. |
| `G` | Side effect Git, remoto o modifica di file di integrazione nel repository. |
| `O` | Operazione che richiede autorita o conferma esplicita dell'owner. |

I codici possono essere combinati. Per esempio, `C/O` indica una scrittura
governata owner-controlled, mentre `G/O` indica un side effect Git controllato
dall'owner.

Opzioni ricorrenti non ripetute in ogni riga:

- `--root PATH` seleziona la root del progetto;
- `--format text|json` e' disponibile su molte letture e mutazioni;
- `--preview-token` e `--confirm` legano le apply alla preview;
- `--actor`, `--approver` ed equivalenti distinguono autorita ed esecutore.

## Vista per ambito

| Ambito | Primitive | Funzione prevalente |
| --- | ---: | --- |
| Bootstrap, salute, runtime e schema | 17 | Avvio, diagnostica, compatibilita e migrazioni. |
| Progetto, verticale, readiness e pubblicazione | 60 | Stato logico del progetto e output umani. |
| Proposte, domande e analisi | 69 | Memoria delle direzioni candidate e loro raffinamento. |
| Decisioni, governance, choice e conflitti | 34 | Autorita, alternative, relazioni e audit. |
| Intake, registri e prossime azioni | 14 | Ingresso di nuove idee e viste operative. |
| Change, software spec e Work | 30 | Handoff implementativo e lifecycle Git attualmente presenti. |
| Collaborazione, consenso e agenti | 17 | Accesso, sincronizzazione e integrazioni locali. |
| **Totale** | **241** | |

## 1. Bootstrap, salute, runtime e schema

Sorgenti principali:
[`doctor.py`](../../src/p2p_engine/cli_commands/doctor.py),
[`project_status.py`](../../src/p2p_engine/cli_commands/project_status.py),
[`runtime.py`](../../src/p2p_engine/cli_commands/runtime.py) e
[`workspace_migrations.py`](../../src/p2p_engine/cli_commands/workspace_migrations.py).

### Comandi root

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p doctor` | `R` | Diagnostica CLI, workspace, Git e disponibilita MCP. |
| `p2p status` | `R` | Mostra un riepilogo di progetto e proposte. |
| `p2p context [--budget] [--target]` | `R` | Costruisce il context packet compatto per un agente. |
| `p2p check` | `R` | Controlla la struttura minima dello workspace. |
| `p2p validate` | `R` | Esegue validazione strutturale e semantica completa. |
| `p2p init NAME` | `C/G` | Inizializza workspace, profilo, owner, verticale e integrazioni richieste; `--vertical-pack` usa un artifact locale con checksum atteso. |

### Runtime contract

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p runtime status` | `R` | Confronta runtime installato e contratto dichiarato dal progetto. |
| `p2p runtime contract preview` | `P` | Prepara una modifica di `requires` e `recommended`. |
| `p2p runtime contract apply` | `C/O` | Applica una preview con state token e conferma. |
| `p2p runtime contract adopt` | `C/O` | Introduce il contratto in un progetto legacy non dichiarato. |

### Schema e migrazioni

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p workspace schema status` | `R` | Mostra versione schema, layout e allineamento. |
| `p2p workspace migrate plan` | `P` | Costruisce il piano deterministico verso `--to VERSION`. |
| `p2p workspace migrate attestation-template` | `R` | Stampa un template source-bound per attestazioni legacy. |
| `p2p workspace migrate apply` | `C/O` | Applica una migrazione con fingerprint, input owner e conferma. |
| `p2p workspace migrate recovery status` | `R` | Ispeziona una transazione di migrazione interrotta. |
| `p2p workspace migrate recovery rollback` | `C/O` | Ripristina lo stato precedente della transazione indicata. |
| `p2p workspace migrate recovery resume` | `C/O` | Riprende la transazione se le precondizioni sono ancora esatte. |

## 2. Progetto, verticale, readiness e pubblicazione

Sorgenti principali:
[`project_ops.py`](../../src/p2p_engine/cli_commands/project_ops.py),
[`project_readiness.py`](../../src/p2p_engine/cli_commands/project_readiness.py)
e [`project_status.py`](../../src/p2p_engine/cli_commands/project_status.py).

### Stato, proiezioni ed export

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p project refresh` | `D` | Ricostruisce le proiezioni di progetto dalle fonti accettate. |
| `p2p project status` | `R` | Mostra stato e disponibilita delle proiezioni razionalizzate. |
| `p2p project progress` | `R` | Separa progresso di definizione e copertura dichiarata. |
| `p2p project freshness` | `R` | Mostra dipendenze derivate e piano ordinato di rebuild. |
| `p2p project show SECTION` | `R` | Stampa una sezione generata dello stato progetto. |
| `p2p project export` | `D` | Esporta la definizione visibile in `outputs/latest/project.md`. |
| `p2p project export-status` | `R` | Controlla latest, export e revisioni visibili. |

### Contesto e sezioni

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p project context` | `R` | Restituisce il contesto del verticale in forma agent-ready. |
| `p2p project sections` | `R` | Elenca le sezioni del verticale attivo o richiesto. |
| `p2p project section SECTION-ID` | `R` | Mostra la definizione di una singola sezione. |

### Memoria verticale

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p project memory status` | `R` | Mostra materializzazione, fingerprint e freshness della memoria. |
| `p2p project memory show` | `R` | Legge aggregato o sezione esatta della memoria verticale. |

### Metadati e stile di interazione

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p project metadata show` | `R` | Mostra metadati limitati e hash delle configurazioni protette. |
| `p2p project metadata preview` | `P` | Valida una modifica bounded dei metadati. |
| `p2p project metadata apply` | `C/O` | Applica la modifica legata alla preview. |
| `p2p project interaction-style show` | `R` | Mostra lo stile owner-facing effettivo. |
| `p2p project interaction-style set` | `C/O` | Aggiorna verbosita, formalita o assertivita. |

### Profilo remoto

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p project remote show` | `R` | Mostra il profilo locale/remoto del progetto. |
| `p2p project remote configure` | `C` | Registra provider, remoto e repository senza creare risorse esterne. |

### Verticali

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p project vertical list` | `R` | Elenca vertical pack integrati, utente e project-local. |
| `p2p project vertical show VERTICAL` | `R` | Mostra manifest e contenuto del pack. |
| `p2p project vertical validate TARGET` | `R` | Valida ID, `vertical.yml` o directory multi-file. |
| `p2p project vertical schema` | `R` | Restituisce schema e limiti dei portable vertical pack v2. |
| `p2p project vertical scaffold TARGET` | `C` | Crea una directory autore v2 locale; non muta `.p2p`. |
| `p2p project vertical inspect TARGET` | `R` | Mostra vista dichiarata o effettiva di directory e archivi locali. |
| `p2p project vertical package TARGET` | `C` | Produce un archivio v2 deterministico fuori dallo stato progettuale. |
| `p2p project vertical install preview/apply` | `R/C` | Installa offline una coordinate esatta con checksum, token e conferma. |
| `p2p project vertical adopt preview/apply` | `R/C/O` | Adotta una coordinate esatta quando non esiste evidenza significativa. |
| `p2p project vertical migrate preview/apply` | `R/C/O` | Migra con mapping esatto e conservazione degli orfani. |
| `p2p project vertical propose IDEA` | `R` | Stampa un candidato YAML importabile senza persisterlo. |
| `p2p project vertical add PATH` | `C` | Copia un vertical pack nel progetto; `--activate` puo selezionarlo. |
| `p2p project vertical select VERTICAL` | `C/O` | Seleziona il verticale attivo e ne registra il lock. |
| `p2p project vertical lock show` | `R` | Mostra stato e drift del lock verticale. |
| `p2p project vertical lock repair` | `C/O` | Ricrea il lock dalla selezione attiva. |

### Rubriche e definizione

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p project rubrics init` | `C` | Crea o sostituisce le rubriche di maturita. |
| `p2p project rubrics show` | `R` | Mostra le rubriche configurate. |
| `p2p project definition show` | `R` | Mostra campi, assunzioni, domande e completamento persistenti. |
| `p2p project definition update PATCH` | `C` | Applica direttamente una patch strutturata supportata. |
| `p2p project definition preview PATCH` | `P` | Valida e tokenizza una candidate patch. |
| `p2p project definition apply PATCH` | `C/O` | Applica una preview owner-confirmed e anti-stale. |

### Readiness del progetto

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p project readiness review` | `R` | Riepiloga gap prioritari e sezioni del verticale. |
| `p2p project readiness gaps` | `R` | Elenca gap paginati legati a uno snapshot. |
| `p2p project readiness gap GAP-ID` | `R` | Mostra un singolo gap stabile. |
| `p2p project readiness preview` | `P` | Converte risposte selezionate in una candidate convergence patch. |
| `p2p project readiness apply` | `C/O` | Applica la convergenza legata al token. |

### Domande di readiness del progetto

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p project readiness questions status` | `R` | Elenca domande, gruppi, revisioni e stato. |
| `p2p project readiness questions next` | `R` | Mostra la prossima domanda applicabile. |
| `p2p project readiness questions answer QUESTION-ID` | `C/O` | Registra o sostituisce una risposta owner con revisione attesa. |
| `p2p project readiness questions defer QUESTION-ID` | `C/O` | Rinvia la domanda con ragione e revisione. |
| `p2p project readiness questions mute QUESTION-ID` | `C/O` | Esclude la domanda dal re-ask ordinario. |
| `p2p project readiness questions reopen QUESTION-ID` | `C/O` | Riapre una domanda precedentemente chiusa. |
| `p2p project readiness questions reconcile-preview` | `P` | Propone la riconciliazione dopo drift del verticale. |
| `p2p project readiness questions reconcile-apply` | `C/O` | Applica la riconciliazione token-bound. |

### Operational brief

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p project brief prompt` | `D` | Genera un prompt per il brief operativo. |
| `p2p project brief import SOURCE` | `C` | Importa un brief umano o prodotto da agente. |
| `p2p project brief show` | `R` | Stampa il brief operativo memorizzato. |

### Pubblicazione umana

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p project publish prepare` | `D` | Prepara packet, profilo, evidenze e candidati per lingua/edizione. |
| `p2p project publish import SOURCE` | `D` | Importa Markdown curato, modello ed evidence accounting. |
| `p2p project publish validate` | `D` | Valida il documento editoriale e registra l'esito. |
| `p2p project publish render` | `D` | Produce il PDF draft dalla versione validata. |
| `p2p project publish review` | `D/O` | Registra la review owner della specifica edizione. |
| `p2p project publish status` | `R` | Mostra freshness e stato degli stage dell'edizione. |
| `p2p project publish list` | `R` | Elenca le edizioni committed senza rebuild. |

### Assessment derivati

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p assess refresh` | `D` | Genera l'assessment deterministico corrente. |
| `p2p assess show` | `R` | Mostra l'assessment memorizzato. |
| `p2p assess maturity refresh` | `D` | Ricalcola la maturita dalle rubriche abilitate. |
| `p2p assess maturity show` | `R` | Mostra la maturita memorizzata. |

## 3. Proposte, domande e analisi

Sorgenti principali: moduli `proposal_*` in
[`cli_commands/`](../../src/p2p_engine/cli_commands/) e
[`prompts.py`](../../src/p2p_engine/cli_commands/prompts.py).

### Proposta di base

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p proposal create TITLE` | `C` | Crea scaffold e sezioni strutturate iniziali. |
| `p2p proposal update PROP-ID` | `C` | Aggiorna problema, contesto, obiettivi, proposta e acceptance. |
| `p2p proposal list` | `R` | Elenca proposte, anche filtrate per stato. |
| `p2p proposal show PROP-ID` | `R` | Mostra sintesi compatta o contenuto completo. |
| `p2p proposal contributions PROP-ID` | `R` | Alias di lettura delle contribution della proposta. |

### Decisioni rapide sulla proposta

Questi comandi usano lo stesso servizio preview/apply del gruppo `decision`.

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p proposal accept PROP-ID` | `P` o `C/O` | Preview o apply dell'accettazione, con override readiness esplicito. |
| `p2p proposal reject PROP-ID` | `P` o `C/O` | Preview o apply del rigetto iniziale. |
| `p2p proposal defer PROP-ID` | `P` o `C/O` | Preview o apply del rinvio. |

### Readiness della proposta

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p proposal readiness show PROP-ID` | `R` | Mostra score, gate e snapshot esistente. |
| `p2p proposal readiness refresh PROP-ID` | `D` | Aggiorna lo snapshot dai dati correnti. |
| `p2p proposal readiness init PROP-ID` | `D` | Inizializza readiness e catalogo minimo. |
| `p2p proposal readiness assess PROP-ID` | `D` | Ricalcola readiness da artefatti e domande. |
| `p2p proposal readiness explain PROP-ID` | `R` | Spiega gap e prossime azioni. |
| `p2p proposal readiness review PROP-ID` | `R` | Produce guida proattiva per la revisione. |

### Domande della proposta

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p proposal questions init PROP-ID` | `C` | Inizializza lo stato persistente delle domande. |
| `p2p proposal questions status PROP-ID` | `R` | Mostra riepilogo e revisioni. |
| `p2p proposal questions list PROP-ID` | `R` | Elenca tutte le domande. |
| `p2p proposal questions add PROP-ID` | `C` | Aggiunge domanda, gap, priorita e gruppo. |
| `p2p proposal questions answer PROP-ID QUESTION-ID ANSWER` | `C/O` | Registra una risposta, opzionalmente sostitutiva. |
| `p2p proposal questions defer PROP-ID QUESTION-ID` | `C/O` | Rinvia una domanda con motivazione. |
| `p2p proposal questions mute PROP-ID QUESTION-ID` | `C/O` | Disabilita il re-ask ordinario. |
| `p2p proposal questions reopen PROP-ID QUESTION-ID` | `C/O` | Riapre una domanda. |
| `p2p proposal questions retire PROP-ID QUESTION-ID` | `C/O` | Ritira una domanda non piu utile. |
| `p2p proposal questions supersede PROP-ID QUESTION-ID REPLACEMENT` | `C/O` | Collega una domanda sostitutiva. |
| `p2p proposal questions group-status PROP-ID GROUP-ID` | `C/O` | Modifica lo stato di re-ask del gruppo. |
| `p2p proposal questions next PROP-ID` | `R` | Mostra la prossima domanda eleggibile. |
| `p2p proposal questions reassess PROP-ID` | `D` | Ricalcola trigger e stato dalle evidenze. |
| `p2p proposal questions apply PROP-ID` | `C/O` | Marca risposte come applicate e stampa il riepilogo. |
| `p2p proposal questions import PROP-ID SOURCE` | `C` | Importa uno stato domanda supportato. |

### Stato degli artefatti della proposta

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p proposal artifact status PROP-ID` | `R` | Mostra copertura logica, materiale e provenienza. |
| `p2p proposal artifact init PROP-ID` | `C` | Inizializza o riallinea il catalogo. |
| `p2p proposal artifact set PROP-ID ARTIFACT` | `C` | Imposta stato, ragione ed evidenza di un artefatto. |
| `p2p proposal artifact confirm PROP-ID ARTIFACT` | `C/O` | Registra conferma owner. |
| `p2p proposal artifact mark-legacy PROP-ID ARTIFACT` | `C/O` | Registra un'assenza legacy dichiarata. |

### Contribution

I due percorsi sono superfici compatibili sullo stesso concetto.

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p contribution add PROP-ID TEXT` | `C` | Aggiunge una contribution tipizzata. |
| `p2p contribution list PROP-ID` | `R` | Elenca le contribution. |
| `p2p proposal contribution add PROP-ID TEXT` | `C` | Percorso annidato equivalente per aggiunta. |
| `p2p proposal contribution list PROP-ID` | `R` | Percorso annidato equivalente per lettura. |

### Copertura del verticale

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p proposal vertical-coverage show PROP-ID` | `R` | Mostra mapping dichiarati e diagnostica. |
| `p2p proposal vertical-coverage suggest PROP-ID` | `R` | Suggerisce mapping senza renderli autoritativi. |
| `p2p proposal vertical-coverage preview PROP-ID SOURCE` | `P` | Valida sostituzione di coverage e artifact state. |
| `p2p proposal vertical-coverage import PROP-ID SOURCE` | `C/O` | Importa atomicamente coverage e provenienza. |

### Analisi e prompt/import

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p explore prompt PROP-ID` | `D` | Genera il prompt di esplorazione. |
| `p2p explore import PROP-ID SOURCE` | `C` | Importa finding, alternative, rischi e altri artefatti. |
| `p2p explore status PROP-ID` | `R` | Mostra stato degli artefatti di esplorazione. |
| `p2p digest prompt PROP-ID` | `D` | Genera il prompt di digest. |
| `p2p clarify prompt PROP-ID` | `D` | Genera il prompt di chiarimento. |
| `p2p clarify import PROP-ID SOURCE` | `C` | Importa il risultato in `clarifications.md`. |
| `p2p synthesize prompt PROP-ID` | `D` | Genera il prompt di sintesi della proposta. |
| `p2p synthesize import PROP-ID SOURCE` | `C` | Importa la proposta sintetizzata. |
| `p2p plan prompt PROP-ID` | `D` | Genera il prompt del piano di esecuzione. |
| `p2p plan import PROP-ID SOURCE` | `C` | Importa `execution-plan.md`. |
| `p2p tasks prompt PROP-ID` | `D` | Genera il prompt per le task. |
| `p2p tasks import PROP-ID SOURCE` | `C` | Importa `tasks.yml`. |

### Impact

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p impact prompt PROP-ID` | `D` | Genera il prompt di impact analysis. |
| `p2p impact import PROP-ID SOURCE` | `C` | Importa impact map, relazioni e conflict analysis. |
| `p2p impact preview PROP-ID SOURCE` | `P` | Prepara una correzione completa senza scrivere. |
| `p2p impact apply PROP-ID SOURCE` | `C/O` | Applica la correzione con token anti-stale. |

### Lifecycle Git delle branch proposta

Queste primitive operano sul repository Git e sono separate dal lifecycle
decisionale `proposal accept/reject/defer`.

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p proposal branch PROP-ID` | `G` | Crea e seleziona una branch proposta gestita. |
| `p2p proposal status PROP-ID` | `R` | Mostra stato della branch proposta. |
| `p2p proposal publish PROP-ID` | `G` | Pubblica la branch sul remoto. |
| `p2p proposal request-review PROP-ID` | `C/G` | Registra l'handoff di review esterna. |
| `p2p proposal merge PROP-ID` | `G/O` | Esegue merge locale, continue o abort. |
| `p2p proposal accept-branch PROP-ID` | `G/O` | Registra accettazione della branch nel lifecycle Git. |
| `p2p proposal reject-branch PROP-ID` | `G/O` | Registra rigetto della branch nel lifecycle Git. |
| `p2p proposal finalize PROP-ID` | `G/O` | Pubblica la base branch dopo il merge. |
| `p2p proposal cleanup PROP-ID` | `G/O` | Elimina branch locale ed eventualmente remota. |
| `p2p proposal retire-branch PROP-ID` | `G/O` | Ritira la branch senza merge. |
| `p2p proposal scan` | `R` | Scansiona branch gestite senza checkout. |

## 4. Decisioni, governance, choice e conflitti

### Ledger decisionale delle proposte

Sorgente:
[`proposal_decisions.py`](../../src/p2p_engine/cli_commands/proposal_decisions.py).

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p decision status PROP-ID` | `R` | Mostra autorita effettiva e stato del ledger. |
| `p2p decision history PROP-ID` | `R` | Legge eventi con `--limit` e `--cursor`. |
| `p2p decision impact PROP-ID` | `R` | Calcola dipendenze per uno specifico event type. |
| `p2p decision preview PROP-ID` | `P` | Prepara evento, condizioni, lineage e impatto. |
| `p2p decision apply PROP-ID` | `C/O` | Appende l'evento usando gli stessi input e il preview token. |
| `p2p decision record PROP-ID` | `P` o `C/O` | Comando compatibile per outcome accept/reject/defer. |
| `p2p decision projection-repair-preview PROP-ID` | `P` | Prepara riallineamento delle proiezioni leggibili. |
| `p2p decision projection-repair-apply PROP-ID` | `C/O` | Applica la riparazione delle proiezioni. |
| `p2p decision ledger-repair-preview PROP-ID` | `P` | Valida un ledger candidato esterno. |
| `p2p decision ledger-repair-apply PROP-ID` | `C/O` | Sostituisce il ledger con il candidato approvato. |
| `p2p decision legacy-resolution-preview PROP-ID` | `P` | Prepara la risoluzione di autorita legacy. |
| `p2p decision legacy-resolution-apply PROP-ID` | `C/O` | Registra l'evento risolutivo token-bound. |

### Governance, SWOT, voti e precedenti

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p governance init` | `C/O` | Inizializza policy, ruoli e artefatti di governance. |
| `p2p governance status` | `R` | Mostra modalita e artefatti di audit. |
| `p2p governance validate` | `R` | Valida la governance senza mutazioni. |
| `p2p swot prompt PROP-ID` | `D` | Genera il prompt SWOT di governance. |
| `p2p vote record PROP-ID` | `C/O` | Registra scelta, ragione, voter e ruolo. |
| `p2p vote status PROP-ID` | `R` | Mostra conteggi e voti. |
| `p2p precedent record PROP-ID` | `C/O` | Registra un precedente riutilizzabile. |
| `p2p precedent search` | `R` | Cerca match deterministici per ID o tag. |

### Choice

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p choice create TITLE` | `C` | Crea una scelta con opzioni esplicite. |
| `p2p choice list` | `R` | Elenca le choice di progetto. |
| `p2p choice status` | `R` | Unifica choice di progetto e candidate locali alle proposte. |
| `p2p choice show CHOICE-ID` | `R` | Mostra opzioni, stato, blocker e decisione. |
| `p2p choice discover` | `R` | Produce finding consultivi senza mutazioni. |
| `p2p choice governance-preflight CHOICE-ID` | `P` | Valuta blocker, voti e precedenti senza decidere. |
| `p2p choice block CHOICE-ID` | `C/O` | Registra un blocker attivo. |
| `p2p choice unblock CHOICE-ID` | `C/O` | Disattiva un blocker. |
| `p2p choice decide CHOICE-ID` | `C/O` | Registra l'opzione selezionata e la motivazione. |

### Memoria dei conflitti

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p conflict record SOURCE TARGET` | `C` | Registra una relazione di conflitto nel progetto. |
| `p2p conflict status` | `R` | Elenca i conflitti registrati. |
| `p2p conflict show CONFLICT-ID` | `R` | Mostra un record stabile. |
| `p2p conflict preview-update CONFLICT-ID` | `P` | Prepara l'aggiornamento di un conflitto esistente. |
| `p2p conflict update CONFLICT-ID` | `C/O` | Applica l'aggiornamento legato alla preview. |

## 5. Intake, registri e prossime azioni

### Registri derivati

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p registry refresh` | `D` | Rigenera registri tipizzati e manifest. |
| `p2p registry status` | `R` | Controlla disponibilita e freshness di base. |
| `p2p registry show REGISTRY` | `R` | Stampa un registro generato. |

### Intake

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p intake prompt IDEA` | `D` | Genera un prompt usando memoria e registri. |
| `p2p intake import INTAKE-ID SOURCE` | `C` | Importa l'analisi prodotta da umano o agente. |
| `p2p intake status` | `R` | Elenca intake e stato di analisi. |
| `p2p intake apply plan INTAKE-ID` | `C` | Crea un piano controllato di azioni supportate. |
| `p2p intake apply show INTAKE-ID` | `R` | Mostra il piano corrente. |
| `p2p intake apply run INTAKE-ID ACTION-ID` | `C/O` | Esegue una sola azione esplicita del piano. |

### Next action

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p next list` | `R` | Unisce azioni curate e generate, opzionalmente limitate da `--top`. |
| `p2p next add KIND TARGET` | `C` | Aggiunge un'azione curata. |
| `p2p next complete ACTION-ID` | `C` | Sposta l'azione curata nell'audit come completata. |
| `p2p next retire ACTION-ID` | `C` | Sposta l'azione nell'audit come ritirata. |
| `p2p next refresh` | `C/D` | Normalizza le azioni curate e rigenera il conteggio operativo. |

## 6. Change, software spec e Work

Questa area rappresenta il sottosistema oggi rivolto a handoff implementativo,
stati operativi e gestione Git. L'inventario ne documenta la presenza senza
stabilire che debba restare nel perimetro futuro del prodotto.

### Change Set

Sorgente:
[`changes.py`](../../src/p2p_engine/cli_commands/changes.py).

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p change create --from PROP-ID` | `C` | Crea metadata operativi da intent accettato. |
| `p2p change status` | `R` | Elenca Change Set e lifecycle. |
| `p2p change policy CHANGE-ID` | `R` | Mostra policy Git associata. |
| `p2p change show CHANGE-ID` | `R` | Mostra summary, target, piano e riferimenti. |
| `p2p change set-status CHANGE-ID STATUS` | `C` | Aggiorna lo stato del lifecycle implementativo. |
| `p2p change tasks CHANGE-ID` | `R` | Mostra task e azioni associate. |

### Software spec ed export

Sorgente:
[`specs.py`](../../src/p2p_engine/cli_commands/specs.py).

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p spec lifecycle` | `R` | Mostra route e preflight per spec o downstream export. |
| `p2p spec refresh --change CHANGE-ID` | `D` | Genera la software spec deterministica. |
| `p2p spec status` | `R` | Elenca spec e freshness. |
| `p2p spec show CHANGE-ID` | `R` | Stampa l'indice della spec. |
| `p2p spec prompt --change CHANGE-ID` | `D` | Genera il prompt di raffinamento. |
| `p2p spec import CHANGE-ID SOURCE` | `D` | Importa un bundle raffinato validato. |
| `p2p spec export --change CHANGE-ID --target TARGET` | `D` | Esporta bundle generic, OpenSpec o Spec Kit. |
| `p2p spec export-status` | `R` | Elenca export generati. |
| `p2p spec export-show CHANGE-ID --target TARGET` | `R` | Stampa il documento principale dell'export. |
| `p2p spec export-validate CHANGE-ID --target TARGET` | `R` | Valida struttura e file dell'export esistente. |

### Work e Git lifecycle

Sorgente:
[`work.py`](../../src/p2p_engine/cli_commands/work.py).

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p work plan --change CHANGE-ID --target TARGET` | `C` | Crea un manifest di handoff senza branch o commit. |
| `p2p work list` | `R` | Elenca i manifest. |
| `p2p work status` | `R` | Mostra riepilogo operativo e prossima azione. |
| `p2p work scan` | `R` | Scansiona branch Work locali senza checkout. |
| `p2p work branch WORK-ID` | `G` | Crea e seleziona la branch implementativa. |
| `p2p work retire WORK-ID` | `C/O` | Ritira un manifest pianificato senza toccare branch. |
| `p2p work submit WORK-ID` | `G` | Crea un commit locale delle modifiche. |
| `p2p work review WORK-ID` | `C/O` | Registra richiesta di review locale. |
| `p2p work publish WORK-ID` | `G` | Pubblica la branch sul remoto. |
| `p2p work request-review WORK-ID` | `C/G` | Registra handoff di review provider-agnostic. |
| `p2p work accept WORK-ID` | `G/O` | Esegue merge locale, continue o abort. |
| `p2p work finalize WORK-ID` | `G/O` | Pubblica la base branch accettata. |
| `p2p work cleanup WORK-ID` | `G/O` | Elimina branch finalizzate locali e remote. |
| `p2p work show WORK-ID` | `R` | Stampa il manifest completo. |

## 7. Collaborazione, consenso e agenti

### Sincronizzazione Git

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p sync status` | `R` | Mostra branch, remoto, ahead/behind e condizioni di sync. |
| `p2p sync fetch` | `G` | Esegue fetch dopo validazione del profilo. |
| `p2p sync pull` | `G` | Esegue soltanto fast-forward pull validato. |
| `p2p sync push` | `G` | Pubblica la branch corrente dopo preflight. |

### Identita e permessi dichiarati

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p permissions show` | `R` | Mostra identita, ruoli e policy dichiarate. |
| `p2p permissions actor add ACTOR-ID` | `C/O` | Aggiunge o aggiorna actor, ruolo, tipo e display name. |

### Consent receipt

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p consent grant OPERATION TARGET` | `C/O` | Crea consenso bounded, opzionalmente single-use e con scadenza. |
| `p2p consent show CONSENT-ID` | `R` | Mostra receipt, scope e stato di consumo. |
| `p2p consent status` | `R` | Elenca i receipt. |
| `p2p consent revoke CONSENT-ID` | `C/O` | Revoca un receipt non consumato. |

### Integrazioni agente

| Comando | Effetto | Utilita |
| --- | --- | --- |
| `p2p agent doctor TARGET` | `R` | Diagnostica runtime e recovery dell'adapter. |
| `p2p agent list` | `R` | Elenca adapter supportati e installati. |
| `p2p agent show ADAPTER` | `R` | Mostra file gestiti e stato dell'integrazione. |
| `p2p agent install TARGET` | `G` | Installa file e aggiorna il registro integrazioni. |
| `p2p agent update TARGET` | `G` | Aggiorna file generati quando non drifted. |
| `p2p agent uninstall ADAPTER` | `G/O` | Rimuove un adapter gestito e non condiviso. |
| `p2p agent instructions refresh` | `G` | Rigenera istruzioni agent-safe per i profili selezionati. |

## Alias, compatibilita e sovrapposizioni osservate

- `p2p contribution add/list` e `p2p proposal contribution add/list` espongono
  lo stesso concetto con due percorsi.
- `p2p proposal contributions` e' un ulteriore comando di sola lettura.
- `p2p proposal accept/reject/defer` sono shortcut del servizio decisionale
  preview/apply.
- `p2p decision record` conserva una superficie compatibile per gli outcome
  storici.
- lifecycle della decisione e lifecycle Git della branch proposta sono
  separati: `proposal accept` non equivale ad `proposal accept-branch`.
- readiness di proposta, readiness di progetto, assessment e maturity sono
  quattro viste differenti.
- `project refresh`, `registry refresh`, `assess refresh`, `spec refresh` e
  `next refresh` aggiornano viste differenti e non sono sinonimi.
- `project export` produce una definizione visibile; `project publish` gestisce
  invece edizioni editoriali con evidenze, validazione e review.

## Boundary pratici

### Primitive di memoria progettuale

Il nucleo piu direttamente rivolto alla memoria logica comprende:

- proposal, contribution e question state;
- decision, choice, governance, impact e conflict;
- project vertical, definition, readiness e memory;
- context, intake, registries e publication.

### Primitive derivate

Prompt, registri, assessment, memoria verticale, proiezioni, spec ed export
possono essere ricostruiti o rigenerati secondo i rispettivi contratti. Una
scrittura `D` non va quindi interpretata automaticamente come nuova autorita
progettuale.

### Primitive con effetti esterni al modello logico

I gruppi `work`, `sync`, le branch proposta e parte di `agent` modificano Git,
remoti o file del repository. I gruppi `change` e `spec` collegano inoltre la
memoria accettata a un handoff implementativo. Questa separazione e' rilevante
quando si vuole usare P2P soltanto come memoria e definizione logica.

## Come verificare una primitiva

Per controllare firma, default ed help effettivi:

```bash
p2p --help
p2p project --help
p2p project readiness --help
p2p project readiness questions --help
p2p proposal --help
p2p decision apply --help
```

Per i comandi che supportano output strutturato, preferire `--format json`
quando il risultato deve essere consumato da un agente o da automazione. Prima
di una scrittura usare la corrispondente preview quando disponibile e
controllare runtime e schema con:

```bash
p2p runtime status
p2p workspace schema status
```
