# Assumptions - PROP-002

- Gli artefatti P2P restano la fonte di verita per la proposta.
- Git versiona il risultato dell'interlocuzione.
- L'agente puo valutare e segnalare la qualita dell'esplorazione, ma non puo
  decidere al posto dell'owner.
- Gli artifact Markdown restano il formato authored per umani e agenti.
- I dati strutturati necessari alla macchina devono vivere in readiness profile,
  readiness assessment, snapshot, registry, export o audit record.
- La readiness della proposta affianca lo stato procedurale della proposal; non
  lo sostituisce.
- La readiness e profile-based e versioned.
- Ogni score deve registrare profile id, profile version e computed_at.
- La maturity della proposta puo essere rappresentata con un valore da 0 a 100.
- La maturity misura la qualita e completezza dell'esplorazione, non il merito
  politico o strategico della decisione.
- `computed_score` deve restare il risultato onesto dei criteri automatici o
  ibridi.
- Owner override e un evento governance, non una modifica del computed score.
- L'override readiness avviene primariamente durante l'accept owner, tramite un
  comando esplicito come `p2p proposal accept --override-readiness --reason`.
- L'owner override deve preservare computed score, failed gates e reason.
- `override_reason` e obbligatorio quando l'owner accetta sotto la readiness
  target.
- Le soglie 70, 85 e 95 possono controllare quanto l'agente deve essere pedante.
- Un punteggio totale alto non basta se mancano criteri essenziali per il tier
  della proposta.
- Le proposal governance-critical richiedono minimum gate piu severi e almeno
  confidence media per automatic `ready_for_decision`.
- PROP-002 e governance-critical.
- La confidence deve essere distinta dallo score e basata sulla qualita delle
  evidenze, non sulla qualita retorica del testo.
- Ogni criterio valutato deve avere evidenze collegate ad artifact o sezioni.
- Gli artifact `placeholder` o `thin` devono limitare il punteggio massimo dei
  criteri collegati.
- `needs_owner_input` e uno stato utile e distinto da `thin`: l'artifact puo
  essere buono ma non decision-ready senza input owner.
- Il modello deve essere ibrido: agenti per valutazione qualitativa e CLI per
  validazione, caps, aggregazione, gate e storage.
- MCP read tools possono essere agent-accessible; MCP write/governance tools
  devono essere permission-gated e non agent-autonomous.
- Readiness deve applicarsi alle nuove proposal e alle draft aperte.
- Le proposal gia accettate non devono essere riscritte o invalidate; possono
  essere marcate legacy o valutate retrospettivamente.
- Readiness registry e snapshot sono cache/viste, non fonte primaria.
- Il modello di maturity deve essere utile anche a `p2p next`, che dovrebbe
  suggerire refinement action specifiche e delta verso il target.
- Il conteggio automatico di questioni unresolved deve essere considerato
  indicativo finche non distingue semanticamente domande, decisioni e subtopic.
- Il modello deve evitare burocrazia inutile sulle proposte piccole, ma restare
  esigente sulle proposte product, architetturali e governance-critical.
