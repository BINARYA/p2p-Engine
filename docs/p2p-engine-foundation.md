# P2P Engine — Project Foundation

**Versione:** 0.3  
**Data:** 2026-05-19  
**Nome provvisorio:** P2P Engine  
**Significato operativo di P2P:** Proposal-to-Plan Engine  
**Stato del documento:** base progettuale iniziale, da usare come riferimento per i prossimi step di analisi e sviluppo.

---

## 1. Sintesi del progetto

P2P Engine è un sistema pensato per trasformare discussioni collaborative, idee sparse, proposte alternative, principi architetturali, obiettivi di business e suggestioni strategiche in **proposal strutturate**, **decisioni governate**, **specifiche progettuali**, **piani esecutivi**, **task** e **azioni operative**.

L'obiettivo non è soltanto generare codice, ma creare un processo più ampio per passare da una discussione non strutturata a un piano realizzabile.

Il codice può essere uno degli output, ma non l'unico. Una proposal può generare attività software, commerciali, marketing, operative, documentali, di ricerca o di governance.

Il sistema deve quindi essere più generale rispetto a un normale tool di spec-driven development software. Strumenti come **Spec Kit**, **OpenSpec**, GitHub Issues, GitLab Issues, Jira, Linear o altri devono essere considerati **target downstream**, non il centro del modello.

La direzione architetturale principale è:

```text
Discussione collaborativa
→ Proposal strutturata
→ Decisione governata
→ Specifica progettuale
→ Execution plan
→ Task e action
→ Export verso strumenti esterni
→ eventuale implementazione software/documentale/operativa
```

---

## 2. Problema che P2P Engine vuole risolvere

In un progetto reale, raramente una nuova direzione nasce da una singola persona o da un requisito perfettamente definito.

Più spesso succede che:

- un utente proponga una feature;
- un altro utente proponga una variante;
- un altro introduca un principio architetturale;
- un altro ancora chiarisca un obiettivo commerciale;
- qualcuno aggiunga una suggestione strategica;
- il team discuta con commenti, obiezioni e integrazioni;
- emergano trade-off, conflitti, rischi e alternative;
- solo dopo una fase di convergenza si possa generare una vera specifica progettuale.

Oggi molti strumenti partono troppo tardi nel processo: partono dalla issue, dalla user story, dalla specifica software o direttamente dal codice.

P2P Engine vuole coprire la fase precedente:

```text
Discussione collaborativa
→ contributi eterogenei
→ sintesi AI
→ proposal strutturata
→ confronto tra alternative
→ governance decisionale
→ specifica progettuale
→ piano
→ task
→ azioni
→ eventuale implementazione
```

---

## 3. Visione

P2P Engine deve diventare un sistema per **governare il passaggio dalla conversazione alla realizzazione**.

La visione è costruire un motore che aiuti team tecnici e non tecnici a:

1. raccogliere contributi da più persone;
2. classificare le idee in modo strutturato;
3. sintetizzare proposte coerenti;
4. confrontare alternative;
5. evidenziare differenze, trade-off, conflitti e rischi;
6. valorizzare i commenti del team ordinandoli per rilevanza;
7. applicare regole di governance per accettare, rifiutare, fondere o rimandare una proposal;
8. trasformare le decisioni approvate in specifiche progettuali;
9. generare piani esecutivi, task e action;
10. distinguere chiaramente cosa richiede codice e cosa invece richiede documentazione, marketing, commerciale, operations o ricerca.

P2P Engine deve essere una **interfaccia metodologica tra persone, Git e agenti AI**.

---

## 4. Principio fondamentale

Il centro del sistema non deve essere la feature, ma la **proposal**.

Una proposal rappresenta una possibile decisione progettuale, strategica o operativa. Può riguardare software, business, marketing, architettura, governance o processi.

Una proposal può nascere da:

- feature request;
- variante di una feature;
- principio architetturale;
- obiettivo di business;
- suggestione di orientamento;
- rischio;
- problema operativo;
- esigenza commerciale;
- esigenza marketing;
- vincolo normativo;
- idea di miglioramento;
- proposta di refactoring;
- proposta di processo;
- decisione di governance.

La proposal, se accettata, può produrre uno o più output esecutivi.

---

## 5. Obiettivi principali

### 5.1 Trasformare discussioni in artefatti strutturati

Il sistema deve prendere input disordinati e convertirli in artefatti leggibili, versionabili e revisionabili.

Esempi di input:

- commenti testuali;
- messaggi di discussione;
- note di riunione;
- proposte alternative;
- obiezioni;
- decisioni preliminari;
- criteri di priorità;
- contributi tecnici e non tecnici.

Esempi di output:

- proposal strutturata;
- confronto tra alternative;
- sintesi commenti;
- decision log;
- specifica progettuale;
- execution plan;
- task list;
- action list;
- export verso strumenti esterni.

### 5.2 Supportare collaborazione multiutente

Il sistema deve essere pensato per team, non solo per un singolo sviluppatore.

Deve consentire a più persone di contribuire, commentare, proporre varianti, formulare obiezioni, votare o partecipare alla decisione.

### 5.3 Usare l'AI come facilitatore, non come decisore

L'AI deve aiutare a:

- sintetizzare;
- classificare;
- trovare conflitti;
- evidenziare trade-off;
- generare domande di chiarimento;
- confrontare alternative;
- ordinare commenti per rilevanza;
- produrre bozze di proposal, specifiche e piani;
- generare task e action coerenti con la decisione approvata.

L'AI non deve essere il decisore finale.

La decisione deve rimanere governata da regole umane, esplicite e tracciabili.

### 5.4 Restare platform-agnostic

P2P Engine non deve dipendere da una singola piattaforma web di hosting codice.

Git può essere il fondamento per versionamento, auditabilità e portabilità, ma il sistema deve poter funzionare con:

- repository locali;
- GitHub;
- GitLab;
- Gitea;
- Bitbucket;
- repository self-hosted;
- eventuali sistemi documentali o gestionali futuri.

### 5.5 Produrre output esportabili

P2P Engine deve produrre artefatti neutri e poi consentire export verso strumenti diversi.

Possibili target:

