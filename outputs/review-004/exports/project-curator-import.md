# P2P Engine

## Executive Summary

P2P Engine e un motore locale-first per trasformare conversazioni, analisi e decisioni progettuali in memoria governata, verificabile e riutilizzabile da persone e agenti. Il progetto tiene separate tre responsabilita: la governance del progetto in `.p2p/`, gli output derivati per lettura o handoff, e l'implementazione software nel repository.

Lo stato corrente sintetizzato da `outputs/latest/project.md` include 93 proposte accettate. Da queste emerge un sistema che non vuole essere solo un archivio di decisioni, ma un metodo operativo: una proposta nasce da intake o conversazione, viene raffinata con readiness, domande, assunzioni, alternative e rischi, puo generare Change Set e Work, puo essere esposta a CLI, MCP e agenti, e puo produrre output leggibili o specifiche operative.

La fonte autorevole resta `.p2p/`: questo documento e un output umano curato, non sostituisce registri, proposte, decisioni, Change Set, readiness o artifact governati. Il suo scopo e rendere comprensibile il progetto come insieme coerente, evitando che il lettore debba ricostruirlo leggendo una sequenza cronologica di artifact interni.

La pipeline di pubblicazione umana introdotta da PROP-099 e ora usata per produrre questo documento: `prepare` genera il packet di curatela, la curatela produce un unico Markdown canonico, la validazione verifica il contratto documentale e il rendering PDF resta uno stage separato. L'approvazione editoriale del documento non e implicita: deve essere registrata con la review owner prevista dalla pipeline.

## Project Identity And Vertical Framing

P2P Engine lavora nel dominio della governance progettuale assistita da agenti. Il suo verticale operativo, per come risulta dalle proposte accettate, combina project governance, memoria decisionale, collaborazione Git, agent orchestration, MCP, documentazione tecnica e generazione di specifiche.

Non risulta selezionato un vertical lock attivo: `p2p project vertical lock show` segnala assenza di `.p2p/project/vertical.lock.yml` e fallback `base_project`. Questo e un elemento di contesto importante: il progetto dispone di funzionalita per verticali e definizione di progetto, ma l'output corrente non puo dichiarare un verticale specializzato formalmente attivo. La lettura corretta e quindi generica ma project-first: P2P Engine e il prodotto, il suo ambito e la gestione strutturata della memoria di progetto.

Il progetto assume che la collaborazione tra umano e agenti debba essere governata da primitive esplicite. Gli agenti possono analizzare, proporre, preparare, validare ed eseguire workflow tecnici; l'owner conserva il controllo sulle decisioni di governance, come accettare proposte, decidere scelte, finalizzare lavori, pubblicare o approvare output.

## Current Project Shape

### Governance Memory

La memoria principale e costituita da proposte, artifact, readiness, registri, decisioni, Change Set e Work. Le proposte accettate definiscono sia il prodotto sia le regole con cui il prodotto evolve. La scelta architetturale centrale e mantenere `.p2p/` come source-of-truth gestito, evitando modifiche manuali agli artifact interni e imponendo l'uso di primitive CLI o MCP esplicite.

Le prime proposte hanno costruito il nucleo: CLI locale, workflow di exploration e readiness, import di prompt, registri, stato progetto, impact map, conflict memory, intake, choice management e comandi di ispezione. Questa base rende il sistema piu vicino a un ambiente di lavoro governato che a un semplice generatore di file. Riferimenti: PROP-001, PROP-002, PROP-004, PROP-009, PROP-010, PROP-012, PROP-016, PROP-017, PROP-018, PROP-020.

### Readiness, Questions And Decision Flow

Il sistema non tratta una proposta come pronta solo perche e stata scritta. Readiness, domande, artifact state, rubriche e assessment servono a distinguere una bozza promettente da una proposta abbastanza definita per una decisione owner. Le decisioni restano owner-controlled, ma il sistema puo spiegare cosa manca, quali artifact sono deboli e quali domande sono ancora rilevanti.

Questo orientamento e stato rafforzato con readiness profile, question-state convergence, artifact-aware readiness e normalizzazione delle evidenze. Il principio attuale e pragmatico: la readiness e advisory, non sostituisce il giudizio dell'owner, ma deve rendere esplicite lacune, rischi e qualita dell'evidenza. Riferimenti: PROP-054, PROP-056, PROP-057, PROP-082, PROP-086, PROP-089, PROP-096.

### Change Sets, Work And Git Collaboration

P2P Engine modella il passaggio da proposta accettata a implementazione con Change Set e Work. Il flusso copre branch, submit, review, publish, accept, status, merge conflict guidance, finalize, cleanup e retire. La collaborazione Git viene trattata come una superficie governata, non come dettaglio operativo libero.

