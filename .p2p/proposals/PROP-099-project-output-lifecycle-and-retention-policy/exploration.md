Ti propongo una formulazione più solida del problema e della direzione progettuale di `PROP-099`.

# PROP-099 — Human Project Publication Pipeline

## Problema

P2P Engine è già in grado di trasformare idee, contributi, proposal, decisioni, readiness, verticali, Change Set e altri artifact governati in una definizione complessiva del progetto.

Il comando di export visibile produce un `project.md` completo e tracciabile, derivato dallo stato gestito sotto `.p2p/`. Questo risultato è utile come memoria consolidata, come base di audit e come fonte per agenti e trasformazioni successive.

Il problema è che completezza e leggibilità editoriale non coincidono.

L’export attuale riflette ancora in larga parte la struttura interna della memoria P2P:

* contenuti organizzati per proposal e artifact;
* sezioni ripetute;
* blocchi di governance molto dettagliati;
* placeholder o artifact vuoti;
* elenchi estesi di requisiti, rischi, assunzioni e decisioni;
* informazioni storiche mescolate allo stato progettuale corrente;
* scarsa distinzione immediata tra direzione accettata, funzionalità implementata, lavoro pianificato e materiale ancora incerto.

Questo rende il documento completo, ma non necessariamente comprensibile a un lettore umano esterno al processo P2P.

Un owner, uno stakeholder, un contributor o un implementatore non dovrebbe essere costretto a ricostruire il progetto leggendo decine di proposal e centinaia di sezioni interne. Ha bisogno di un documento che presenti il progetto attraverso un filo conduttore:

1. che cos’è;
2. perché esiste;
3. quale problema risolve;
4. chi coinvolge;
5. quali sono i confini;
6. quale direzione è stata accettata;
7. quali capability compongono il sistema;
8. come funziona operativamente;
9. quale livello di maturità ha raggiunto;
10. quali rischi, lacune e prossimi passi rimangono.

La criticità non riguarda quindi la quantità di contenuto disponibile. Il materiale progettuale esiste già.

La criticità riguarda la trasformazione da:

```text
memoria completa e governata
```

a:

```text
documento editoriale leggibile e pubblicabile
```

Convertire direttamente l’export completo in PDF non risolverebbe il problema. Produrrebbe semplicemente una versione impaginata di un documento ancora troppo vicino alla struttura interna di P2P.

Serve quindi uno strato editoriale esplicito tra l’export completo e il rendering finale.

## Obiettivo

Introdurre una pipeline di pubblicazione che trasformi lo stato P2P in un documento umano curato e successivamente in un PDF neutro e condivisibile.

La pipeline target è:

```text
.p2p/ managed state
  ↓
p2p project export
  ↓
project.md completo
  ↓
project curator skill
  ↓
project.curated.md
  ↓
publication validation
  ↓
PDF renderer
  ↓
project.pdf
```

La pipeline deve mantenere una separazione netta tra:

```text
contenuto governato
curatela editoriale
validazione della pubblicazione
rendering tipografico
```

## Soluzione proposta

La soluzione da perseguire è una pipeline ibrida composta da componenti indipendenti.

### 1. Export completo deterministico

P2P continua a generare un documento completo a partire dalla memoria governata.

Questo livello deve restare:

* deterministico;
* tracciabile;
* completo;
* rigenerabile;
* vicino alla struttura dello stato P2P;
* privo di interpretazioni editoriali non verificabili.

Il suo compito è raccogliere fedelmente il contenuto disponibile, non produrre necessariamente il miglior documento da leggere.

### 2. Curatela semantica tramite skill agentica

Una skill dedicata, `p2p-project-curator`, trasforma l’export completo in una versione editoriale.

La skill deve comportarsi come un editor tecnico di progetto.

Deve:

* identificare la tesi centrale del progetto;
* leggere il verticale attivo e la project definition;
* adattare la struttura del documento al dominio;
* raggruppare le proposal per capability;
* distinguere stato corrente e storia;
* separare accepted, implemented, planned, partial, pending e missing;
* eliminare placeholder e ripetizioni;
* spostare i dettagli eccessivi nelle appendici;
* mantenere rischi, assunzioni e questioni aperte;
* preservare la tracciabilità verso proposal, decisioni e artifact;
* produrre Markdown pulito e stabile.

