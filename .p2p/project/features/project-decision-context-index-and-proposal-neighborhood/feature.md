# Project Decision Context Index and Proposal Neighborhood

## Provenance

- Proposal: PROP-100
- Source: .p2p/proposals/PROP-100-project-decision-memory-and-proposal-topology

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

## Decision

# Decision - PROP-100

## Status

`accepted`

## Outcome

accepted

## Reason

Accepted as the umbrella architecture direction for a derived, read-only and source-linked decision context index delivered through independently gated slices. Governed artifacts remain authoritative; public integration requires the defined performance and compatibility gates, and any persistent cache remains a separate measured feature.

## Date

2026-07-15

## Approver

owner
