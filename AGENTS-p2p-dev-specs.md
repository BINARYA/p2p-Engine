# AGENTS-p2p-dev-specs — Regole Locali per Specs di Sviluppo

Questo file definisce linee guida **locali al repository P2P Engine** per
progettare, scrivere e mantenere specifiche di sviluppo (`specs/`).

Queste regole servono a separare la governance P2P dalla consegna del codice:

- `.p2p/` governa problemi, proposte, scelte, decisioni e readiness.
- `specs/` traduce una direzione approvata in contesto tecnico e task
  operativi di implementazione.
- `src/`, `tests/` e `docs/` contengono codice, verifiche e documentazione
  effettivamente mantenuta o rilasciata.

Le specs locali non sono parte dell'API o del prodotto rilasciato di P2P
Engine, salvo decisione esplicita del proprietario. Non devono essere incluse
nel comportamento runtime, nei comandi pubblici, nei template distribuiti o
nella documentazione di release solo perché esistono nel repository.

## 0) Quando usare questo file

Gli agenti devono usare queste regole quando viene chiesto di:

- implementare codice nel repository P2P Engine;
- trasformare una proposta P2P accettata in contesto tecnico di sviluppo;
- ampliare una direzione P2P in `requirements.md`, `design.md` e `tasks.md`;
- generare passi operativi per consegnare una feature o una modifica tecnica;
- chiarire gap tra governance P2P, design tecnico e lavoro implementativo.
- collegare un output generato di project definition alle specs locali e
  verificare quali task risultano davvero implementati nel codice.

Quando il punto di partenza è una proposta P2P accettata, leggere la proposta
tramite gli strumenti P2P disponibili, poi produrre o aggiornare specs locali
fuori da `.p2p/`. Le specs possono derivare dall'output P2P, ma non devono
duplicare lo stato P2P né sostituire decisioni del proprietario.

## 1) Scopo delle specs

Le specs servono a:

- allineare business, prodotto e implementazione
- ridurre ambiguità prima del codice
- rendere tracciabili decisioni e compromessi
- permettere a umani e AI di lavorare in modo coerente

Una spec valida deve essere:

- chiara
- verificabile
- implementabile
- mantenibile nel tempo

## 2) Principi guida

1. **Source of truth separata per livello**
Le decisioni di governance/prodotto vivono in P2P. Le decisioni funzionali e
tecniche necessarie a implementare codice vivono nelle specs locali, non in chat
sparse o commit message.

2. **Separazione tra cosa e come**
`requirements.md` descrive *cosa* deve fare il sistema.
`design.md` descrive *come* lo fa.
`tasks.md` descrive *come* si consegna il lavoro.

3. **Verificabilità**
Ogni requisito deve poter essere testato con un esito binario (pass/fail).

4. **Atomicità**
Un requisito deve descrivere un solo comportamento osservabile.

5. **Tracciabilità**
Ogni task deve mappare a requisiti e design. Nessun task “orfano”.

Per lavoro derivato da P2P, ogni feature spec deve indicare la proposta,
decisione o scelta sorgente quando esiste.

6. **Evoluzione controllata**
Se cambia un requisito, vanno aggiornati anche design e task correlati.

7. **Esplicitazione delle assunzioni**
Assunzioni, vincoli e dipendenze devono essere scritti: niente conoscenza implicita.

8. **Decisioni motivate**
Ogni decisione importante deve includere razionale e impatti.

9. **Incrementalità**
Favorire slice piccole e rilasciabili, evitando piani monolitici.

10. **Linguaggio operativo**
Testo concreto, non marketing. Evitare formule vaghe (“ottimizzare”, “migliorare”).

## 3) Struttura standard consigliata

```
specs/
├── steering/
│   ├── product.md
│   ├── domain.md
│   ├── structure.md
│   └── tech.md
└── features/
    └── <feature-name>/
        ├── requirements.md
        ├── design.md
        └── tasks.md
```

Questa struttura è locale al repository. Non usare `.p2p/changes`,
`.p2p/work` o altri file gestiti P2P per rappresentare task di coding minuto,
sequenze di modifica file, checklist implementative o stato operativo dei
branch.

## 4) Ruolo dei file steering

- `product.md`: obiettivi, utenti, problema, perimetro funzionale
- `domain.md`: concetti, glossario, regole di business invarianti
- `structure.md`: confini tra moduli/sistemi e ownership
- `tech.md`: stack, standard, vincoli operativi e di deploy

Questi file sono il contesto stabile e trasversale alle feature.

## 5) Regole per `requirements.md`

### Formato consigliato (EARS-like)

Usare frasi normative:

- `WHEN <evento/trigger>, THE SYSTEM SHALL <comportamento>`
- `IF <condizione>, THEN THE SYSTEM SHALL <comportamento>`
- `THE SYSTEM SHALL <vincolo sempre vero>`

### Regole pratiche

