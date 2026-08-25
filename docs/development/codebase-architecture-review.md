# Fotografia dell'architettura attuale della codebase

## Scopo del documento

Questo documento descrive come P2P Engine e' costruito nel repository al momento
dell'analisi. Il suo scopo e' ridurre l'incertezza sulla codebase, non definire
l'architettura futura del prodotto.

> Nota 0.4.6: questa fotografia resta intenzionalmente riferita alla 0.4.1.
> La baseline corrente ha rimosso analyzer, registry, handler e CLI delle
> workspace migration; supporta solo workspace schema 4 e vertical-pack schema
> 2. Il journal atomico corrente e' separato sotto
> `.p2p/.internal/workspace-transactions/`. Per i contratti operativi correnti
> vedere [`WORKSPACE-SCHEMA.md`](../WORKSPACE-SCHEMA.md) e
> [`CLI-GUIDE.md`](../CLI-GUIDE.md).

La fotografia distingue quattro categorie:

- **osservato**: comportamento o struttura verificati direttamente nel codice,
  nei test o nella configurazione del repository;
- **misurato**: dato ottenuto da un'analisi statica locale della revisione
  indicata sotto;
- **interpretazione**: spiegazione ragionevole sostenuta da piu evidenze, ma non
  formalizzata come contratto dal codice;
- **da verificare**: relazione o intenzione che il repository non rende
  sufficientemente esplicita.

Il documento non introduce policy architetturali, quality budget, registri del
debito, baseline da aggiornare, gate CI o nuovi formati interni. Non prescrive un
refactoring e non assegna automaticamente priorita agli elementi osservati.

## Perimetro e snapshot

La fotografia e' stata costruita sul commit:

```text
c4735cee23442fab1ff614cbc111a16da6050ed4
data commit: 2026-07-21T22:42:42+02:00
data analisi: 2026-07-22
package: p2p-engine 0.4.1
Python dichiarato: >=3.11
```

Sono inclusi nell'analisi:

- `src/` come codice applicativo e risorse distribuite;
- `tests/` come evidenza dei contratti verificati;
- `scripts/` come supporto allo sviluppo, ai test e alle misure;
- `pyproject.toml`, packaging e workflow di release;
- `.p2p/` esclusivamente come area dati gestita con cui il software interagisce.

Sono esclusi dalle metriche sul codice runtime `.p2p/`, `outputs/`, `drafts/`,
ambienti virtuali, build, cache e artefatti generati. I conteggi sono una
fotografia, non un vincolo da mantenere. Sono stati ottenuti con ispezione
statica dei file Python e con la raccolta dei test tramite gli script ufficiali
del repository; non e' stato aggiunto alcun analizzatore permanente.

## Quadro generale

**Osservato.** P2P Engine e' un'applicazione Python locale, file-backed e
Git-aware. Espone due interfacce eseguibili:

- una CLI Typer/Rich registrata come `p2p`;
- un server MCP JSON-RPC su standard input/output registrato come
  `p2p-mcp-server`.

Entrambe convergono su `P2PWorkspace`, che costruisce e collega i servizi
applicativi. I servizi operano su modelli e policy in `core`, usano primitive
condivise in `foundation` e leggono o modificano soprattutto lo workspace
gestito `.p2p/`. Git e' invocato come processo esterno da un adapter dedicato.

La forma effettiva del sistema puo essere riassunta cosi:

```text
CLI Typer/Rich                 MCP JSON-RPC stdio
      |                               |
      +---------- adapter -----------+
                      |
                P2PWorkspace
          composizione + facade pubblica
                      |
        servizi applicativi e di dominio
          |           |             |
        core      foundation    adapter Git
          |           |             |
          +---- filesystem ----------+
                      |
          .p2p/ e output derivati
```

**Interpretazione.** L'architettura non segue un framework esplicito o una
separazione formale in layer. Presenta pero una separazione riconoscibile tra
modelli/policy, orchestrazione, interfacce e side effect. Il punto di
composizione principale e' collocato nel package `storage`, quindi il nome del
package non rappresenta pienamente il ruolo reale di quel modulo.

## Albero ragionato dei package