- OpenSpec;
- Spec Kit;
- Markdown documentale;
- GitHub Issues;
- GitLab Issues;
- Gitea Issues;
- Jira;
- Linear;
- sistemi interni;
- document generator;
- agenti AI di implementazione;
- strumenti di project management.

### 5.6 Integrare AI diverse senza lock-in

P2P Engine deve poter lavorare con differenti strumenti AI:

- Codex;
- Claude;
- Llama locale;
- Ollama;
- OpenAI API;
- Anthropic API;
- provider OpenAI-compatible;
- LiteLLM o gateway equivalenti;
- futuri agenti compatibili con MCP.

La strategia non deve essere “scegliere un modello”, ma creare un **AI Adapter Layer**.

---

## 6. Cosa P2P Engine non deve essere, almeno inizialmente

P2P Engine non deve nascere come:

- clone di Jira;
- clone di GitHub Issues;
- clone di Notion;
- clone di Confluence;
- editor collaborativo real-time;
- solo generatore di codice;
- fork diretto di Spec Kit;
- strumento legato esclusivamente a GitHub;
- sistema che decide automaticamente al posto del team;
- servizio SaaS AI-costoso già nella prima versione.

La prima versione deve essere un motore leggero, Git-native, AI-assisted e orientato alla trasformazione di discussioni in piani esecutivi.

---

## 7. Entità concettuali principali

### 7.1 Contribution

Un contributo atomico fornito da un utente.

Può essere:

- feature;
- variante;
- obiettivo;
- principio;
- vincolo;
- rischio;
- obiezione;
- suggerimento;
- commento;
- domanda;
- evidenza;
- nota strategica.

### 7.2 Discussion

Una discussione raccoglie contributi relativi a un tema comune.

La discussione può essere non strutturata all'inizio, ma deve poter essere sintetizzata dall'AI.

### 7.3 Proposal

Una proposta strutturata che descrive una possibile decisione da prendere.

Deve contenere almeno:

- titolo;
- problema;
- contesto;
- obiettivi;
- proposta;
- alternative;
- impatti;
- rischi;
- domande aperte;
- criteri di accettazione;
- stato;
- decisione finale.

### 7.4 Alternative

Una variante o soluzione concorrente rispetto alla proposal principale.

Le alternative devono poter essere confrontate dall'AI rispetto a criteri espliciti.

### 7.5 Comment

Un commento associato a una proposal, a una sezione della proposal, a una decisione o a una task.

L'AI può:

- raggruppare commenti simili;
- evidenziare commenti bloccanti;
- ordinare per rilevanza;
- distinguere obiezioni, suggerimenti, rischi e chiarimenti.

### 7.6 Exploration

La fase di Exploration è il momento in cui P2P Engine interroga un'idea grezza prima di trasformarla in proposal.

Non serve a riassumere, ma a scoprire:

- implicazioni;
- alternative;
- rischi;
- assunzioni;
- decisioni nascoste;
- domande aperte;
- possibili scope;
- confini tra domini di esecuzione.

La conversazione può avvenire nella CLI, in un agente AI tramite skill o in futuro nella web app, ma gli output validi devono essere salvati negli artefatti P2P versionati.

Artefatti principali:

```text
exploration.md
findings.md
alternatives.md
open-questions.md
risks.md
assumptions.md
suggested-scope.md
```

`findings.md` può contenere elementi strutturati riutilizzabili:

```yaml
findings:
  - id: F001
    type: hidden_decision
    title: AI integration strategy
    impact: high
    related_to:
      - PROP-001
```

### 7.7 AI Digest

Una sintesi generata dall'AI a partire da contributi, commenti e contesto.

Non è una decisione, ma una rappresentazione ordinata della discussione.

### 7.8 Decision

La decisione formale sulla proposal.

Può essere:

- accepted;
- accepted_with_changes;
- rejected;
- deferred;
- split;
- merged_into_other;
- superseded.

### 7.9 Specification

La specifica progettuale derivata da una proposal accettata.

Può essere software o non software.

### 7.10 Execution Plan

Il piano operativo per realizzare quanto deciso.

Può contenere più workstream.

### 7.11 Workstream

Una linea di lavoro autonoma o semi-autonoma.

Esempi:

- software;
- documentazione;
- marketing;
- commerciale;
- operations;
- governance;
- ricerca.

### 7.12 Task

Una attività assegnabile.

Deve avere:

- id;
- titolo;
- descrizione;
- workstream;
- tipo;
- stato;
- priorità;
- dipendenze;
- deliverable;
- evidenza richiesta;
- action collegate.

### 7.13 Action

Una sotto-attività più fine di una task.

Esempio:

```yaml
task: T002 - Implementare p2p init
actions:
  - A001 - Creare directory .p2p
  - A002 - Generare project.yml
  - A003 - Generare template governance
  - A004 - Supportare opzione --agent
```

### 7.14 Deliverable

Il risultato prodotto da una task o da un workstream.

Può essere:

- codice;
- documento;
- procedura;
- landing page;
- campagna;
- analisi;
- contratto;
- configurazione;
- export verso altro strumento.

### 7.15 Evidence

La prova che una task o action è stata completata.

Esempi:

- commit;
- merge request;
- file prodotto;
- documento approvato;
- URL pubblicato;
- screenshot;
- test automatici;
- decision log;
- approvazione umana.

---

## 8. Workflow generale

Il workflow ideale è:

```text
1. Intake di una nuova idea o contributo
2. Triage rispetto alle proposal esistenti
3. Raccolta contributi
4. Classificazione AI dei contributi
5. Raggruppamento per tema
6. Exploration della proposta o dell'idea grezza
7. Generazione o aggiornamento di una o più proposal
8. Confronto tra proposal o alternative
9. Discussione commentata
10. Eventuale nuova exploration quando emergono nuovi elementi
11. Sintesi AI dei commenti
12. Ordinamento dei commenti per rilevanza
13. Verifica criteri di governance
14. Decisione umana
15. Proposal accettata
16. Generazione specifica progettuale
17. Generazione execution plan
18. Generazione workstream
19. Generazione task
20. Generazione action
21. Tracciamento deliverable
22. Eventuale export verso strumenti esterni
23. Eventuale implementazione codice/documenti/campagne/processi
```