- Un requisito = un comportamento osservabile
- Usare termini misurabili, evitare “rapido”, “intuitivo”, “robusto” senza metrica
- Distinguere requisiti funzionali e non funzionali
- Includere casi limite e condizioni di errore
- Evitare dettagli implementativi (framework, query, classi), salvo vincoli espliciti

### Checklist minima

- Copre happy path, edge case, failure path
- È testabile senza interpretazioni soggettive
- Non contraddice steering o altri requisiti
- Se deriva da P2P, cita la sorgente P2P e non introduce decisioni non approvate

## 6) Regole per `design.md`

`design.md` traduce i requisiti in architettura implementabile.

### Contenuti attesi

- decisioni principali (con motivazione)
- componenti coinvolti e responsabilità
- flussi dati/API/interfacce
- modello dati e contratti
- gestione errori, idempotenza, retry, osservabilità (se rilevante)
- rischi, tradeoff, alternative considerate

### Regole pratiche

- Ogni blocco di design deve riferirsi ai requisiti che soddisfa
- Esplicitare cosa **non** viene fatto (out of scope tecnico)
- Evidenziare impatti backward compatibility/migrazioni

## 7) Regole per `tasks.md`

`tasks.md` è il piano di consegna eseguibile.

### Regole pratiche

- Task piccoli, verticali e verificabili
- Ogni task deve produrre un output concreto (file, test, migration, doc)
- Ogni task deve essere tracciabile a requisiti/design
- Ordinare i task in dipendenza logica, non cronologica arbitraria
- Includere task di validazione (test automatici, smoke test, check manuali)
- Non usare `tasks.md` per registrare stato governato, decisioni P2P o avanzamento
  autoreferenziale: quello resta nella conversazione di lavoro, in Git, nei test
  o negli strumenti di review.

### Formato consigliato

- Checkbox markdown (`- [ ]`, `- [x]`)
- Frase breve: `azione + artefatto + criterio di completamento`

## 8) Tracciabilità minima obbligatoria

Ogni feature deve permettere queste domande:

1. Quale requisito sto implementando?
2. Quale decisione di design lo copre?
3. Quale task lo realizza?
4. Quale test dimostra che funziona?
5. Se deriva da P2P, quale proposta/scelta/decisione ha originato il lavoro?

Se una risposta manca, la spec è incompleta.

## 9) Workflow di aggiornamento specs

Quando cambia la feature:

1. aggiornare `requirements.md` (fonte primaria del cambiamento)
2. aggiornare `design.md` (impatto tecnico)
3. aggiornare `tasks.md` (piano operativo)
4. aggiornare test/documentazione collegati

Mai aggiornare solo `tasks.md` se il comportamento richiesto è cambiato.

## 10) Anti-pattern da evitare

- requisiti ambigui o non testabili
- design senza rationale (“si fa così e basta”)
- task troppo grandi (“implementare tutta la feature”)
- mismatch tra requisito e task consegnati
- conoscenza critica tenuta solo in conversazioni private
- copia/incolla di template non adattati al caso reale

## 11) Contratto operativo per agenti AI

Un agente AI che lavora con queste specs deve:

1. leggere prima steering + feature specs rilevanti
2. non inventare requisiti mancanti: deve esplicitare assunzioni
3. proporre aggiornamenti specs quando trova gap o incoerenze
4. mantenere coerenza tra requirements, design e tasks
5. preferire modifiche piccole, verificabili e tracciabili
6. quando implementa codice derivato da P2P, usare P2P solo per leggere la
   direzione approvata e usare `specs/` per il contesto e i task operativi
7. non scrivere dettagli implementativi o stato dei task dentro `.p2p/`
8. non trattare le specs locali come contenuto di release senza richiesta esplicita
9. quando lavora da un export generato `project.md`/`propose.md`, seguire
   `specs/methods/project-output-binding.md` e `specs/skills/project-output-binding.md`;
   segnare task completati solo con evidenza da `src/`, `tests/`, `docs/` o
   comportamento CLI osservato

## 12) Template rapido (riuso)

### `requirements.md`

- Scopo
- Origine P2P o origine locale della richiesta
- In scope / Out of scope
- Requisiti funzionali (normativi)
- Requisiti non funzionali
- Casi limite ed errori
- Criteri di accettazione

### `design.md`

- Decisioni chiave + rationale
- Architettura e componenti
- Flussi e contratti dati/API
- Strategia error handling/observability
- Tradeoff e alternative
- Piano di migrazione/compatibilità

### `tasks.md`

- Preparazione/analisi
- Implementazione per slice
- Test e validazione
- Rollout e monitoraggio
- Chiusura (doc, cleanup, handover)

---

Questo file deve essere richiamato dalle istruzioni degli agenti locali quando
il lavoro passa dalla governance P2P all'implementazione del codice.

Se serve, può essere importato da `AGENTS.md` con:

`@AGENTS-p2p-dev-specs.md`