La direzione piu recente prevede lavoro concorrente e collaborazione multi-branch, mantenendo `main` come contenitore dello stato accettato. Questo riduce ambiguita tra sperimentazione locale, branch gestiti e stato governato. Riferimenti: PROP-030, PROP-031, PROP-032, PROP-034, PROP-035, PROP-036, PROP-039, PROP-040, PROP-043, PROP-072.

### Agent And MCP Surfaces

Il progetto e agent-first: Codex, Claude e profili generici ricevono istruzioni generate e aggiornabili. Le skill non sono considerate sorgente canonica quando sono generate dentro superfici adapter-specifiche; la sorgente dei template appartiene alla release di P2P Engine e l'installazione genera le destinazioni attese dai diversi agenti.

MCP affianca la CLI per l'accesso locale e remoto controllato. Le proposte accettate hanno esteso MCP da lettura e bootstrap verso import, refinement, choice, contribution, readiness, next actions, artifact parity e Work lifecycle parity. Le operazioni di scrittura richiedono schema esplicito e, dove previsto, permessi o consent receipt. Riferimenti: PROP-005, PROP-006, PROP-021, PROP-044, PROP-045, PROP-046, PROP-048, PROP-049, PROP-050, PROP-052, PROP-065, PROP-066, PROP-075, PROP-077, PROP-081, PROP-088, PROP-092, PROP-093.

### Software Specification And Downstream Handoff

Il progetto include un ciclo di vita per trasformare decisioni governate in specifiche software e handoff downstream. Questa parte distingue tra proposta P2P, sviluppo locale, specification lifecycle, export Spec Kit e validazione export. L'obiettivo e impedire che una conversazione venga confusa con una specifica implementabile senza Change Set, evidence e passaggi di refresh/validate.

Le specifiche locali sotto `specs/` restano un layer di sviluppo del repository, non il source-of-truth governato. Quando servono implementazioni, il sistema usa le decisioni P2P come input e poi produce requirement, design e task locali con vincoli di tracciabilita. Riferimenti: PROP-026, PROP-027, PROP-028, PROP-029, PROP-064, PROP-094.

### Runtime, Documentation And Release

Il progetto ha consolidato installazione locale, runtime bootstrap, documentazione agent-first, setup MCP, release wheel e aggiornamento dei contratti runtime. Questo rende P2P Engine installabile e aggiornabile in repository terzi, con attenzione alla separazione tra repo del motore e progetto governato che lo usa.

La documentazione pubblica resta un'area esplicitamente aperta: PROP-063 e una draft proposal dedicata alla chiusura del gap documentale pubblico. Questo significa che il sistema interno e ricco, ma la superficie pubblica deve ancora essere rifinita come prodotto comunicabile in modo stabile. Riferimenti: PROP-058, PROP-061, PROP-062, PROP-067, PROP-068, PROP-069, PROP-070, PROP-073, PROP-074, PROP-078, PROP-080, PROP-095, PROP-097.

### Human Project Publication

PROP-099 introduce il ciclo di vita dell'output umano canonico. La scelta chiave e non moltiplicare versioni commerciali, tecniche o per audience: il progetto produce un unico documento umano che rappresenta "il progetto X" in modo coerente. Altri tagli possono essere derivati fuori da questa pipeline.

La pipeline distingue source export, publication profile, curator packet, curated Markdown, validation, rendering PDF e owner review. `project.md` resta export grezzo e machine-friendly; `project.curated.md` e il documento umano canonico; `project.pdf` e un rendering draft; `approved_for_publication` diventa vero solo dopo review owner. Riferimento: PROP-099.

## Operating Model

Il flusso operativo corrente puo essere letto cosi:

1. Una nuova esigenza entra come conversazione, intake o proposta.
2. Il sistema crea o aggiorna artifact leggibili: problema, obiettivo, alternative, rischi, assunzioni, decisione e domande.
3. La readiness valuta se l'evidenza e sufficiente, quali gate falliscono e quali domande meritano risposta.
4. L'owner decide se accettare, rinviare o respingere.
5. Le proposte accettate possono alimentare Change Set, Work, specifiche locali, export downstream o output di progetto.
6. CLI e MCP devono offrire superfici coerenti quando il caso d'uso e lo stesso, con confini piu stretti sulle operazioni owner-controlled.
7. Gli output derivati devono dichiarare la propria relazione con `.p2p/` e non sostituire lo stato governato.

Questo modello spiega perche P2P Engine investe molto in primitive apparentemente "di processo": senza primitive esplicite, agenti diversi tendono a ricostruire il contesto in modo fragile, leggendo troppi file, ignorando artifact importanti o trattando come decisione cio che era solo una bozza.

## Planned And Pending Work

Tre aree risultano visibili come lavoro non accettato nello stato corrente:

- PROP-063, "Public Documentation Gap Closure", e una draft proposal per migliorare la documentazione pubblica.
- PROP-098, "Test Impact and Validation Routing", e una draft proposal per decidere in modo deterministico quali test eseguire dopo una modifica.
- PROP-100, "Project Decision Memory and Proposal Topology", e una draft proposal per migliorare la lettura della memoria di progetto tramite prossimita, sintesi e relazioni tra decisioni.

Queste draft non fanno parte delle 93 proposte accettate sintetizzate dal source export. Sono utili come segnale di direzione: il progetto sta affrontando tre problemi maturi, cioe comunicazione esterna, efficienza della validazione tecnica e scalabilita cognitiva della memoria decisionale.

Il Change Set corrente rilevato e `CHANGE-068 Human Project Publication Pipeline` con stato `implementation_ready`. Il comportamento osservato della pipeline di pubblicazione e utilizzabile per generare questo output, ma lo stato governato del Change Set va comunque allineato tramite il lifecycle previsto quando l'owner decide di chiudere il lavoro.

## Risks, Assumptions And Open Questions

Il rischio principale e la crescita della memoria: molte proposte accettate rendono il progetto tracciabile, ma aumentano il costo cognitivo per agenti e owner. La bozza PROP-100 nasce proprio da questa frizione. Una soluzione utile dovrebbe migliorare sintesi e navigazione senza ribaltare l'impianto esistente di proposte, readiness, CLI, MCP e registri.

Un secondo rischio e la parita incompleta tra CLI e MCP. La direzione generale del progetto spinge verso parity locale quando il caso d'uso e lo stesso, ma alcune superfici owner-controlled restano piu caute. Questo tema va trattato come decisione di prodotto e sicurezza, non come semplice copia di comandi.

Un terzo rischio riguarda la concorrenza e la persistenza. Il progetto oggi e local-first e file-system based; questa scelta e coerente con installazione locale, Git e trasparenza. Tuttavia, se l'uso remoto multiutente cresce, la memoria su file potrebbe richiedere in futuro un backend piu strutturato o un modello di locking/transazione piu forte.

Un'assunzione importante e che gli output umani siano derivati, non governino direttamente il progetto. Se un documento umano risulta poco leggibile, l'agente puo rigenerarlo o curarlo meglio; se invece una decisione e sbagliata, va corretta nello stato P2P tramite le primitive di governance.

Una domanda aperta e il vertical lock. Il sistema supporta verticali, ma lo stato corrente usa il fallback base. Se l'owner vuole che gli output futuri siano davvero vertical-aware, serve selezionare o definire formalmente il verticale attivo.

## Source Of Truth And Publication Status

`.p2p/` remains authoritative as the source-of-truth for proposals, decisions, readiness, registries, Change Sets and Work. `outputs/latest/project.md` is a generated export from that state. `outputs/latest/project.curated.md` is the curated human publication draft derived from the export and from the publication packet.

Questo documento non dichiara approvazione editoriale. La review owner e uno stage separato della pipeline di pubblicazione. Fino a quella review, il documento va considerato una bozza canonica curata, valida come output di lavoro ma non ancora approvata per pubblicazione finale.

## Traceability Notes

L'input principale e `outputs/latest/curator-input.md`, generato dalla pipeline di pubblicazione. Il source export e `outputs/latest/project.md` con sha256 `72b2be19fcb5d51a23ac326ab3a7f4f98645421c6c8d192c7e6742c2adbd1622`. Il P2P source fingerprint del packet e `645a05ca7c7b125041f5d733876b8b6ccd28bc90512e99fc8b9074c2e0000f3a`.

I gruppi funzionali citati derivano dalle proposte accettate elencate nel packet di curatela: fondazione CLI e governance (PROP-001, PROP-002, PROP-004, PROP-009, PROP-010, PROP-012, PROP-016), intake e decision flow (PROP-017, PROP-018, PROP-019, PROP-020, PROP-022, PROP-023, PROP-024, PROP-025), Work e Git (PROP-030 through PROP-043, PROP-072), MCP e agenti (PROP-044 through PROP-052, PROP-065, PROP-066, PROP-075, PROP-077, PROP-081, PROP-088, PROP-092, PROP-093), verticali e project definition (PROP-071, PROP-083, PROP-085, PROP-090), software specs (PROP-026, PROP-027, PROP-028, PROP-029, PROP-064, PROP-094), runtime e release (PROP-058, PROP-061, PROP-062, PROP-067 through PROP-070, PROP-073, PROP-074, PROP-078, PROP-080, PROP-095, PROP-097), readiness e qualita (PROP-054, PROP-056, PROP-057, PROP-060, PROP-082, PROP-086, PROP-089, PROP-096), e pubblicazione umana (PROP-099).

Le draft citate come lavoro non accettato sono state rilevate dallo stato CLI corrente con `p2p proposal list --status draft`: PROP-063, PROP-098 e PROP-100. Il vertical lock mancante e stato rilevato con `p2p project vertical lock show`.