`triage` valuta se una nuova idea è già coperta, parzialmente coperta, duplicata, in conflitto o da trasformare in nuova proposal.

`explore` viene prima di `synthesize` e normalmente prima di `clarify` o `digest`, ma può essere rilanciato più volte durante la discussione.

Esempio:

```text
idea grezza
→ triage rispetto alle proposal esistenti
→ explore
→ contributi del team
→ digest
→ nuova explore
→ clarify
→ synthesize
```

Regola architetturale:

```text
CLI / engine = sorgente di verità
Skill agente = guida conversazionale
Filesystem/Git = memoria e audit
```

---

## 9. Stati della proposal

Una proposal deve attraversare stati espliciti.

Stati iniziali:

```text
draft
under_discussion
needs_clarification
ready_for_review
ready_for_decision
accepted
accepted_with_changes
rejected
deferred
split
merged_into_other
superseded
archived
```

Transizioni operative tipiche:

```text
draft → under_discussion
under_discussion → needs_clarification
needs_clarification → under_discussion
under_discussion → ready_for_review
ready_for_review → ready_for_decision
ready_for_decision → accepted
ready_for_decision → rejected
ready_for_decision → deferred
accepted → planned
planned → tasks_generated
```

La CLI deve mostrare sempre lo stato corrente e suggerire il prossimo comando utile.

Esempio:

```text
Status:
  draft → ready_for_review

Next suggested command:
  p2p decision request PROP-001
```

---

## 10. Governance

P2P Engine deve introdurre un sistema di governance configurabile.

La governance serve a decidere se una proposal deve essere:

- accettata;
- accettata con modifiche;
- rifiutata;
- rimandata;
- divisa in più proposal;
- fusa con un'altra proposal;
- convertita in principio;
- convertita in task;
- convertita in research item.

Modelli possibili:

| Modello | Uso tipico |
|---|---|
| Decisione del responsabile | Team piccolo, alta velocità |
| Lazy consensus | Community/open source |
| Voto semplice | Decisioni leggere |
| Voto pesato per ruolo | Team con responsabilità diverse |
| Consent-based governance | Si approva se non ci sono obiezioni bloccanti |
| RFC formale | Decisioni architetturali importanti |
| Steering committee | Decisioni strategiche o commerciali ad alto impatto |

Esempio di configurazione:

```yaml
governance:
  mode: consent
  required_roles:
    - product_owner
    - tech_lead
  blocking_objections_allowed: true
```

### 10.1 Governance MVP

Per i primi step, la governance non deve ancora implementare un sistema completo di privilegi applicativi.

La distinzione fondamentale è:

```text
governance metodologica
  regole, ruoli, voti, decisioni, precedenti

governance tecnica
  Git, branch, commit, merge, PR, permessi esterni
```

Modelli iniziali consigliati:

```yaml
governance:
  mode: owner_decides
```

```yaml
governance:
  mode: open_consensus
```

```yaml
governance:
  mode: exclusive_vote
```

Significato operativo:

| Mode | Uso |
|---|---|
| `owner_decides` | Bootstrap, team piccolo, decisioni rapide |
| `open_consensus` | Community, proposte non esclusive, obiezioni bloccanti |
| `exclusive_vote` | Alternative contrapposte dove una sola opzione deve vincere |

Artefatti di governance:

```text
.p2p/governance/
  governance.yml
  roles.yml
  decision-precedents.yml

.p2p/proposals/<proposal>/
  alternatives.md
  swot-analysis.md
  votes.yml
  decision.md
```

Quando due o più alternative sono contrapposte, l'AI può generare una SWOT analysis per agevolare la scelta:

```text
Strengths
Weaknesses
Opportunities
Threats
```

La SWOT è supporto alla decisione, non decisione.

Git fornisce auditabilità:

```text
proposal branch
→ modifica artefatti governance/proposal
→ commit
→ decision.md + votes.yml + swot-analysis.md
→ merge su main = decisione applicata
```

Git non sostituisce un sistema di permessi applicativi. In futuro GitHub, GitLab o Gitea possono aggiungere branch protection, CODEOWNERS, required approvals, signed commits e team permissions.

Comandi MVP:

```bash
p2p governance init --mode owner_decides
p2p governance status

p2p swot prompt PROP-008

p2p vote record PROP-008 \
  --choice "ALT-A" \
  --reason "Mantiene semplice la governance MVP." \
  --voter "local" \
  --role "owner"

p2p vote status PROP-008

p2p precedent record PROP-008 \
  --title "La governance MVP e audit-only" \
  --reason "I privilegi reali restano nel sistema Git fino a necessita piu mature."
```

---

## 11. Criteri di rilevanza dei commenti

L'AI deve poter ordinare e valorizzare i commenti sulla base di criteri espliciti.

Possibili criteri:

```yaml
relevance_criteria:
  - strategic_alignment
  - user_value
  - risk_reduction
  - feasibility
  - novelty
  - evidence_quality
  - decision_impact
  - urgency
  - architectural_impact
  - cost_impact
  - security_impact
  - legal_or_compliance_impact
```

L'AI può classificare i commenti come:

- blocking objection;
- major concern;
- minor concern;
- suggestion;
- clarification;
- evidence;
- duplicate;
- out of scope.

---

## 12. Distinzione tra codice e non-codice

Ogni task deve dichiarare il proprio dominio di esecuzione.

Esempi:

```yaml
execution_domain: software
implementation_target: openspec
```

```yaml
execution_domain: marketing
implementation_target: document
```

```yaml
execution_domain: commercial
implementation_target: manual
```

Domini possibili:

```text
software
documentation
marketing
commercial
operations
governance
research
legal
quality
mixed
```

Target possibili:

```text
code
openspec
speckit
markdown
issue_tracker
document
campaign
manual
crm
none
```

Questa distinzione è essenziale perché P2P Engine non deve forzare ogni decisione dentro un flusso di sviluppo software.

---

## 13. Strategia Git-native

Git deve essere usato come layer di versionamento, audit e portabilità.

P2P Engine deve poter funzionare anche senza GitHub.

### 13.1 Modello managed Git sotto al cofano

P2P Engine non identifica rigidamente ogni proposal con un branch.

