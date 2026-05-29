# P2P Engine — Landscape, riferimenti e posizionamento

> This is a vision and positioning document. It contains implemented, planned,
> and exploratory ideas. For current usage, start with `../../README.md`,
> `../INSTALL.md`, `../TUTORIAL.md`, `../CONCEPTS.md`, `../CLI-GUIDE.md`, and
> `../MCP.md`.

**Versione:** 0.1  
**Data:** 2026-05-19  
**Stato:** documento di benchmark e orientamento progettuale  
**Documento collegato:** `p2p-engine-foundation.md`

---

## 1. Scopo del documento

Questo documento raccoglie i principali sistemi, framework e approcci che possono ispirare la progettazione di **P2P Engine**.

L'obiettivo non è copiare un prodotto esistente, ma capire:

- quali idee sono già state esplorate;
- quali pattern funzionano;
- quali limiti evitare;
- quali parti possono diventare input per l'architettura di P2P Engine;
- come posizionare P2P Engine rispetto a strumenti già presenti nell'ecosistema AI, Git e spec-driven development.

Il documento va letto come supporto al documento principale `p2p-engine-foundation.md`, che resta la base progettuale stabile.

---

## 2. Sintesi del posizionamento

P2P Engine si posiziona **a monte** degli strumenti di spec-driven development, AI coding e project execution.

La sua funzione principale è trasformare discussioni collaborative in decisioni progettuali, piani e task eseguibili.

```text
Discussione collaborativa
→ contributi strutturati
→ proposal
→ confronto alternative
→ sintesi AI
→ governance decisionale
→ decisione
→ execution plan
→ task/action
→ export verso strumenti esterni
```

A differenza di molti strumenti esistenti, P2P Engine non parte dal codice e nemmeno necessariamente da una specifica software.

Parte da elementi più grezzi e trasversali:

- feature request;
- variante proposta da un altro utente;
- principio architetturale;
- obiettivo commerciale;
- suggestione strategica;
- vincolo operativo;
- rischio;
- obiezione;
- proposta marketing;
- idea documentale;
- task di ricerca.

Il codice è solo uno dei possibili output.

---

## 3. Mappa dei sistemi analoghi

| Sistema | Ambito principale | Cosa insegna a P2P Engine | Limite rispetto a P2P Engine |
|---|---|---|---|
| GitHub Spec Kit | Spec-driven development software | Constitution, spec, plan, tasks, integrazione agenti | Centrato sul software e sulla fase post-proposal |
| OpenSpec | Change proposal e spec-driven development | Proposal/change come unità di lavoro esportabile | Poco orientato a governance e multi-dominio |
| Kiro | IDE agentico spec-first | UX requirements → design → tasks | Prodotto IDE, non engine Git-native neutro |
| BMAD Method | Metodo AI-driven agile | Agenti specializzati e workflow guidati | Orientamento software/agile, meno proposal-governance |
| Aider | AI pair programming da terminale | CLI Git-native semplice e potente | Orientato alla modifica codice, non alle decisioni |
| Maestro | Orchestrazione agenti AI | Gestione di più agenti/progetti | Orquestra agenti, non proposal e governance |
| Gerrit | Review Git-based | Review, approval, audit trail | Lavora su patch/codice, non su proposal generali |
| MCP | Protocollo integrazione agenti/tool | Esporre P2P Engine come tool usabile dagli agenti | Richiede attenzione forte a sicurezza e sandbox |

---

## 4. Analisi dei riferimenti

---

### 4.1 GitHub Spec Kit

#### Cosa fa

GitHub Spec Kit è un toolkit open source per fare **spec-driven development**. L'approccio sposta il centro dal codice alla specifica: prima si chiarisce cosa costruire, poi si genera piano, task e infine implementazione tramite agenti AI.

Il flusso tipico è:

```text
constitution
→ specify
→ clarify
→ checklist
→ plan
→ tasks
→ analyze
→ implement
```

Spec Kit supporta diversi agenti AI e lavora con artefatti Markdown salvati nel repository.