Il principio guida è:

```text
Le proposal sono evidenze del progetto.
Non sono la struttura narrativa del documento.
```

La skill non deve:

* modificare `.p2p/`;
* inventare fatti;
* modificare decisioni;
* reinterpretare readiness come implementazione;
* nascondere lacune;
* generare software specification al posto della pipeline dedicata;
* occuparsi di impaginazione PDF.

La skill già predisposta formalizza correttamente questa distinzione editoriale e il principio project-first. 

### 3. Output parallelo e revisionabile

Nella prima implementazione la curatela non deve sovrascrivere automaticamente il documento completo.

Gli output iniziali dovrebbero essere:

```text
outputs/latest/project.md
outputs/latest/project.curated.md
outputs/latest/project.pdf
```

Dove:

```text
project.md
  = export completo attuale

project.curated.md
  = versione editoriale candidata

project.pdf
  = rendering della versione curata
```

Questo permette all’owner di confrontare sorgente ed elaborazione prima di decidere quale artifact debba diventare il documento umano principale.

In una fase successiva, dopo aver validato il comportamento della pipeline, si potrà adottare la convenzione:

```text
project.full.md
project.md
project.pdf
```

dove `project.md` diventa la versione curata e `project.full.md` conserva l’export completo.

### 4. Validazione editoriale

Prima del rendering PDF deve esistere una validazione specifica della pubblicazione.

Non si tratta di validare il progetto nel senso di `p2p validate`, ma di controllare il contratto del documento.

Controlli minimi:

* un solo heading H1;
* gerarchia Markdown coerente;
* executive summary presente;
* assenza di placeholder noti nel corpo;
* nessun dump completo di proposal nel testo principale;
* distinzione esplicita tra stato progettuale e stato implementativo;
* distinzione tra accepted, planned, pending e missing;
* source-of-truth warning presente;
* traceability disponibile;
* struttura compatibile con il verticale;
* Markdown adatto al rendering PDF.

Questa fase deve essere prevalentemente deterministica.

La skill produce contenuto semantico; il validatore verifica che l’output rispetti il contratto editoriale.

### 5. Renderer PDF neutro

Il PDF renderer consuma esclusivamente il documento curato e validato.

Il primo tema deve essere semplice e asettico:

```text
A4
tipografia standard
colori neutri
indice
numeri di pagina
heading coerenti
tabelle leggibili
code block essenziali
header e footer minimi
```

Il renderer non deve:

* riscrivere il contenuto;
* eliminare sezioni;
* cambiare lo stato delle informazioni;
* inventare titoli;
* modificare decisioni o readiness;
* decidere cosa è importante.

La regola è:

```text
curator = contenuto e struttura
renderer = presentazione
```

## Perché una pipeline ibrida

Una soluzione interamente deterministica non è sufficiente per la curatela.

Il motore può ordinare, filtrare, normalizzare heading e rimuovere placeholder. Ma difficilmente può comprendere in modo affidabile:

* quale sia il filo narrativo più utile;
* quali proposal descrivano la stessa capability;
* quali dettagli debbano restare nel corpo;
* cosa possa essere spostato in appendice;
* come adattare il documento a verticali molto differenti;
* come spiegare il progetto a un pubblico misto.

Questa parte richiede interpretazione semantica.

Allo stesso tempo, affidare tutto a una skill senza contratti deterministici produrrebbe risultati variabili e difficili da verificare.

La divisione corretta è quindi:

```text
CLI / engine
  prepara input, congela fonti, definisce contratti, valida output, archivia versioni

skill agentica
  sintetizza, raggruppa, riscrive e costruisce il filo narrativo

owner
  revisiona e approva

renderer
  impagina il documento validato
```

## Struttura adattiva al verticale

La pipeline non deve imporre un indice software a tutti i progetti.

Deve distinguere:

```text
sezioni comuni
sezioni derivate dal verticale
sezioni opzionali
appendici
```

Le sezioni comuni possono includere:

* identità del progetto;
* visione;
* problema;
* stakeholder;
* scope;
* direzione accettata;
* maturità;
* rischi;
* domande aperte;
* roadmap;
* tracciabilità.

