# PROP-100 - Project Decision Context Index and Proposal Neighborhood

## Status

`accepted`

## Problem

P2P conserva gia molte informazioni necessarie a ricostruire il ragionamento del progetto: decisioni e motivazioni nei Markdown, stati e readiness negli YAML, impact map, related proposals, conflict analysis, choice, Change Set, registri, artifact state, vertical coverage, decision precedents e artifact di pubblicazione. Il problema osservato non e prima di tutto il formato di persistenza. Il problema e che i servizi che generano registri, contesti e prompt ne usano solo una parte, perdendo motivazioni, vincoli, relazioni, autorita, provenienza e stato di attivazione.

La revisione della codebase e della feature implementativa ha chiarito ulteriori cause:

- `decisions-map.yml` e `relations.yml` sono projection lossy e non possono essere usati come memoria semantica autorevole;
- intake e context rendering usano ancora selezioni first-N o letture globali non ordinate per rilevanza;
- alcuni path ricostruiscono Change Set o summary ripetutamente e possono moltiplicare scansioni e tempi di risposta;
- il parser Markdown corrente e stretto e non preserva span, sezioni duplicate o diagnostica affidabile per frontmatter malformato;
- `P2PWorkspace` memoizza i service object, quindi un indice conservato nel service potrebbe diventare stale dopo una scrittura nella stessa sessione;
- proposal status e decision outcome possono divergere e il lifecycle include stati come `accepted_with_changes`, `split`, `merged_into_other` e `superseded` che non possono essere ridotti a accepted/rejected;
- decision precedents, project definition, governance constraints e Work execution state devono avere scope e authority espliciti;
- Change Set frontmatter e file di relazione companion possono duplicare o contraddirsi;
- similarity, topologia e authority sono dimensioni differenti e non devono essere fuse in uno score opaco;
- `generated_at` non puo far cambiare l'identita semantica di un output deterministico;
- CLI e MCP possono divergere se payload, serializer e target compatibility non vengono aggiornati nella stessa slice.

L'effetto pratico resta invariato: P2P possiede memoria, ma non recupera in modo affidabile cio che e gia stato deciso o analizzato quando deve supportare una nuova proposta, un intake, una sintesi o il prossimo passo.

## Context

PROP-017 ha introdotto intake e context analysis. PROP-025 ha introdotto il controlled intake apply workflow. PROP-012 ha introdotto impact map e conflict memory. PROP-016 ha introdotto i registri di progetto. PROP-023 e PROP-024 hanno introdotto next actions, choice blocking e choice discovery. PROP-044 e PROP-088 espongono superfici MCP e import parity. PROP-086, PROP-089 e PROP-096 hanno rafforzato readiness, artifact coverage e question state. PROP-099 ha evidenziato la tensione tra output derivati, pubblicazione e stato autorevole.

PROP-100 resta una decisione architetturale ombrello. Non introduce una nuova memoria canonica e non sceglie ora SQLite, PostgreSQL o altri storage. Definisce un livello derivato, rebuildable, validabile e interrogabile sopra gli artifact canonici esistenti.

La specifica repository `specs/features/prop-100-decision-context-index/` descrive l'intero programma implementativo tramite slice indipendenti e gate verificabili. Questo non trasforma PROP-100 in un singolo Change Set: ogni slice deve restare consegnabile, testabile e revisionabile separatamente. La prima consegna resta il dominio, il source snapshot e gli estrattori proposal/decision; le integrazioni pubbliche sono bloccate dai gate delle slice precedenti.

La proposta e decision-ready come direzione architetturale. Non e implementation-ready come unita indivisibile e non autorizza automaticamente il completamento di tutte le slice.

## Goals