#### Cosa prendere

P2P Engine dovrebbe prendere da Spec Kit:

- l'idea di **artefatti versionati** nel repository;
- il concetto di **constitution** come documento di principi e vincoli;
- la pipeline a fasi;
- il passaggio da specifica a piano e task;
- la possibilità di generare comandi/istruzioni per diversi agenti AI;
- l'uso di template e workflow personalizzabili;
- la logica di validazione progressiva degli artefatti.

#### Cosa evitare

P2P Engine non dovrebbe limitarsi al paradigma:

```text
feature software → specifica → codice
```

Perché il nostro obiettivo è più ampio:

```text
contributo umano → discussione → decisione → piano → deliverable
```

Il deliverable può essere codice, ma anche documento, proposta commerciale, campagna marketing, procedura operativa o attività di ricerca.

#### Relazione con P2P Engine

Spec Kit è un possibile **target downstream**.

P2P Engine può esportare verso Spec Kit quando una proposal approvata contiene lavoro software.

```text
P2P Engine
→ accepted proposal
→ execution plan
→ software workstream
→ export Spec Kit
→ spec/plan/tasks/implementation
```

---

### 4.2 OpenSpec

#### Cosa fa

OpenSpec è un framework leggero per spec-driven development orientato agli AI coding assistant. Il suo modello è basato su modifiche proposte, ciascuna organizzata in una propria cartella con artefatti come proposal, design, tasks e spec delta.

Il flusso concettuale è vicino a:

```text
proposal
→ specs
→ design
→ tasks
→ implement
→ apply/archive
```

#### Cosa prendere

P2P Engine dovrebbe prendere da OpenSpec:

- il concetto di **change proposal** come unità operativa;
- la separazione tra proposta, design, task e specifiche;
- l'organizzazione file-based;
- la possibilità di mantenere una source of truth delle specifiche;
- il concetto di change applicabile/archiviabile;
- la compatibilità con più AI assistant.

#### Cosa evitare

OpenSpec resta orientato allo sviluppo software. P2P Engine deve evitare di trattare tutto come una change software.

Una proposta può essere:

- software;
- architetturale;
- commerciale;
- marketing;
- operations;
- documentale;
- governance;
- ricerca;
- mista.

#### Relazione con P2P Engine

OpenSpec è probabilmente uno dei migliori target di export per le proposal software.

Mapping possibile:

```text
P2P Engine proposal.md
→ openspec/changes/<change>/proposal.md

P2P Engine execution-plan.md
→ openspec/changes/<change>/design.md

P2P Engine tasks.yml/tasks.md
→ openspec/changes/<change>/tasks.md

P2P Engine software requirements
→ openspec/changes/<change>/specs/<domain>/spec.md
```

---

### 4.3 Kiro

#### Cosa fa

Kiro è un IDE agentico orientato a uno sviluppo guidato da specifiche. Prima della scrittura del codice aiuta a produrre requisiti, design e task.

Il valore principale è nella UX: l'utente viene guidato verso una maggiore chiarezza prima dell'implementazione.

#### Cosa prendere

P2P Engine dovrebbe prendere da Kiro:

- l'idea di una UX guidata;
- la sequenza requirement → design → tasks;
- l'approccio che riduce il “vibe coding”;
- la centralità delle domande prima della generazione;
- l'attenzione alla chiarezza dei requisiti.

#### Cosa evitare

Kiro è un prodotto IDE-oriented. P2P Engine non dovrebbe diventare dipendente da un IDE o da una esperienza solo visuale.

La nostra direzione è:

```text
core engine
→ CLI
→ web app successiva
→ exporter
→ AI adapters
```

non:

```text
IDE monolitico
```

#### Relazione con P2P Engine

Kiro è utile come riferimento per l'esperienza utente, soprattutto per:

- domande guidate;
- chiarimento requisiti;
- passaggio da idea a design;
- generazione task.

---

### 4.4 BMAD Method

#### Cosa fa