Le sezioni specifiche devono derivare dal verticale attivo e dalla project definition.

Per un progetto software potranno emergere:

* workflow;
* architettura;
* modello dati;
* integrazioni;
* requisiti non funzionali;
* validazione.

Per un board game, un progetto sociale o un prodotto fisico, la struttura dovrà seguire altri capisaldi.

La struttura editoriale standard deve quindi essere un fallback, non una gabbia.

## Profilo di pubblicazione

Per limitare la variabilità agentica, la pipeline dovrebbe introdurre un profilo di pubblicazione, inizialmente anche solo come contratto concettuale:

```yaml
publication_profile:
  audience: mixed
  depth: standard
  language: project_default
  vertical_structure: adaptive
  include_appendix: false
  theme: neutral-v1
```

Questo consente di specificare:

* per chi è scritto il documento;
* quanto deve essere approfondito;
* quale lingua usare;
* se includere appendici;
* quale tema applicare al PDF.

## Perimetro della prima implementazione

La proposta deve definire subito l’intera pipeline, ma la prima implementazione deve essere un vertical slice minimale e completo.

### Incluso

```text
- skill p2p-project-curator valida e installabile;
- struttura adattiva al verticale;
- compact surfaces first;
- output project.curated.md;
- validazione editoriale minima;
- PDF renderer neutro;
- output project.pdf;
- owner review manuale;
- source traceability;
- nessuna modifica a .p2p.
```

### Escluso dal primo slice

```text
- temi multipli;
- branding personalizzato;
- editor visuale;
- marketplace di template;
- appendici sofisticate;
- sostituzione automatica definitiva di project.md;
- curatela completamente deterministica;
- integrazione con OpenSpec o Spec Kit nella stessa pipeline;
- generazione di software spec;
- publication package avanzato;
- MCP parity completa, salvo decisione esplicita.
```

## Evoluzione prevista

### Slice 1 — End-to-end minimo

```text
project.md
  → curator skill
  → project.curated.md
  → validation
  → neutral PDF
```

### Slice 2 — Orchestrazione CLI

```text
p2p project publish prepare
p2p project publish validate
p2p project publish render
p2p project publish status
```

### Slice 3 — Publication package

```text
project.full.md
project.md
project.appendix.md
project.pdf
publication-manifest.yml
render-report.yml
```

### Slice 4 — Profili e temi

```text
audience profiles
depth profiles
vertical publication profiles
additional PDF themes
branding opzionale
```

## Rischi da evitare

### PDF elegante su contenuto debole

Mitigazione: il PDF può essere generato solo dal Markdown curato e validato.

### Nuova source of truth parallela

Mitigazione: tutti gli output dichiarano chiaramente di essere derivati; `.p2p/` resta la fonte governata.

### Perdita di informazioni durante la sintesi

Mitigazione: traceability, appendici e report di curatela.

### Confusione tra accepted e implemented

Mitigazione: vocabolario di stato esplicito e quality gate dedicato.

### Struttura troppo rigida

Mitigazione: sezioni adattive al verticale.

### Variabilità eccessiva tra esecuzioni

Mitigazione: publication profile, struttura dichiarata, validazione e snapshot.

### Renderer che modifica il contenuto

Mitigazione: contratto rigido tra `project.curated.md` e PDF renderer.

### Proposta troppo ampia

Mitigazione: una sola architettura, ma slice interne indipendenti e verificabili.

## Direzione raccomandata

`PROP-099` dovrebbe quindi definire una **Human Project Publication Pipeline** completa.

La soluzione non è scegliere tra skill e PDF.

La soluzione è collegarli correttamente:

```text
export completo
  → curatela semantica
  → validazione
  → rendering PDF
```

La skill è il motore editoriale.

La CLI e il validatore forniscono controllo e ripetibilità.

Il PDF è il risultato pubblicabile.

La proposta deve progettare subito questo flusso completo, mantenendo però ogni fase indipendente, ispezionabile e sostituibile.

Questa formulazione può diventare direttamente la base di `problem`, `proposal`, `goals`, `scope`, `risks` e `acceptance criteria` di `PROP-099`.