- Approvare un decision context index derivato, non canonico, rebuildable, read-only e spiegabile.
- Introdurre un Source Catalog versionato che classifichi fonti semantiche, metadata di qualita, execution state, projection derivate e fonti escluse.
- Richiedere uno snapshot immutabile per richiesta che scopra le fonti una volta e legga, hashi e parsifichi ogni fonte al massimo una volta usando gli stessi byte.
- Mantenere `ProjectDecisionContextService` come facade stateless dietro `P2PWorkspace`, senza snapshot stale tra richieste.
- Definire record, node, relation, evidence, diagnostic, retrieval hit, index e manifest tipizzati e serializzabili con schema versionato.
- Separare canonicality, authority, activation, confidence e completeness.
- Coprire l'intero proposal decision lifecycle, inclusi acceptance qualificata, split, merge, supersession, pending e legacy divergence.
- Indicizzare decision precedents e un sottoinsieme esplicitamente catalogato di governance/project-definition constraints senza interpretazione libera di ogni testo.
- Normalizzare progressivamente relazioni da proposal artifacts, Change Set, choices, blockers, conflict memory, vertical coverage e Work lineage.
- Usare node namespace tipizzati, relation vocabulary versionata, evidence merge deterministico e traversal cycle-safe.
- Distinguere edge di topologia da retrieval reasons quali lexical overlap, same surface e heuristic vertical match.
- Fornire retrieval deterministico e spiegabile per proposal ID e idea text, con policy versionata, applicabilita esplicita, score ricostruibile e protezione dai falsi positivi.
- Rendere `small` e `medium` budget semantici misurabili applicati dopo ranking e grouping.
- Bloccare l'integrazione pubblica finche profiling, scan/read count e fixture di scala non dimostrano che il nuovo percorso non replica i timeout correnti.
- Introdurre freshness basata su presenza/hash reali delle fonti e versioni delle policy, separando `generated_at` dall'identita semantica.
- Migrare context packet, intake, prompt, next actions, projection e MCP per slice compatibili, mantenendo owner authority e controlled apply.

## Non-Goals

- Non sostituire proposal, decision, choice, Change Set, Work, YAML o Markdown canonici come source of truth.
- Non creare una memoria canonica parallela aggiornata da sintesi LLM libera.
- Non usare registri, decisions map, pubblicazioni, prompt o altri output derivati come input semantico dell'indice.
- Non implementare PROP-100 come un unico Change Set senza gate intermedi.
- Non scegliere o implementare una cache persistente nella prima realizzazione; una cache giustificata dalle misure richiede una feature separata.
- Non introdurre embeddings o ricerca non spiegabile nel primo retrieval.
- Non ridefinire proposal lifecycle, governance, owner authority, Git flow o controlled apply.
- Non interpretare genericamente ogni documento di governance o project definition.
- Non applicare automaticamente relazioni, tag, supersessioni, decisioni o vincoli.
- Non pubblicare una nuova registry topology stabile senza un consumer e uno schema separatamente approvati.
- Non estendere nella prima integrazione il retrieval pubblico a Change Set, Choice o Work target.
- Non incorporare nel dominio semantico la correzione funzionale del timeout preesistente; profiling e remediation delle scansioni necessarie all'integrazione restano tuttavia un gate obbligatorio di PROP-100.
- Non fissare nella proposta ombrello pesi numerici e layout dei moduli: tali dettagli appartengono alla feature versionata.

## Proposal

Introdurre un livello di accesso decisionale derivato sopra gli artifact canonici P2P esistenti. Il livello estrae, normalizza, collega e recupera decisioni, vincoli, relazioni e contesto rilevante con provenance, authority, activation, confidence, completeness e freshness verificabili. Non sostituisce gli artifact originali e non introduce una nuova fonte di verita.

Il programma e organizzato in slice dipendenti:

1. Domain, Source Catalog, request-scoped snapshot e proposal/decision extraction.
2. Authority policy e typed topology normalization.
3. Explainable retrieval e semantic budgets.
4. Performance profiling/remediation gate.
5. Context packet, CLI e MCP integration.
6. Intake e proposal prompt neighborhood.
7. Next actions e legacy projection migration.
8. Freshness e materialized manifest.
9. Cache decision basata su misure, senza cache implementation in PROP-100.

Una singola specifica repository puo coordinare queste slice, ma non elimina i gate: ogni slice deve avere dipendenze, exit criteria, focused tests e compatibility evidence. La prima slice non cambia CLI, MCP, intake, prompt, registri o storage.

Il Source Catalog dichiara cosa e semantic source e cosa e escluso. Proposal/decision, project choices, conflict memory, Change Set relation sources, declared vertical coverage e decision precedents possono produrre evidenza secondo policy. Readiness, artifact state, questions, contributions e Work status descrivono qualita, evento o execution state e non attivano decisioni. Registri e narrative generate restano projection escluse.

L'extraction session cattura path root-relative, presence, bytes, hash, parsed fragments e diagnostics. Hash e parse usano gli stessi byte. Stable identity dipende da source path normalizzato, owner, record kind e semantic fragment anchor; content hash e line span restano metadata separati.