BMAD Method è un framework AI-driven/agile che usa agenti specializzati e workflow guidati per accompagnare il progetto dall'ideazione alla pianificazione e all'implementazione.

Introduce ruoli AI specializzati, come analyst, product manager, architect, developer, QA e altri profili.

#### Cosa prendere

P2P Engine dovrebbe prendere da BMAD:

- il concetto di **ruoli AI specializzati**;
- workflow che cambiano in base alla complessità;
- l'idea di front-loaded planning;
- la separazione tra analisi, prodotto, architettura, sviluppo e QA;
- la possibilità di far intervenire l'AI con “cappelli” diversi.

Esempi di ruoli AI utili per P2P Engine:

```text
AI Facilitator
AI Analyst
AI Product Reviewer
AI Architect
AI Risk Reviewer
AI Governance Assistant
AI Planner
AI Task Generator
AI Export Assistant
```

#### Cosa evitare

P2P Engine non deve diventare una metodologia agile rigida o solo software-oriented.

Il nostro modello deve restare:

```text
proposal-centered
multi-dominio
Git-native
export-oriented
```

#### Relazione con P2P Engine

BMAD è utile per progettare la parte multi-agent o multi-role del sistema, ma P2P Engine deve restare più generale e centrato sulla governance delle proposal.

---

### 4.5 Aider

#### Cosa fa

Aider è uno strumento di AI pair programming da terminale. Lavora direttamente su repository Git locali e permette di modificare codice tramite conversazione con un LLM.

#### Cosa prendere

P2P Engine dovrebbe prendere da Aider:

- CLI semplice e potente;
- integrazione naturale con Git;
- esperienza developer-friendly;
- lavoro locale sul repository;
- possibilità di usare diversi modelli AI.

#### Cosa evitare

Aider è pensato per modificare codice. P2P Engine non deve partire dalla modifica del codice, ma dalla decisione progettuale.

P2P Engine deve rispondere prima a:

```text
Che decisione stiamo prendendo?
Quali alternative esistono?
Quali trade-off abbiamo?
Chi approva?
Quale piano ne deriva?
```

Solo dopo, eventualmente:

```text
Che codice va scritto?
```

#### Relazione con P2P Engine

Aider è un possibile riferimento per la UX CLI, non per il modello di governance.

---

### 4.6 Maestro

#### Cosa fa

Maestro è un'app desktop cross-platform per orchestrare una flotta di agenti AI e più progetti in parallelo.

#### Cosa prendere

P2P Engine dovrebbe prendere da Maestro:

- l'idea di orchestrare strumenti AI differenti;
- il concetto di progetti multipli;
- sessioni isolate;
- controllo centrale dei lavori agentici;
- eventuale dashboard futura.

#### Cosa evitare

P2P Engine non deve ridursi a un orchestratore di agenti.

La sua specificità è orchestrare:

```text
contributi
proposal
discussioni
commenti
sintesi
decisioni
piani
task
export
```

Gli agenti AI sono strumenti al servizio del processo, non il processo stesso.

#### Relazione con P2P Engine

Maestro può ispirare la futura interfaccia web/desktop e la gestione multi-agent, ma non sostituisce il cuore proposal-to-plan.

---

### 4.7 Gerrit e sistemi di code review Git-based

#### Cosa fa

Gerrit è un sistema web-based di code review per repository Git. Permette review patchset-based, permessi granulari e integrazione con pipeline CI/CD.

#### Cosa prendere

P2P Engine dovrebbe prendere da Gerrit:

- review formale;
- stati di approvazione;
- audit trail;
- integrazione con Git;
- separazione tra proposta e merge;
- permessi e ruoli;
- decisione accetta/rifiuta.

#### Cosa evitare

Gerrit lavora sulle patch di codice. P2P Engine deve lavorare prima sulle proposal e sulle decisioni, non solo sulle modifiche tecniche.

#### Relazione con P2P Engine

Gerrit è utile come modello mentale per la governance Git-based:

```text
proposal branch
→ review
→ commenti
→ decisione
→ merge/archive
```