```text
Proposal != Branch
```

L'utente non deve ragionare normalmente in termini di branch, commit, merge o tag.

```text
Utente vede:
  proposal → choice → decision → change → task

P2P Engine gestisce internamente:
  file → commit → branch → merge → tag
```

Definizioni:

```text
Proposal
  unita decisionale versionata in .p2p/proposals/

Choice
  scelta aperta tra alternative

Decision
  scelta registrata dalla governance

Change Set
  pacchetto operativo che raggruppa proposal accettate, decisioni, piano e task

Git Adapter
  componente interno che traduce operazioni P2P in operazioni Git

Branch
  spazio Git interno usato quando la policy richiede isolamento o review

Commit
  checkpoint interno di audit

Merge
  evento Git che rende ufficiale il change set nello stato progetto

Tag
  riferimento interno opzionale per decisioni, change o release
```

Workflow:

```text
idea / contributo
→ proposal
→ exploration
→ impact/conflict analysis
→ choices aperte
→ decisione
→ change set
→ operazioni Git interne quando la policy lo richiede
→ .p2p/project refresh
```

### 13.2 Policy Git gestita

```yaml
git_policy:
  mode: managed
  expose_git_details: false

  proposal_branching:
    default: auto
    create_branch_when:
      - complex_proposal
      - divergent_alternative
      - formal_review_required
      - multi_actor_edit

  change_branching:
    default: auto
    create_branch_when:
      - source_code_changes
      - governance_changes
      - schema_or_template_changes
      - public_cli_behavior_changes
      - high_impact
      - mutually_exclusive_alternative

  commits:
    auto_commit: false
    message_style: conventional
    include_actor: true

  tags:
    create_for_decisions: false
    create_for_changes: false

  debug:
    show_internal_operations_with_verbose: true
```

### 13.3 Regola generale

Di default, una proposal crea artefatti in `.p2p/proposals/`.

La CLI puo creare branch/commit/tag internamente se la policy lo prevede, ma non lo espone come concetto primario.

```bash
p2p proposal create "Voglio predisporre la CLI"
```

I change set sono visibili:

```bash
p2p change create --from PROP-001
p2p change policy CHANGE-001
```

I dettagli Git sono visibili solo in modalita avanzata:

```bash
p2p status --verbose
p2p doctor
```

Questa separazione riduce l'alea per l'utente: non decide manualmente se creare branch, ma lavora su concetti P2P. La policy interna decide le operazioni Git.

### 13.4 Struttura change set

```text
.p2p/changes/
  CHANGE-001-cli-foundation/
    change.md
    included-proposals.yml
    included-decisions.yml
    impact-map.yml
    git-policy.yml
    execution-plan.md
    tasks.yml
```

I branch possono essere chiusi o rimossi, ma lo storico decisionale deve restare negli artefatti P2P.

### 13.5 Git come source of truth documentale

Git è ottimo per:

- storia delle decisioni;
- diff tra proposal;
- branch alternativi;
- merge di specifiche approvate;
- tracciabilità;
- audit;
- portabilità;
- lavoro offline.

Git non è sufficiente da solo per:

- commenti conversazionali ricchi;
- notifiche;
- permessi applicativi;
- dashboard;
- assegnazioni task;
- esperienza utente non tecnica.

Per questo la prima versione sarà CLI/Git-native, mentre la web app potrà arrivare dopo.

---

## 14. Strategia AI-first senza lock-in

P2P Engine deve essere progettato come orchestratore di AI, non come AI proprietaria.

Il sistema deve supportare tre modalità principali.

### 14.1 Modalità A — P2P Engine chiama l'AI

L'utente usa la CLI P2P e sceglie un adapter AI:

```bash
p2p digest PROP-001 --ai codex
p2p plan PROP-001 --ai claude
p2p tasks PROP-001 --ai ollama
```

P2P Engine:

1. legge i file del progetto;
2. costruisce il prompt;
3. invoca l'AI scelta;
4. riceve la risposta;
5. valida l'output;
6. salva gli artefatti.

### 14.2 Modalità B — L'AI usa P2P Engine

L'utente lavora dentro Codex, Claude o un altro agente e chiede:

```text
Usa P2P Engine per generare il piano della proposal PROP-001.
```

L'agente usa i comandi P2P, le skill o in futuro un server MCP.

### 14.3 Modalità C — Agent-files

P2P Engine prepara file, prompt, skill e istruzioni per gli agenti, senza chiamare direttamente un modello.

Esempio:

```bash
p2p init "P2P Engine" --agent codex
p2p init "P2P Engine" --agent claude
p2p init "P2P Engine" --agent generic
```

Possibili file generati:

```text
.p2p/prompts/
.p2p/templates/
.p2p/workflows/
.codex/skills/p2p-engine/SKILL.md
CLAUDE.md
```

Questa modalità è utile perché:

- riduce i costi iniziali;
- non obbliga a usare API centralizzate;
- lascia all'utente la scelta del proprio strumento AI;
- permette uso locale o aziendale;
- riduce il lock-in verso un provider.

### 14.4 Progressione consigliata dell'integrazione AI

```text
Fase 1: Core e CLI senza AI diretta
Fase 2: Prompt generator
Fase 3: Agent-files per Codex/Claude/generic
Fase 4: Adapter Codex/Claude/Ollama/OpenAI-compatible
Fase 5: MCP server
Fase 6: Web app con BYOK o provider configurabile
Fase 7: eventuale AI gestita dal servizio con billing/quote
```

---

## 15. CLI-first, web app later

La sequenza di sviluppo raccomandata è:

```text
1. P2P Core Engine
2. CLI Git-native
3. AI adapter / prompt generator
4. Exporter verso OpenSpec, Spec Kit, Markdown
5. API server
6. Web app
```

La CLI è il primo prodotto minimo reale.

La web app deve arrivare dopo, quando:

- il modello dati è stabile;
- il workflow proposal → decision → plan → tasks è validato;
- gli exporter funzionano;
- l'integrazione AI è sufficientemente chiara;
- sono stati affrontati i problemi di utenti, permessi, costi AI, quote, sicurezza e sandbox.

La web app deve essere un client del motore, non il motore stesso.

---

## 16. UX della CLI