| Area | Dimensione misurata | Responsabilita osservata |
| --- | ---: | --- |
| `src/p2p_engine/core/` | 28 file, 5.299 righe | Dataclass, enum, identita, eventi e policy pure per proposte, decisioni, verticali, readiness, publication, workspace e preview di mutazione. |
| `src/p2p_engine/foundation/` | 5 file, 328 righe | Caricamento YAML, helper Markdown, validazione e scritture atomiche di singoli file. |
| `src/p2p_engine/services/` | 79 file, 54.054 righe | Orchestrazione applicativa, lifecycle, indici derivati, migrazioni, validazione e gran parte dell'accesso ai file. |
| `src/p2p_engine/storage/` | 3 file, 3.730 righe | Facade/composition root `P2PWorkspace`, adapter Git e compatibility surface MCP storica. |
| `src/p2p_engine/cli_commands/` | 30 file, 6.616 righe | Registrazione dei comandi Typer, parsing degli argomenti e rendering Rich/JSON. |
| `src/p2p_engine/mcp/` | 27 file, 4.602 righe | Catalogo JSON Schema, registro dei tool, dispatcher, handler e server JSON-RPC stdio. |
| `src/p2p_engine/prompts/` | 10 file, 357 righe | Renderer di prompt testuali per intake, analisi e sintesi. |
| `src/p2p_engine/exporters/` | 3 file, 35 righe | Piccoli exporter Markdown/OpenSpec con accesso diretto al filesystem. |
| `src/p2p_engine/resources/` | risorse package | Vertical pack integrati e template distribuiti con wheel e sdist. |

Il package `services` contiene circa il 72% delle righe runtime misurate. Questo
non dimostra da solo un problema, ma identifica il luogo in cui si concentra la
maggior parte del comportamento da comprendere.

### Core

**Osservato.** `core` non importa `services`, `storage`, `cli_commands` o `mcp`
e non contiene accessi diretti ai file. Fornisce il vocabolario interno usato
dagli altri package. Tra i contratti piu trasversali vi sono:

- eventi e autorita delle decisioni sulle proposte;
- identita e stati di proposal, choice, Change Set e Work;
- schema dello workspace e compatibilita delle operazioni;
- readiness di proposta e progetto;
- verticali, sezioni, memoria verticale e publication;
- preview token e precondizioni per le mutazioni.

Questa e' la parte piu vicina a un dominio indipendente dagli adapter, anche se
il repository non la dichiara formalmente come layer.

### Foundation