---

### 4.8 MCP — Model Context Protocol

#### Cosa fa

MCP è uno standard aperto per collegare applicazioni AI a strumenti, dati e workflow esterni.

Nel contesto P2P Engine, MCP consentirebbe a Codex, Claude, Cursor o altri agenti di usare P2P Engine come tool.

#### Cosa prendere

P2P Engine dovrebbe considerare MCP per esporre strumenti come:

```text
p2p_create_project
p2p_create_proposal
p2p_add_contribution
p2p_generate_digest
p2p_compare_alternatives
p2p_rank_comments
p2p_record_decision
p2p_generate_plan
p2p_generate_tasks
p2p_export_openspec
p2p_export_speckit
```

#### Cosa evitare

MCP non va introdotto troppo presto se il core non è stabile.

Inoltre va trattato con attenzione per:

- sicurezza;
- sandbox;
- permessi;
- validazione input;
- controllo dei comandi eseguibili;
- isolamento workspace.

#### Relazione con P2P Engine

MCP è una direzione strategica successiva:

```text
MVP CLI
→ AI prompt generator
→ AI adapters
→ export
→ MCP server
```

---

## 5. Cosa P2P Engine deve copiare

### 5.1 Da Spec Kit

- Artefatti Markdown versionati.
- Constitution del progetto.
- Workflow a fasi.
- Spec → plan → tasks per la parte software.
- Integrazione con più agenti AI.
- Template personalizzabili.
- Check di coerenza.

### 5.2 Da OpenSpec

- Change proposal come unità di lavoro.
- Separazione proposal/design/tasks/specs.
- Struttura file-based.
- Export verso AI coding assistant.
- Gestione di modifiche applicabili/archiviabili.

### 5.3 Da Kiro

- UX guidata.
- Domande prima della generazione.
- Requirements/design/tasks come progressione comprensibile.
- Riduzione del “vibe coding”.

### 5.4 Da BMAD Method

- Ruoli AI specializzati.
- Planning front-loaded.
- Workflow adattivi.
- Agenti con responsabilità diverse.

### 5.5 Da Aider

- CLI locale semplice.
- Git come contesto naturale.
- Supporto a più modelli.
- Developer experience rapida.

### 5.6 Da Maestro

- Orchestrazione multi-agent.
- Gestione di progetti multipli.
- Sessioni isolate.
- Possibile dashboard futura.

### 5.7 Da Gerrit

- Review formale.
- Stati di approvazione.
- Audit trail.
- Merge come momento decisionale.

### 5.8 Da MCP

- Tool interface per agenti AI.
- Standardizzazione dell'accesso ai comandi P2P.
- Possibilità di far usare P2P Engine da strumenti diversi.

---

## 6. Cosa P2P Engine deve evitare

P2P Engine dovrebbe evitare:

1. **Essere solo un clone di Spec Kit**  
   Spec Kit è utile per software specification, ma P2P Engine deve coprire discussione, governance e piani multi-dominio.

2. **Essere solo un clone di OpenSpec**  
   OpenSpec è molto utile come target, ma P2P Engine deve partire prima della change proposal già ordinata.

3. **Essere solo un coding assistant**  
   Il valore di P2P Engine non è scrivere codice, ma trasformare decisioni collaborative in piani eseguibili.

4. **Partire dalla web app**  
   La web app deve arrivare dopo core engine e CLI.

5. **Dipendere da GitHub**  
   Git è centrale, GitHub no. Il sistema deve funzionare anche con GitLab, Gitea, Bitbucket o repository locali.

6. **Dipendere da un solo modello AI**  
   Codex, Claude, Llama locale, OpenAI API, Anthropic API e Ollama devono essere intercambiabili tramite adapter.

7. **Mescolare tutto con il software**  
   Task marketing, commerciali, documentali e operative non devono essere forzate dentro uno schema da sviluppo software.

8. **Far decidere l'AI al posto del team**  
   L'AI può sintetizzare, confrontare, ordinare, evidenziare rischi e generare piani. La decisione resta umana o governance-defined.