La CLI non deve essere solo una lista di comandi. Deve essere una guida di processo.

Deve:

- creare struttura;
- fare domande guidate;
- proporre opzioni;
- salvare contributi e decisioni;
- invocare o preparare l'AI;
- validare output AI;
- mostrare stato corrente;
- suggerire il prossimo comando.

Comandi iniziali proposti:

```bash
p2p init
p2p proposal create
p2p contribution add
p2p comment add
p2p explore
p2p digest
p2p clarify
p2p synthesize
p2p compare
p2p rank-comments
p2p decision request
p2p plan
p2p tasks
p2p export
p2p status
```

### 16.1 Comandi AI-oriented

```bash
p2p explore PROP-001 --ai codex
p2p digest PROP-001 --ai codex
p2p clarify PROP-001 --ai codex
p2p synthesize PROP-001 --ai codex
p2p compare PROP-001 --ai claude
p2p plan PROP-001 --ai ollama
p2p tasks PROP-001 --ai openai-compatible
```

### 16.2 Comandi prompt-only

```bash
p2p explore prompt PROP-001
p2p explore import PROP-001 exploration-output.md
p2p explore status PROP-001
p2p digest prompt PROP-001
p2p clarify prompt PROP-001
p2p clarify import PROP-001 clarification-output.md
p2p synthesize prompt PROP-001
p2p synthesize import PROP-001 proposal-output.md
p2p plan prompt PROP-001
p2p plan import PROP-001 plan-output.md
p2p tasks prompt PROP-001
p2p tasks import PROP-001 tasks-output.yml
```

Questi comandi generano prompt riutilizzabili manualmente e importano gli output prodotti da AI, agenti esterni o dall'utente.

---

## 17. Distinzione tra triage, explore, digest, clarify e synthesize

Il workflow AI deve distinguere chiaramente cinque fasi.

### 17.1 `p2p proposal triage`

Valuta una nuova idea rispetto alle proposal esistenti.

Serve a capire se l'idea deve:

- creare una nuova proposal;
- aggiornare una proposal esistente;
- diventare un contributo;
- essere fusa con una proposal;
- essere divisa;
- essere rimandata;
- essere marcata come duplicato.

Output tipico:

- overlap-analysis.md;
- related-proposals.yml;
- suggested action;
- next P2P command.

### 17.2 `p2p explore`

Esplora una proposta o idea grezza per scoprire implicazioni, alternative, assunzioni, rischi, decisioni nascoste e domande aperte.

Non produce una decisione e non sostituisce la proposal finale.

Output tipico:

- exploration.md;
- findings.md;
- alternatives.md;
- open-questions.md;
- risks.md;
- assumptions.md;
- suggested-scope.md.

Comandi prompt-only iniziali:

```bash
p2p explore prompt PROP-001
p2p explore import PROP-001 exploration-output.md
p2p explore status PROP-001
```

### 17.3 `p2p digest`

Produce una sintesi della discussione.

Output tipico:

- summary;
- main objectives;
- key constraints;
- risks;
- conflicts;
- open questions;
- suggested next steps.

### 17.4 `p2p clarify`

Genera domande e raccoglie risposte.

Esempio:

```text
Q1. La CLI deve essere completamente locale o prevedere già una futura API server?
Q2. L'integrazione AI iniziale deve invocare Codex o solo generare prompt?
Q3. Le proposal devono sempre creare un branch Git?
Q4. I task devono supportare sotto-task/action?
```

Le risposte vengono salvate in:

```text
.p2p/proposals/PROP-001-cli-foundation/clarifications.md
```

### 17.5 `p2p synthesize`

Produce una proposal strutturata pronta per review.

Input:

- proposal grezza;
- exploration;
- contributi;
- commenti;
- chiarimenti;
- AI digest;
- governance rules;
- project constitution.

Output:

```text
proposal.md
```

Stato tipico:

```text
draft → ready_for_review
```

---

## 18. Validazione degli output AI

P2P Engine non deve salvare passivamente qualunque output prodotto dall'AI.

Ogni comando AI-assisted deve prevedere validazione.

Esempio di output terminale:

```text
AI response received.

Validated sections:
  ✓ Summary
  ✓ Main objectives
  ✓ Key constraints
  ✓ Open questions
  ✓ Possible conflicts
  ✓ Suggested next steps

Saved:
  .p2p/proposals/PROP-001-cli-foundation/ai-digest.md
```

La validazione può riguardare:

- presenza delle sezioni obbligatorie;
- schema YAML/JSON valido;
- coerenza tra task e proposal;
- presenza di action per ogni task;
- assenza di decisioni non autorizzate;
- rispetto della governance;
- distinzione corretta tra software e non-software;
- riferimenti a proposal, task e contribution esistenti.

---

## 19. Convenzione file: Markdown + YAML

P2P Engine deve usare due tipi principali di artefatti.

### 19.1 Markdown per documenti leggibili

Esempi:

```text
proposal.md
decision.md
execution-plan.md
comparison.md
ai-digest.md
clarifications.md
exploration.md
alternatives.md
open-questions.md
risks.md
assumptions.md
suggested-scope.md
```

### 19.2 YAML/JSON per dati strutturati

Esempi:

```text
project.yml
contributions.yml
comments.yml
tasks.yml
workstreams.yml
governance.yml
```

Questa distinzione permette sia lettura umana sia automazione.

---

## 20. Struttura file proposta

Struttura iniziale:

```text
.p2p/
  project.yml
  governance/
    constitution.md
    decision-rules.md
    relevance-criteria.yml
  templates/
    proposal-template.md
    decision-template.md
    execution-plan-template.md
    tasks-template.yml
  prompts/
  workflows/
  proposals/
    PROP-001-cli-foundation/
      proposal.md
      contributions.yml
      comments.yml
      exploration.md
      findings.md
      alternatives.md
      open-questions.md
      risks.md
      assumptions.md
      suggested-scope.md
      ai-digest.md
      clarifications.md
      comparison.md
      decision.md
      execution-plan.md
      tasks.yml
      tasks.md
      exports/
        markdown/
        openspec/
        speckit/
```

Eventuali file agent-specific:

```text
.codex/
  skills/
    p2p-engine/
      SKILL.md

CLAUDE.md
```