**Osservato.** `foundation` raccoglie primitive usate trasversalmente. In
particolare, [`files.py`](../../src/p2p_engine/foundation/files.py#L87) realizza
la sostituzione atomica di un singolo file con file temporaneo nella stessa
directory, `fsync` e `replace`; `yaml_loaders.py` centralizza il caricamento
YAML e permette di forzare il loader Python tramite ambiente.

### Services

**Osservato.** I servizi non sono soltanto logica di dominio: includono anche
lettura e scrittura di file, costruzione di indici, validazione, rendering,
coordinamento di transazioni e chiamate all'adapter Git. Le aree funzionali piu
ampie sono:

- lifecycle di proposte, decisioni, readiness, domande e artefatti;
- definizione del progetto, verticali, memoria, progresso e convergenza;
- runtime contract, schema workspace e migrazioni;
- registri, freshness, context packet e decision-context retrieval;
- Change Set, Work, software spec e relativi export;
- publication editoriale, validazione, render e review;
- collaborazione Git, consenso, permessi e agent integration.

La dipendenza tra servizi e' costruita in prevalenza passando callback e
provider ai costruttori. Questo consente sostituzioni nei test, ma rende il
grafo delle dipendenze meno visibile rispetto a import e tipi espliciti.

### Storage e facade

**Osservato.** [`P2PWorkspace`](../../src/p2p_engine/storage/filesystem.py#L279)
e' il composition root e la facade effettiva del sistema. Il costruttore fissa
la root, individua `.p2p/` e inizializza in modo lazy numerosi servizi. I metodi
pubblici delegano in larga parte ai servizi, applicando anche controlli comuni
di runtime, schema e lock di migrazione.

La classe misura 3.255 righe, espone 251 metodi non privati e importa 81 moduli
interni. La maggioranza dei metodi e' breve e non ramificata: la dimensione
riflette soprattutto l'ampiezza della facade, non un unico algoritmo
monolitico. Restano nella classe anche alcuni default e alcune operazioni
dirette, per cui non e' una facade puramente meccanica.

[`storage/git.py`](../../src/p2p_engine/storage/git.py#L174) concentra le
invocazioni a `git` tramite `subprocess.run`. Non sono emerse altre chiamate a
processi esterni nel codice runtime.

### CLI

**Osservato.** [`cli.py`](../../src/p2p_engine/cli.py#L28) crea l'app Typer,
definisce i gruppi principali e demanda la registrazione ai moduli
`cli_commands`. [`cli_shared.workspace`](../../src/p2p_engine/cli_shared.py#L20)
costruisce un nuovo `P2PWorkspace` a partire dalla root richiesta.

L'introspezione locale della struttura Typer ha rilevato:

- 55 gruppi di comando complessivi;
- 241 comandi foglia;
- 30 gruppi di primo livello, tra cui `proposal`, `decision`, `project`,
  `workspace`, `spec`, `work`, `change`, `sync`, `agent` e `runtime`;
- 6 comandi registrati direttamente sulla root: `doctor`, `status`, `context`,
  `check`, `validate` e `init`.

Il file piu concentrato della superficie CLI e'
[`project_ops.py`](../../src/p2p_engine/cli_commands/project_ops.py#L16): la
funzione di registrazione include molti comandi annidati nello stesso scope.

### MCP

**Osservato.** [`mcp/server.py`](../../src/p2p_engine/mcp/server.py#L15)
implementa un loop JSON-RPC 2.0 su stdio e gestisce `initialize`, `tools/list` e
`tools/call`. Il catalogo separa le definizioni JSON Schema dagli handler. Il
registro ordinato in [`mcp/registry.py`](../../src/p2p_engine/mcp/registry.py#L14)
verifica duplicati e disallineamenti tra nomi e definizioni.

La revisione contiene 174 tool MCP, con corrispondenza esatta tra nomi
registrati e definizioni. Gli handler costruiscono `P2PWorkspace` e riusano gli
stessi servizi della CLI; MCP non costituisce quindi una seconda
implementazione del dominio.

### Risorse distribuite

**Osservato.** Il package include quattro vertical pack canonici multi-file:

- `base_project`;
- `software_project`;
- `packaging_or_physical_product_design`;
- `social_impact_program_design`.

Il loader dei verticali considera, in ordine controllato, pack di progetto,
directory configurate con `P2P_HOME`, directory utente e risorse integrate nel
package. Manifest, definizione, rubriche e sezioni sono dati dichiarativi, non
codice Python.

## Entry point e contratti pubblici

Gli entry point di packaging sono dichiarati in
[`pyproject.toml`](../../pyproject.toml#L30):

```text
p2p            -> p2p_engine.cli:app
p2p-mcp-server -> p2p_engine.mcp.server:main
```

`python -m p2p_engine` richiama la stessa app Typer. Il package root esporta
soltanto la versione, mentre la superficie Python effettivamente riusata dagli
adapter e' `P2PWorkspace`.

**Interpretazione.** I contratti pubblici reali sono distribuiti su quattro
livelli:

1. comandi, opzioni, exit code e output CLI;
2. nomi, schema e payload dei tool MCP;
3. metodi della facade `P2PWorkspace` usati internamente e nei test;
4. layout e semantica dei file gestiti nello workspace.

Il quarto livello e' persistente e quindi particolarmente delicato, anche se
non e' un'API Python. I test di packaging e migrazione ne coprono parti
significative.

## Flussi principali di esecuzione

### 1. Comando CLI

```text
shell
  -> entry point p2p
  -> Typer app e comando registrato
  -> parsing opzioni / root
  -> P2PWorkspace
  -> servizio applicativo
  -> modello core + filesystem o Git
  -> rendering Rich, testo o JSON
```

La CLI contiene soprattutto adattamento e presentazione, ma alcune funzioni di
registrazione sono abbastanza ampie da includere coordinamento e costruzione
dei payload oltre al rendering.

### 2. Chiamata MCP

```text
client MCP
  -> JSON-RPC su stdio
  -> registro e schema del tool
  -> handler per area
  -> P2PWorkspace
  -> stesso servizio usato dalla CLI
  -> payload JSON serializzabile
```

La separazione catalogo/handler permette di validare la superficie dichiarata,
ma le funzioni che elencano schema o instradano intere aree sono alcuni degli
hotspot dimensionali del codice MCP.

### 3. Lettura coerente

[`P2PWorkspace.read_consistently`](../../src/p2p_engine/storage/filesystem.py#L1734)
crea un [`WorkspaceReadContext`](../../src/p2p_engine/services/workspace_reads.py#L237).
Il contesto:

- cattura una sola volta contenuto, hash e metadati dei file letti;
- riusa parsing YAML, discovery e risultati di provider nella singola richiesta;
- osserva il lock di migrazione;
- al termine controlla se file o directory osservati sono cambiati;
- ripete una volta la lettura oppure segnala una modifica concorrente.

Questa cache e' deliberatamente request-scoped: non sopravvive alla chiamata
pubblica e non introduce stato condiviso tra processi.

### 4. Scrittura governata

Il percorso comune di una scrittura e':

```text
comando o tool autorizzato
  -> controllo runtime contract
  -> controllo schema compatibile con l'operazione
  -> controllo lock/recovery di migrazione
  -> preview e precondizioni, quando previste
  -> validazione del candidato
  -> commit su file
  -> eventuale aggiornamento derivato post-commit
```

Le operazioni sconosciute falliscono in modo chiuso rispetto alla matrice di
compatibilita dello schema. Le scritture piu sensibili usano
[`AtomicMutationWriter`](../../src/p2p_engine/services/workspace_transactions.py#L270),
che gestisce lock esclusivo, precondizioni delle fonti, staging, journal,
sostituzioni ordinate e recovery.

Tredici moduli di `services` definiscono o richiamano esplicitamente questa
transazione multi-file; i consumer coprono, tra l'altro, decisioni sulle
proposte, registri, memoria verticale, project state, software spec e runtime
contract. Altri servizi usano la scrittura atomica di singolo file o procedure
specifiche. La publication, che scrive anche fuori da `.p2p`, ha un lock e un
rollback propri.

### 5. Costruzione del contesto decisionale

[`ProjectDecisionContextService`](../../src/p2p_engine/services/decision_context.py#L33)
costruisce su richiesta un indice in memoria:

1. cataloga le fonti applicabili;
2. estrae decisioni, evidenze e relazioni;
3. normalizza topologia e identita;
4. deduplica e ordina record e diagnostica;
5. costruisce adiacenze e posting per il retrieval;
6. calcola un fingerprint semantico;
7. restituisce risultati bounded e spiegabili.

L'indice non e' una cache persistente. Nei context packet piccoli viene evitata
la costruzione globale; per un target specifico viene usato il retrieval vicino
alla proposta richiesta.

### 6. Memoria verticale e readiness

[`VerticalProjectMemoryBuilder`](../../src/p2p_engine/services/vertical_memory.py#L52)
materializza una vista del progetto organizzata secondo il verticale attivo.
La vista contiene manifest, stato complessivo e file per sezione. Supporta
rebuild completo, aggiornamento incrementale, fingerprint delle fonti e due
livelli di verifica della freshness:

- `status`, che ricalcola le fonti;
- `fast_status`, che verifica manifest e digest degli output senza una scansione
  semantica completa.

La readiness di progetto puo usare questa memoria invece di rileggere tutti gli
artefatti canonici. Distingue definizione, evidenza dichiarata, evidenza
euristica, domande, assunzioni e blocker. La memoria verticale e' quindi una
vista derivata del progetto, non una sostituzione delle fonti governate.

### 7. Publication

Il flusso editoriale parte da evidenze gestite e dal verticale attivo:

```text
fonti governate + verticale
  -> evidence index completo e fingerprint
  -> packet e profilo dell'edizione
  -> modello editoriale + accounting delle evidenze
  -> documento Markdown autonomo
  -> validazione
  -> eventuale render PDF
  -> review owner separata
```

[`ProjectPublicationService`](../../src/p2p_engine/services/project_publication.py#L221)
coordina edizioni distinte per lingua e nome output. Gli artefatti editoriali
sono derivati; la review non viene inferita dalla generazione o dal render.

### 8. Migrazione dello workspace

Il sottosistema di migrazione rileva lo schema, costruisce un piano per
transizioni adiacenti, raccoglie eventuali input owner, prepara un overlay
candidato e applica la modifica tramite lock, journal e recovery. La revisione
supporta il percorso legacy -> v1 -> v2 -> v3. Gli handler e il registro delle
migrazioni si richiamano tramite import locali e `TYPE_CHECKING` per evitare un
ciclo durante l'import.

## Dati, memoria e stato derivato

### `.p2p/` come boundary gestito

Rispetto alla codebase Python, `.p2p/` e' un'area dati esterna e persistente.
Non e' inclusa nelle metriche runtime, ma e' il principale boundary del
sistema. Il codice ne conosce il layout, applica versionamento dello schema e
legge o scrive gli artefatti tramite servizi e facade.

Nello snapshot locale l'area contiene circa 3.016 file. La distribuzione e'
dominata da proposte, Change Set e viste di progetto. Questo dato spiega perche
le scansioni ricorsive, la freshness e la ricostruzione degli indici sono
rilevanti anche in un sistema usato da una sola persona.

### Tre forme di memoria

**1. Fonti canoniche governate.** Comprendono proposte e relativi artefatti,
eventi decisionali append-only, definizione e domande del progetto, choice,
Change Set, Work, governance e configurazione. Il loro significato dipende
dallo schema workspace e dalle regole di autorita.

**2. Viste materializzate derivate.** Comprendono registri, memoria verticale,
proiezioni di progetto, software spec e artefatti publication. Hanno manifest,
fingerprint o regole di freshness e possono essere ricostruite dalle fonti.

**3. Indici di richiesta.** Il decision-context index e le cache di
`WorkspaceReadContext` vengono costruiti per una singola operazione. Non sono
persistenza canonica e non costituiscono una cache globale.

Questa distinzione e' importante: nel codice esistono gia sia compattazione
materializzata per verticale sia retrieval semantico su richiesta. Non e'
corretto descrivere la codebase come se rileggesse sempre ogni proposta, ma
alcuni percorsi completi continuano legittimamente a ricatalogare molte fonti.

### Grafo di freshness

Il servizio `derived_freshness` descrive dipendenze tra fonti canoniche e viste
come memoria verticale, registri, decision context, project projection,
assessment, software spec, brief, next action, export visibile e publication.
Lo stato completo puo invocare numerosi provider; i percorsi interattivi piccoli
usano invece controlli veloci quando disponibili.

**Interpretazione.** La codebase ha gia due strategie prestazionali coerenti
con il modello file-backed:

- materializzazione incrementale delle letture di progetto frequenti;
- cache e indici limitati alla richiesta per letture ad hoc.

Le strategie non eliminano il costo dei controlli globali e non sono una cache
di processo. La loro efficacia va valutata per singolo comando, non soltanto
dalla dimensione complessiva dello workspace.

## Persistenza e side effect

### Filesystem

**Osservato.** Il filesystem e' usato in `services`, `storage`, `foundation` e,
in misura minima, `exporters`. Non esiste un repository abstraction unico.
L'accesso ai file segue tre forme principali:

1. primitive atomiche condivise per singolo file;
2. `AtomicMutationWriter` per mutazioni multi-file con recovery;
3. procedure dirette o specifiche del servizio per output, copie, spostamenti e
   lifecycle legacy.

Questa pluralita e' una descrizione dello stato attuale. Non implica che ogni
scrittura debba usare la stessa transazione: per esempio gli output publication
fuori da `.p2p` hanno esigenze diverse. Tuttavia, il contratto di durabilita non
e' uniforme e va letto servizio per servizio.

### Git

Tutte le chiamate Git individuate passano da `storage/git.py`. L'adapter avvia
il binario locale e interpreta output e codici di ritorno. Le operazioni remote
possono produrre traffico di rete attraverso Git, ma il runtime non include un
client HTTP applicativo.

### Processi, terminale e PDF

- CLI scrive sul terminale tramite Typer/Rich;
- MCP legge e scrive messaggi JSON-RPC su stdio;
- il rendering PDF carica WeasyPrint opzionalmente;
- configurazione e discovery leggono variabili come `P2P_HOME` e
  `P2P_YAML_FORCE_PYTHON`.

Non sono emerse code path runtime che avviino processi esterni diversi da Git.

## Dipendenze interne

L'analisi statica degli import ha rilevato 593 archi tra moduli interni. Le
direzioni aggregate piu frequenti sono:

| Da | A | Archi misurati | Lettura |
| --- | --- | ---: | --- |
| `services` | `core` | 117 | I servizi consumano ampiamente i modelli e le policy. |
| `services` | `foundation` | 82 | YAML, file e Markdown sono primitive trasversali. |
| `storage` | `services` | 60 | `P2PWorkspace` compone e delega ai servizi. |
| `cli_commands` | package root | 25 | I comandi riusano soprattutto `cli_shared`. |
| `storage` | `core` | 18 | La facade espone o costruisce modelli core. |
| `mcp` | `storage` | 13 | Gli handler MCP passano dalla facade. |
| package root | `cli_commands` | 12 | `cli.py` registra i gruppi di comando. |

I moduli con maggiore fan-in sono helper file/YAML, mutation preview,
`cli_shared`, eventi decisionali e `P2PWorkspace`. Il maggiore fan-out appartiene
a `storage/filesystem.py`, seguito a distanza da servizi trasversali come
proposal artifacts, workspace compatibility e migration.

### Cicli statici osservati

Sono emerse due componenti fortemente connesse:

1. `lifecycle_authority` -> `proposal_decision_ledger` ->
   `proposal_decision_legacy` -> `lifecycle_authority`;
2. `workspace_migration_handlers` <-> `workspace_migration_registry`.

Import locali e blocchi `TYPE_CHECKING` evitano il fallimento durante l'import.
I cicli sono quindi una dipendenza concettuale/statica, non un errore runtime
dimostrato. Indicano aree che richiedono lettura congiunta.

### Accoppiamenti impliciti osservati

- alcuni servizi importano helper con nome privato da altri servizi;
- callback e provider manualmente iniettati rappresentano dipendenze che non
  sempre emergono dal solo grafo degli import;
- publication adatta alcune firme di provider tramite introspezione;
- il layout persistente collega servizi che non si importano direttamente.

Questi punti aumentano il lavoro necessario per ricostruire un flusso, ma non
sono classificati automaticamente come difetti.

## Test, packaging e release

### Test

La suite contiene 119 file Python e circa 38.395 righe. La raccolta tramite lo
script ufficiale ha individuato 1.448 test. La classificazione in
[`tests/conftest.py`](../../tests/conftest.py) assegna marker per area e usa
`service` come default per i test non classificati.

Gli script espongono quattro percorsi principali:

- [`test-focused.sh`](../../scripts/test-focused.sh): unita, servizi e adapter,
  esclusi i test slow;
- [`test-public.sh`](../../scripts/test-public.sh): superfici CLI e MCP;
- [`test-smoke.sh`](../../scripts/test-smoke.sh): smoke test;
- [`test-full.sh`](../../scripts/test-full.sh): intera suite.

Gli script impostano esplicitamente `PYTHONPATH=src`. Una raccolta diretta con
l'interprete dell'ambiente virtuale, senza tale impostazione, ha caricato una
versione installata non allineata al checkout e ha prodotto errori di import.
Questo non e' un errore della suite ufficiale, ma una differenza concreta tra
testare i sorgenti correnti e testare l'artefatto installato.

### Benchmark disponibili

Il repository contiene script mirati per:

- read path generali;
- read path MCP;
- memoria verticale a scala crescente;
- pipeline publication.

Sono strumenti di misura manuali, non gate permanenti. Questa fotografia non
riporta nuovi benchmark temporali perche l'obiettivo e' descrivere la struttura,
non stabilire una nuova baseline prestazionale.

### Packaging

[`pyproject.toml`](../../pyproject.toml) richiede Python 3.11 o successivo e
dipende a runtime da `packaging`, `PyYAML`, `Rich` e `Typer`. Il PDF e' un extra
con `markdown-it-py` e `weasyprint`. La wheel include `src/p2p_engine` e le
risorse distribuite, mentre esclude workspace, output, draft e specifiche del
repository.

Il workflow [`release.yml`](../../.github/workflows/release.yml) testa Python
3.11 e 3.14, verifica le superfici pubbliche e la suite completa, quindi
costruisce wheel e sdist su Python 3.11 prima di creare la release GitHub. I
test di packaging verificano anche l'assenza di `.p2p` negli artefatti e la
presenza dei vertical pack e dei moduli richiesti.

## Hotspot quantitativi

Lo snapshot runtime comprende 191 file Python e 75.479 righe. Sono state
rilevate 2.690 funzioni o metodi, 95 dei quali superano 100 righe e 27 superano
200 righe. Le classi rilevate sono 505.

I file piu grandi sono:

| File | Righe | Ruolo sintetico |
| --- | ---: | --- |
| `services/project_verticals.py` | 3.688 | Vertical pack, definizione e readiness del progetto. |
| `storage/filesystem.py` | 3.544 | Composition root e facade `P2PWorkspace`. |
| `services/vertical_memory.py` | 2.243 | Build, update, freshness e query della memoria verticale. |
| `services/project_questions.py` | 2.019 | Stato, riconciliazione e lifecycle delle domande di progetto. |
| `services/proposal_decisions.py` | 1.931 | Preview/apply e lifecycle append-only delle decisioni. |
| `services/project_publication.py` | 1.824 | Coordinamento del lifecycle publication. |
| `services/agent_templates.py` | 1.773 | Generazione delle risorse per agenti. |
| `services/decision_context_topology.py` | 1.418 | Normalizzazione del grafo decisionale. |
| `services/workspace_compatibility.py` | 1.410 | Compatibilita runtime/schema/operazioni. |
| `services/runtime_contract.py` | 1.338 | Contratto runtime e relative mutazioni. |

La dimensione di `agent_templates.py` include molto testo di template e non va
equiparata automaticamente a complessita algoritmica.

Le funzioni piu estese comprendono registratori CLI, cataloghi e dispatcher MCP,
costruzione del context packet, readiness verticale, build della memoria e
pianificazione delle migrazioni. La concentrazione e' quindi presente sia nei
domini centrali sia nel codice che dichiara le superfici pubbliche.

## Stato osservato: punti di forza strutturali

Questi elementi sono presenti e verificabili, senza giudicare se siano la forma
definitiva:

- CLI e MCP riusano la stessa facade e gli stessi servizi;
- `core` resta indipendente dagli adapter e dagli accessi al filesystem;
- runtime contract, schema e lock vengono controllati prima delle scritture
  governate;
- le decisioni v3 usano eventi append-only e mutazioni preview/apply;
- esiste una transazione multi-file con precondizioni, journal e recovery;
- le letture possono rilevare modifiche concorrenti;
- memoria verticale e registri riducono scansioni ripetute nei percorsi comuni;
- il decision context supporta retrieval bounded senza introdurre un database;
- vertical pack e risorse sono inclusi e verificati negli artefatti package;
- test pubblici, completi e di packaging distinguono checkout e distribuzione.

## Problemi e incertezze supportati da evidenze

Questa sezione non definisce ancora interventi.

### 1. Il confine della facade e' molto ampio

**Osservato.** `P2PWorkspace` espone 251 metodi pubblici e dipende da 81 moduli.
CLI, MCP e molti test la attraversano.

**Incertezza.** Non e' ancora misurato quali gruppi di metodi cambino insieme o
quali client usino direttamente porzioni specifiche della facade. Senza questa
informazione, dividerla soltanto per dimensione sarebbe prematuro.

### 2. `services` concentra comportamenti eterogenei

**Osservato.** Il package contiene logica di dominio, orchestrazione,
persistenza, rendering e integrazione. Alcuni file superano 1.000 o 2.000 righe.

**Incertezza.** Le dimensioni non distinguono codice intrinsecamente coeso da
responsabilita accidentalmente aggregate. Servono analisi per flusso e storia
delle modifiche prima di proporre confini diversi.

### 3. Le dipendenze runtime sono in parte implicite

**Osservato.** I servizi ricevono numerosi callback/provider; esistono helper
privati condivisi e due cicli statici mitigati da import ritardati.

**Problema pratico.** Il grafo degli import da solo non basta a spiegare la
collaborazione tra componenti. La manutenzione richiede spesso di seguire la
costruzione dei servizi dentro `P2PWorkspace`.

### 4. La durabilita delle scritture non ha un unico contratto

**Osservato.** Coesistono transazione multi-file, sostituzione atomica di
singolo file e procedure dirette o specifiche.

**Da verificare.** Per ogni lifecycle critico va accertato se la forma scelta e'
deliberata e quale comportamento garantisca in caso di crash. Questa fotografia
non assume che uniformare tutto sia la soluzione corretta.

### 5. La superficie pubblica e' ampia

**Misurato.** Sono presenti 241 comandi CLI foglia, 174 tool MCP e 251 metodi
pubblici nella facade.

**Problema pratico.** Aumentano i contratti da navigare e verificare. Non e'
stato pero misurato quali comandi siano ridondanti, legacy o realmente usati;
una riduzione non puo essere dedotta dai soli conteggi.

### 6. Stato derivato e freshness formano un sottosistema articolato

**Osservato.** Registri, memoria verticale, proiezioni, decision context,
assessment, spec e publication hanno strategie di build e freshness diverse.

**Interpretazione.** Questa articolazione risponde alla scala dello workspace
file-backed, ma rende importante sapere quale vista sia usata da ogni comando.
Il full freshness graph puo attivare molti provider; i percorsi veloci esistono
ma non sono universali.

### 7. Checkout e package installato sono due ambienti distinti

**Osservato.** Gli script ufficiali testano `src`; un comando pytest diretto puo
importare una build installata precedente.

**Problema pratico.** Un risultato locale puo essere interpretato male se non e'
chiaro quale codice sia stato importato. Packaging e release coprono entrambi i
mondi, ma il flusso manuale richiede attenzione.

### 8. Alcune sovrapposizioni richiedono chiarimento

**Da verificare.** I piccoli moduli `exporters` convivono con il piu recente
`SpecExportService` e con la publication pipeline. Il repository non rende
immediatamente evidente se siano compatibilita mantenuta, uso ancora attivo o
superficie sostituibile.

**Da verificare.** `project_publication.py` usa una procedura transazionale
diversa da quella dello workspace. La diversa destinazione degli output la
rende plausibile, ma il contratto di recovery va interpretato nel suo lifecycle
specifico.

## Domande aperte per una verifica successiva

Le seguenti domande emergono dal codice e non sono decisioni architetturali:

1. Quali comandi dominano davvero il tempo percepito dall'utente su workspace
   piccoli, medi e grandi?
2. Quali provider del freshness graph vengono attivati dai comandi interattivi
   piu frequenti e quali usano gia il fast path?
3. Quali metodi di `P2PWorkspace` sono usati soltanto come deleghe e quali
   contengono ancora policy o accessi diretti?
4. Quali callback tra servizi rappresentano veri contratti stabili e quali sono
   dipendenze contingenti?
5. I due cicli statici corrispondono a un unico concetto indivisibile o a confini
   oggi sovrapposti?
6. Quali scritture dirette richiedono garanzie di recovery e quali producono
   output rigenerabili senza rischio canonico?
7. `exporters` e le compatibility surface storiche hanno ancora chiamanti
   esterni o soltanto test di regressione?
8. Quali parti dei grandi file cambiano insieme nella storia Git e quali invece
   evolvono indipendentemente?
9. Qual e' il costo separato di catalogazione, parsing YAML, hashing, retrieval
   e rendering nei flussi lenti?
10. Quali contratti sono intenzionalmente pubblici per integrazioni terze oltre
    a CLI e MCP?

## Possibili approfondimenti futuri, non decisioni

Solo dopo aver validato la fotografia si potranno valutare, separatamente:

- profiling dei comandi percepiti come lenti con i benchmark gia presenti;
- analisi dei chiamanti e della coesione dei maggiori hotspot;
- verifica mirata dei contratti di scrittura e recovery;
- inventario d'uso delle superfici CLI/MCP/facade;
- confronto tra responsabilita dichiarate e modifiche che avvengono insieme;
- eventuali estrazioni modulari limitate, sostenute da test esistenti.

Queste sono direzioni di indagine. Il documento non conclude che servano un
nuovo framework, un database, una riscrittura, nuovi gate o una diversa
organizzazione del repository.

## Conclusione

P2P Engine e' oggi un sistema Python file-backed con un dominio ampio, due
adapter pubblici condivisi, una facade centrale, persistenza versionata e
diverse viste derivate per limitare il costo della memoria progettuale. La
codebase contiene meccanismi robusti per compatibilita, letture coerenti,
mutazioni sensibili e packaging, ma concentra molta orchestrazione nei servizi
e una superficie molto estesa nella facade e negli adapter.

La fotografia consente di localizzare complessita e incertezze senza assumere
una soluzione. Il passo successivo, quando richiesto, dovrebbe verificare una
domanda concreta alla volta usando chiamanti, test, profiling e storia delle
modifiche, mantenendo separate l'osservazione del sistema attuale e la scelta
della sua eventuale architettura futura.