9. **Generare output AI non validati**  
   Ogni digest, proposal, piano e task deve rispettare uno schema minimo e passare controlli di coerenza.

10. **Introdurre MCP o sandbox complesse troppo presto**  
    Prima serve stabilizzare il core e la CLI.

---

## 7. Differenziazione di P2P Engine

La differenza di P2P Engine rispetto ai riferimenti studiati è questa:

```text
P2P Engine non è un coding assistant.
P2P Engine non è solo uno spec generator.
P2P Engine non è solo un project manager.
P2P Engine non è solo un issue tracker.
P2P Engine non è solo un orchestratore di agenti.
```

P2P Engine è un:

```text
Collaborative Proposal-to-Plan Engine
```

La sua promessa è:

```text
trasformare discussioni collaborative, proposte alternative e contributi disordinati
in decisioni tracciate, specifiche progettuali, execution plan, task e action.
```

Il suo posizionamento:

```text
A monte di Spec Kit
A monte di OpenSpec
A monte degli issue tracker
A monte degli AI coding assistant
A monte del codice
```

Output possibili:

```text
- proposal strutturata
- confronto alternative
- sintesi commenti
- decisione governance
- execution plan
- task/action
- export OpenSpec
- export Spec Kit
- export Markdown
- export issue tracker
- documenti marketing
- documenti commerciali
- procedure operative
```

---

## 8. Implicazioni per l'MVP

Il benchmark conferma che l'MVP non deve partire dalla web app e non deve partire dalla generazione codice.

L'MVP dovrebbe validare il cuore del metodo.

### MVP consigliato

```text
P2P Core Engine
+ CLI Git-native
+ file-based storage
+ prompt generator
+ agent-files per Codex/Claude/generic
+ export Markdown
+ export OpenSpec
+ struttura pronta per export Spec Kit
```

### Comandi minimi

```bash
p2p init
p2p proposal create
p2p contribution add
p2p comment add
p2p digest
p2p clarify
p2p synthesize
p2p compare
p2p decision request
p2p plan
p2p tasks
p2p export --target markdown
p2p export --target openspec
```

### Da non includere nell'MVP

```text
- web app multiutente
- billing AI
- account centralizzati
- dashboard avanzata
- integrazione issue tracker bidirezionale
- MCP server
- implementazione automatica codice
- permessi complessi
```

---

## 9. Decisioni progettuali derivate

### Decisione 1 — P2P Engine sarà upstream

P2P Engine non sostituisce Spec Kit, OpenSpec o gli AI coding assistant.

Li alimenta.

```text
P2P Engine
→ OpenSpec
→ Spec Kit
→ Codex/Claude/Aider
→ issue tracker
→ documenti non software
```

---

### Decisione 2 — Il modello centrale è la proposal

La proposal è l'unità centrale di lavoro.

Una proposal può riguardare:

- software;
- architettura;
- marketing;
- commerciale;
- operations;
- documentazione;
- governance;
- ricerca;
- mix di domini.

---

### Decisione 3 — La CLI arriva prima della web app

La CLI è il primo prodotto reale.

La web app arriverà dopo, come client collaborativo sopra un engine già funzionante.

---

### Decisione 4 — AI pluggable, non AI-owned

P2P Engine deve integrare AI diverse senza dipendere da una sola.

Modalità previste:

```text
1. Prompt generator
2. Agent-files / skills
3. CLI adapter
4. API adapter
5. MCP server futuro
```

---

### Decisione 5 — Git è source of truth, non GitHub

Il sistema userà Git per:

- versioning;
- branch proposal;
- audit;
- merge;
- storia decisionale;
- portabilità.

Ma non dovrà dipendere da GitHub.

---

### Decisione 6 — Documenti leggibili + dati strutturati

Convenzione iniziale:

```text
Markdown = documenti leggibili
YAML/JSON = dati strutturati
```

Esempio:

```text
proposal.md
decision.md
execution-plan.md
comparison.md
ai-digest.md

contributions.yml
comments.yml
tasks.yml
project.yml
```

---

### Decisione 7 — L'AI assiste, non governa

L'AI può:

- sintetizzare;
- confrontare;
- chiarire;
- suggerire;
- ordinare;
- evidenziare conflitti;
- generare piani;
- generare task/action.

La governance decide.

---

## 10. Rischi progettuali

| Rischio | Descrizione | Mitigazione |
|---|---|---|
| Troppa astrazione | Il sistema rischia di diventare troppo generale | MVP ristretto su CLI + proposal software/documentale |
| Clone di tool esistenti | Rischio di imitare Spec Kit/OpenSpec senza differenziazione | Mantenere focus su discussion → governance → plan |
| Complessità AI | Troppi provider e modalità | Partire con prompt generator + generic adapter |
| Complessità web | Web app anticipata troppo presto | Prima core e CLI |
| Costi AI | Web con account centralizzato genera spesa | BYOK solo in fase web, nessun costo nel MVP CLI |
| Lock-in piattaforma | Dipendenza da GitHub | Git-first, exporter modulari |
| Output AI incoerente | Sintesi o task poco affidabili | Schema validation, checklist, human review |
| Security MCP/agenti | Tool AI possono eseguire azioni rischiose | MCP solo dopo sandbox e permission model |

---

## 11. Roadmap derivata dal benchmark

### Fase 1 — Foundation CLI

- Core domain model.
- File structure `.p2p/`.
- Proposal lifecycle.
- Contribution/comment storage.
- Digest/clarify/synthesize come prompt generator.
- Export Markdown.

### Fase 2 — AI Adapter minimale

- Adapter `generic`.
- Adapter `codex-cli` opzionale.
- Adapter `claude-cli` opzionale.
- Adapter `ollama/openai-compatible` opzionale.

### Fase 3 — Export software

- Export OpenSpec.
- Export Spec Kit.
- Mapping task/action verso target esterni.

### Fase 4 — Governance avanzata

- Relevance criteria.
- Comment ranking.
- Decision rules.
- Voting/approval models.
- Decision log.

### Fase 5 — Web/API

- API server.
- Web app.
- Utenti/progetti.
- Commenti collaborativi.
- BYOK AI.

### Fase 6 — Agent integration avanzata

- MCP server.
- Agent skills.
- Dashboard multi-agent.
- Sandbox execution.

---

## 12. Conclusione

Il landscape conferma che P2P Engine ha uno spazio progettuale autonomo.

Gli strumenti esistenti sono molto utili, ma coprono principalmente:

```text
specifiche software
coding assistant
agent orchestration
code review
```

P2P Engine vuole coprire il passaggio precedente:

```text
discussione collaborativa
→ proposta strutturata
→ confronto alternative
→ governance
→ decisione
→ piano
→ task/action
→ export
```

Questa posizione consente a P2P Engine di integrarsi con Spec Kit, OpenSpec, Codex, Claude, Aider, issue tracker e strumenti documentali, senza dipendere da uno solo di essi.

La direzione consigliata resta:

```text
Core Engine
→ CLI Git-native
→ AI prompt/adapter layer
→ exporter
→ governance avanzata
→ web app
→ MCP/agent integration
```

---

## 13. Riferimenti consultati

- GitHub Spec Kit: https://github.com/github/spec-kit
- GitHub Blog — Spec-driven development with AI: https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/
- OpenSpec: https://github.com/Fission-AI/OpenSpec
- Kiro: https://kiro.dev/
- Kiro — Introducing Kiro: https://kiro.dev/blog/introducing-kiro/
- BMAD Method: https://github.com/bmad-code-org/BMAD-METHOD
- BMAD Docs: https://docs.bmad-method.org/
- Aider: https://aider.chat/
- Maestro: https://github.com/RunMaestro/Maestro
- Gerrit Code Review: https://www.gerritcodereview.com/
- Model Context Protocol: https://modelcontextprotocol.io/docs/getting-started/intro