La authority policy distingue canonicality, authority, activation, confidence e completeness. `accepted_with_changes` attiva una decisione qualificata dal reason; rejected/deferred/split/merged/superseded restano storia o lineage. Una divergenza tra proposal status e decision outcome produce diagnostics e non ripara automaticamente le fonti. Acceptance status da solo non rende una decisione applicabile a ogni query.

La topologia usa node type distinti per proposal, decision, choice, Change Set, Work, vertical section, capability, surface, feature, command e file. Una relation canonica memorizza source, type e target; incoming/outgoing e calcolato rispetto alla query e non crea edge inversi duplicati. Assertion equivalenti fondono le evidence senza moltiplicare score. Change Set source duplicati vengono riconciliati con precedence e divergence diagnostics. Traversal e depth/fan-out bounded.

Il retrieval usa un indice in memoria e non legge file dopo il build. Candidate selection, lexical normalization, applicability, score contributions, cap, status penalties, historical threshold, tie-breaking, grouping, empty result e budget sono policy versionate. Ogni score deve essere ricostruibile dalle contribution esposte. `small` e `medium` sono assemblati dopo ranking; non esiste fallback first-N.

Il percorso pubblico puo partire da `PROP-*`. Target `CHANGE-*`, `CHOICE-*`, `WORK-*` e no-target mantengono il comportamento corrente finche non ricevono slice dedicate. CLI text, structured output e MCP espongono semantica equivalente; renderer e handler non devono rerankare.

Il source fingerprint include catalog version, path, presence e source hash. Il semantic fingerprint include le versioni di extractor, authority e relation policy; i packet includono retrieval e budget policy. `generated_at` e metadata osservazionale con clock iniettabile e non cambia semantic equality.

Il bug corrente di `p2p context` puo essere corretto come lavoro tecnico separato, ma PROP-100 non puo integrare altro lavoro nel path finche non sono rispettati: un discovery pass, una read/hash/parse per fonte, zero source read durante query, assenza di nested full scan e una fixture di scala con ceiling documentato.

## Acceptance Criteria

- L'owner puo approvare o respingere consapevolmente la direzione di un decision context index derivato, non canonico e source-linked.
- La proposta distingue umbrella decision, specifica multi-slice e Change Set indipendenti.
- Il Source Catalog classifica fonti incluse, metadata e fonti derivate escluse; l'indice non legge registri o publication come semantic truth.
- Una extraction session scopre le fonti una volta e legge/hasha/parsa ogni fonte al massimo una volta dagli stessi byte.
- Un service memoizzato non conserva snapshot stale tra richieste; una modifica nella stessa workspace e visibile alla richiesta successiva.
- Stable IDs, content hashes, evidence span e completeness sono contratti distinti e deterministici.
- Il lifecycle copre accepted, accepted-with-changes, rejected, deferred, split, merged, superseded, pending e legacy divergence.
- Accepted-with-changes conserva il reason come qualifier; acceptance status non trasmette automaticamente applicabilita globale.
- Decision precedents, project choices, readiness, artifact state, questions, contributions, vertical signals e Work state ricevono authority/activation coerenti con il loro ruolo.
- Node e relation type sono validati; query direction non duplica edge; evidence duplicate non moltiplicano lo score; traversal termina su cicli e fan-out.
- Change Set relation sources discordanti producono divergence diagnostics e precedence deterministica.
- Retrieval per proposal ID e idea text e deterministico, source-free dopo il build, versionato e spiegabile tramite contribution che ricostruiscono lo score.
- `small` e `medium` hanno limiti misurabili definiti nella feature e applicati dopo ranking/grouping, senza fallback first-N.
- Empty, partial e unavailable context sono distinguibili e mantengono evidence minima per i claim inclusi.
- Profiling e performance remediation soddisfano structural read/scan gates prima della context integration.
- `generated_at` non modifica semantic fingerprint; source presence/hash e policy version changes rendono stale le projection pertinenti.
- La prima implementazione non persiste cache; una cache eventualmente necessaria richiede una feature separata.
- `PROP-*` puo ricevere `nearby_context` mantenendo i legacy fields; non-proposal target restano compatibili nella prima integrazione.
- CLI text, structured output e MCP mantengono semantica e schema allineati e read-only.
- Intake e prompt usano context rilevante ma non estendono controlled apply o owner authority.
- Golden, adversarial, malformed-source, determinism, same-workspace, cycle, scale e public-contract tests proteggono le slice.
- Nessuna build/query del decision context modifica fonti canoniche o crea cache/projection implicite.

## Decision

Pending.