La skill Codex locale deve trattare la CLI P2P come sorgente operativa e gli artefatti `.p2p/` come memoria versionata. La skill guida l'interlocuzione, ma non sostituisce il motore.

---

## 21. Scenario operativo iniziale: implementare P2P Engine con P2P Engine

Il primo caso di utilizzo deve essere il dogfooding: usare P2P Engine per progettare P2P Engine.

### 21.1 Avvio progetto

```bash
mkdir p2p-engine
cd p2p-engine
git init
p2p init "P2P Engine" --agent codex
```

Output atteso:

```text
P2P Engine project initialized.

Project:
  name: P2P Engine
  id: p2p-engine

Git:
  repository initialized
  default branch: main

AI integration:
  agent: codex
  mode: agent-files

Created:
  .p2p/project.yml
  .p2p/governance/constitution.md
  .p2p/governance/decision-rules.md
  .p2p/templates/proposal-template.md
  .p2p/templates/decision-template.md
  .p2p/templates/execution-plan-template.md
  .p2p/templates/tasks-template.yml
  .p2p/prompts/
  .codex/skills/p2p-engine/SKILL.md

Next step:
  p2p proposal create "Voglio predisporre la CLI"
```

### 21.2 Creazione prima proposal

```bash
p2p proposal create "Voglio predisporre la CLI"
```

Wizard atteso:

```text
Creating new proposal.

Title:
  Voglio predisporre la CLI

Select proposal type:
  1. Feature
  2. Architectural principle
  3. Objective
  4. Research topic
  5. Operational process
  6. Marketing/commercial activity

> 1

Primary execution domain:
  1. Software
  2. Documentation
  3. Marketing
  4. Commercial
  5. Operations
  6. Governance
  7. Mixed

> 1

Should P2P Engine create a Git branch for this proposal?
  Y/n

> Y
```

Output atteso:

```text
Created proposal:

  id: PROP-001
  slug: cli-foundation
  branch: proposal/PROP-001-cli-foundation
  status: draft
  domain: software

Created files:

  .p2p/proposals/PROP-001-cli-foundation/proposal.md
  .p2p/proposals/PROP-001-cli-foundation/contributions.yml
  .p2p/proposals/PROP-001-cli-foundation/comments.yml
  .p2p/proposals/PROP-001-cli-foundation/ai-digest.md
  .p2p/proposals/PROP-001-cli-foundation/comparison.md
  .p2p/proposals/PROP-001-cli-foundation/decision.md
  .p2p/proposals/PROP-001-cli-foundation/execution-plan.md
  .p2p/proposals/PROP-001-cli-foundation/tasks.yml

Current branch:
  proposal/PROP-001-cli-foundation

Next suggested command:
  p2p contribution add PROP-001
```

### 21.3 Aggiunta contributo

```bash
p2p contribution add PROP-001
```

Esempio:

```text
Contribution type:
  1. Feature request
  2. Alternative proposal
  3. Architectural principle
  4. Objective
  5. Constraint
  6. Risk
  7. Suggestion
  8. Objection

> 1

Write your contribution:
> Voglio una CLI che permetta di inizializzare un progetto, creare proposal, aggiungere contributi, generare sintesi AI, decidere una proposal, produrre piano e task.

Relevance hint:
  1. Low
  2. Medium
  3. High
  4. Blocking

> 3
```

Output atteso:

```text
Contribution added.

  id: C001
  proposal: PROP-001
  type: feature_request
  relevance_hint: high

Saved to:
  .p2p/proposals/PROP-001-cli-foundation/contributions.yml

Next suggested command:
  p2p clarify PROP-001
```

### 21.4 Esempio di principio architetturale

```bash
p2p contribution add PROP-001
```

Input:

```text
Contribution type:
> 3

Write your contribution:
> La CLI deve essere Git-native e non dipendere da GitHub. Deve funzionare anche con GitLab, Gitea o repository locale.

Relevance hint:
> 4
```

Output atteso:

```text
Contribution added.

  id: C002
  type: architectural_principle
  relevance_hint: blocking

Detected impact:
  - platform independence
  - storage model
  - branch strategy
  - export strategy

Next suggested command:
  p2p digest PROP-001 --ai codex
```

### 21.5 Digest AI

```bash
p2p digest PROP-001 --ai codex
```

Output atteso:

```text
Generating AI digest for PROP-001 using codex...

Context loaded:
  proposal.md
  contributions.yml
  constitution.md
  decision-rules.md

Prompt generated:
  .p2p/prompts/PROP-001/digest.prompt.md

Running:
  codex exec <digest.prompt.md>

AI response received.

Validated sections:
  ✓ Summary
  ✓ Main objectives
  ✓ Key constraints
  ✓ Open questions
  ✓ Possible conflicts
  ✓ Suggested next steps

Saved:
  .p2p/proposals/PROP-001-cli-foundation/ai-digest.md
```

### 21.6 Chiarimenti guidati

```bash
p2p clarify PROP-001 --ai codex
```

Esempio di domande:

```text
Q1. La prima CLI deve essere completamente locale o deve prevedere già una futura API server?
> Locale, ma progettata per poter avere in futuro un API server.

Q2. L'integrazione AI iniziale deve invocare direttamente Codex o solo generare prompt?
> Per MVP generiamo prompt e supportiamo Codex exec come opzione.

Q3. Le proposal devono sempre creare un branch Git?
> Di default sì, ma deve esistere un flag --no-branch.

Q4. I task devono supportare sotto-task?
> Sì, li chiameremo actions.

Q5. Il formato principale dei dati deve essere Markdown o YAML?
> Markdown per documenti leggibili, YAML per dati strutturati.

Q6. La CLI deve già esportare verso OpenSpec o Spec Kit?
> Sì, almeno export OpenSpec e Markdown; Spec Kit può arrivare subito dopo.
```

Output atteso:

```text
Clarifications saved.

Updated:
  .p2p/proposals/PROP-001-cli-foundation/proposal.md
  .p2p/proposals/PROP-001-cli-foundation/clarifications.md

Next suggested command:
  p2p synthesize PROP-001 --ai codex
```

### 21.7 Sintesi proposal strutturata

```bash
p2p synthesize PROP-001 --ai codex
```

Output atteso:

```text
Synthesizing structured proposal...

Input:
  proposal.md
  contributions.yml
  clarifications.md
  ai-digest.md

Saved:
  .p2p/proposals/PROP-001-cli-foundation/proposal.md

Proposal status:
  draft → ready_for_review

Next suggested command:
  p2p decision request PROP-001
```

### 21.8 Decisione

```bash
p2p decision request PROP-001
```

Output atteso:

```text
Decision required for PROP-001.

Current status:
  ready_for_review

Available decisions:
  1. accept
  2. accept_with_changes
  3. reject
  4. defer
  5. split
  6. merge_into_other

> 1

Decision reason:
> La CLI è il primo passo necessario per validare P2P Engine senza introdurre complessità web.

Record decision? Y/n
> Y
```

Risultato:

```text
Decision recorded.

Proposal:
  PROP-001 CLI Foundation

Decision:
  accepted

Saved:
  .p2p/proposals/PROP-001-cli-foundation/decision.md

Status:
  ready_for_review → accepted

Next suggested command:
  p2p plan PROP-001 --ai codex
```

### 21.9 Piano

```bash
p2p plan PROP-001 --ai codex
```

Output atteso:

```text
Generating execution plan for PROP-001...

Detected execution domains:
  - software
  - documentation

Suggested workstreams:
  WS1 Core domain model
  WS2 CLI commands
  WS3 Git adapter
  WS4 AI prompt/adapter layer
  WS5 Exporters
  WS6 Documentation

Saved:
  .p2p/proposals/PROP-001-cli-foundation/execution-plan.md

Next suggested command:
  p2p tasks PROP-001 --ai codex
```

### 21.10 Task e action

```bash
p2p tasks PROP-001 --ai codex
```

Output atteso:

```text
Generating tasks and actions...

Created:
  18 tasks
  64 actions

Saved:
  .p2p/proposals/PROP-001-cli-foundation/tasks.yml
  .p2p/proposals/PROP-001-cli-foundation/tasks.md

Next suggested commands:
  p2p export PROP-001 --target markdown
  p2p export PROP-001 --target openspec
```

Esempio task:

```yaml
tasks:
  - id: T001
    title: Define core project structure
    workstream: WS1
    type: software
    status: todo
    actions:
      - id: A001
        title: Define Project entity
      - id: A002
        title: Define Proposal entity
      - id: A003
        title: Define Contribution entity
      - id: A004
        title: Define Decision entity

  - id: T002
    title: Implement p2p init command
    workstream: WS2
    type: software
    status: todo
    actions:
      - id: A001
        title: Create .p2p directory
      - id: A002
        title: Generate project.yml
      - id: A003
        title: Generate governance templates
      - id: A004
        title: Support --agent option
```

---

## 22. Rapporto con Spec Kit e OpenSpec

P2P Engine deve essere upstream rispetto a Spec Kit, OpenSpec e strumenti simili.

```text
P2P Engine
  → proposal
  → decision
  → P2P software spec
  → execution plan
  → task/action
  → export selettivo
      → OpenSpec
      → Spec Kit
      → Markdown
      → issue tracker
```

Tra proposal accettata ed export deve esistere uno strato P2P-native di razionalizzazione:

```text
accepted proposal
→ .p2p/outputs/software-spec/
→ export selettivo
    → OpenSpec
    → Spec Kit
```

Questo evita di trasformare ogni proposal grezza direttamente in una feature software. La proposal conserva discussione, governance, alternative e decisione; la software spec P2P conserva invece il risultato implementabile e normalizzato.

Output suggeriti:

```text
.p2p/project/
  overview.md
  problem.md
  scope.md
  project-swot.md
  features/
    <feature-id>/
      feature.md
      tasks.yml
      actions.yml
  decisions-map.yml
  conflicts.yml
  exports/
    markdown/
    openspec/
    speckit/
```

Nel primo MVP l'aggiornamento dello stato progettuale e esplicito:

```bash
p2p project refresh
p2p project status
p2p project show overview
```

In una fase successiva, l'accettazione di una proposal puo aggiornare automaticamente gli output derivati:

```bash
p2p decision record PROP-010 --outcome accepted --reason "..."
# refresh automatico di .p2p/project/
```

### 22.1 Impact map e memoria dei conflitti

Prima che una proposal venga accettata, P2P Engine deve poter analizzare cosa tocca:

```text
proposal
→ features coinvolte
→ comandi coinvolti
→ file e artefatti coinvolti
→ governance coinvolta
→ dipendenze
→ overlap
→ conflitti
```

Artefatti proposta:

```text
.p2p/proposals/<proposal>/
  impact-map.yml
  related-proposals.yml
  conflict-analysis.yml
```

Memoria progetto:

```text
.p2p/project/conflicts.yml
```

Comandi MVP:

```bash
p2p impact prompt PROP-012
p2p impact import PROP-012 impact-output/

p2p conflict record PROP-010 PROP-012 \
  --type overlaps \
  --reason "Entrambe modificano la semantica dello stato progetto."

p2p conflict status
```

Il rilevamento di conflitti e overlap e consultivo. L'accettazione o il rigetto resta una decisione di governance.

### 22.2 OpenSpec come target

OpenSpec è un target naturale quando una proposal accettata produce una modifica software descrivibile come change proposal.

Mapping indicativo:

```text
P2P proposal.md       → openspec/changes/<change>/proposal.md
P2P execution-plan.md → openspec/changes/<change>/design.md
P2P tasks.md          → openspec/changes/<change>/tasks.md
P2P software spec     → openspec/changes/<change>/specs/<domain>/spec.md
```

### 22.3 Spec Kit come target

Spec Kit è utile quando una parte del lavoro deve diventare:

```text
spec → plan → tasks → implementation
```

Mapping indicativo:

```text
P2P accepted proposal → Spec Kit spec.md
P2P software plan     → Spec Kit plan.md
P2P software tasks    → Spec Kit tasks.md
```

Spec Kit non deve essere il cuore di P2P Engine, ma un possibile motore downstream per la parte software.

---

## 23. Architettura logica consigliata

```text
p2p-core
  dominio
  validazione
  governance
  AI orchestration
  planner
  task generator
  exporter

p2p-cli
  interfaccia terminale

p2p-git-adapter
  branch
  file
  commit
  status
  merge

p2p-ai-adapters
  prompt-only
  codex
  claude
  ollama
  openai-compatible
  mcp

p2p-exporters
  markdown
  openspec
  speckit
  jira
  linear
  github
  gitlab
  gitea

p2p-server
  futura API server

p2p-web
  futura web app
```

Possibile monorepo:

```text
p2p-engine/
  packages/
    core/
    cli/
    git-adapter/
    ai-adapters/
    exporters/
      markdown/
      openspec/
      speckit/
  apps/
    api/
    web/
  examples/
    p2p-engine-self/
```

---

## 24. MVP consigliato

### MVP 1 — CLI Git-native

Obiettivo: dimostrare che il metodo funziona.

Funzioni minime:

```text
p2p init
p2p proposal create
p2p contribution add
p2p digest
p2p clarify
p2p synthesize
p2p decision request
p2p plan
p2p tasks
p2p export --target markdown
p2p export --target openspec
```

Caratteristiche:

- nessuna web app;
- nessun database;
- nessuna autenticazione;
- nessun billing AI;
- file + Git + prompt generator;
- AI opzionale.

### MVP 2 — AI adapter reali

Aggiungere:

- Codex adapter;
- Claude adapter;
- Ollama/OpenAI-compatible adapter;
- validazione output più robusta;
- configurazione provider;
- modalità BYOK locale.

### MVP 3 — Export avanzato

Aggiungere:

- export Spec Kit;
- export issue tracker;
- export task board;
- export documentale.

### MVP 4 — API/Web locale

Aggiungere:

- FastAPI o Django backend;
- semplice UI browser;
- workspace progetto;
- commenti via web;
- visualizzazione proposal;
- trigger comandi CLI da backend.

### MVP 5 — Web collaborativa

Aggiungere:

- utenti;
- organizzazioni;
- permessi;
- governance multiutente;
- notifiche;
- dashboard;
- AI BYOK o billing gestito;
- sandbox multiutente.

---

## 25. Prima proposal reale del progetto

La prima proposal da creare con P2P Engine dovrebbe essere:

```text
PROP-001 — CLI Foundation
```

Titolo utente:

```text
Voglio predisporre la CLI.
```

Obiettivo:

```text
Realizzare una CLI Git-native, platform-agnostic e AI-adapter-ready per validare il modello P2P Engine senza introdurre subito la complessità della web app.
```

Scope MVP:

- inizializzazione progetto;
- creazione proposal;
- aggiunta contribution;
- digest AI o prompt-only;
- clarify guidato;
- synthesize proposal;
- decision request;
- execution plan;
- task/action generation;
- export Markdown;
- export OpenSpec.

Fuori scope:

- web app;
- multiutenza;
- billing;
- dashboard;
- gestione permessi;
- implementazione automatica codice;
- editor collaborativo real-time.

---

## 26. Decisioni architetturali iniziali

Decisioni provvisorie da confermare:

1. P2P Engine nasce come CLI Git-native.
2. La web app arriva dopo il core e la CLI.
3. P2P Engine non deve dipendere da GitHub.
4. La proposal è l'entità centrale.
5. Le task possono avere action più fini.
6. L'AI facilita ma non decide.
7. Gli output AI devono essere validati.
8. Markdown è il formato per i documenti leggibili.
9. YAML/JSON è il formato per dati strutturati.
10. OpenSpec e Spec Kit sono target downstream, non il cuore del sistema.
11. L'integrazione AI deve supportare modalità prompt-only, agent-files, adapter e MCP.
12. La prima integrazione web, quando arriverà, dovrà essere client del motore e non sostituire la CLI.

---

## 27. Questioni aperte

Da approfondire nei prossimi step:

1. Linguaggio di implementazione della CLI: Python, TypeScript, Go o Rust?
2. Formato primario dei dati strutturati: YAML o JSON?
3. Strategia di identificazione proposal: numerica, data-based, slug, prefisso dominio?
4. Come gestire commenti lunghi o conversazioni molto articolate?
5. Come calcolare il relevance score dei commenti?
6. Come rappresentare voti e decisioni nel filesystem?
7. Quanto automatizzare il branch management?
8. Come gestire conflitti Git su proposal concorrenti?
9. Quale exporter implementare per primo: Markdown, OpenSpec o Spec Kit?
10. Come implementare AI adapter senza rendere fragile la CLI?
11. Quando introdurre MCP?
12. Quando introdurre web app e database?
13. Come distinguere in modo affidabile task software e non-software?
14. Come evitare che l'AI produca piani troppo generici?
15. Come validare task e action rispetto alla proposal approvata?

---

## 28. Direzione consigliata immediata

La direzione consigliata è:

```text
Step 1
  Consolidare questo documento come foundation.

Step 2
  Definire il modello dati minimo: Project, Proposal, Contribution, Decision, Plan, Task, Action.

Step 3
  Definire il formato file .p2p.

Step 4
  Disegnare la UX CLI per PROP-001 — CLI Foundation.

Step 5
  Implementare un MVP senza AI diretta, con prompt generator.

Step 6
  Aggiungere agent-files per Codex/Claude/generic.

Step 7
  Aggiungere export Markdown e OpenSpec.

Step 8
  Solo dopo valutare adapter AI reali e web app.
```

---

## 29. Sintesi finale

P2P Engine deve nascere come un motore platform-agnostic per trasformare discussioni collaborative in proposal, decisioni, piani, task e action.

La CLI è il primo prodotto minimo reale. Git è il layer di versionamento e audit. L'AI è integrata tramite adapter, prompt, agent-files e in futuro MCP, ma non è il centro proprietario del sistema.

Spec Kit e OpenSpec sono strumenti utili, ma downstream. P2P Engine deve stare prima: deve aiutare persone e team a chiarire cosa vogliono decidere e realizzare, prima ancora di generare codice.

La prima proposal concreta da realizzare è:

```text
PROP-001 — CLI Foundation
```

Questa proposal servirà a validare il metodo usando P2P Engine per progettare P2P Engine stesso.
