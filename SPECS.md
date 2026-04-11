# SPECS.md — Wiki LLM
**Auteur** : François Biller
**Date** : 2026-04-09
**Version** : 1.0
**Statut** : prêt pour implémentation Claude Code
**Méthode** : co-construction en 9 étapes — toutes les étapes validées

---

## Bloc 0 — Constitution

Règles non négociables définies avant tout code. Ni le comportement de
l'outil ni son implémentation ne peuvent les violer. Elles ont guidé
chaque décision des Blocs 1 à 5.

### Fidélité aux sources

1. Ne jamais réécrire une page existante si une mise à jour partielle suffit.
2. Signaler explicitement toute contradiction entre sources.
3. « Mes notes » dans les fiches sources : aspirer automatiquement à chaque
   ingestion. Reproduire verbatim, sans modifier ni paraphraser. Afficher
   sous le label `Note personnelle :` dans les pages wiki pour distinguer
   du contenu généré par le LLM.
4. `index.md` mis à jour à chaque ingestion sans exception.
5. Ne jamais inventer un lien non établi par les sources.
6. Sources brutes immuables — lire uniquement, jamais modifier.

### Intégrité du wiki dans le temps

7. Ne jamais supprimer, renommer ou déplacer une page sans instruction
   explicite de l'humain.
8. Nouvelle source qui contredit une page existante : ajouter un angle,
   jamais écraser l'ancien.
9. Page orpheline détectée (sans lien entrant) : signaler immédiatement.
10. Source insuffisante (transcript absent, contenu trop court, structure
    illisible) : déplacer dans `wiki/a-traiter/` et enregistrer dans
    `log.md` avec le label `insuffisant`.

### Discipline d'exécution

11. Périmètre d'écriture : `sources/`, `concepts/`, `syntheses/`,
    `a-traiter/` uniquement — jamais dans `YT-Knowledge/` ni ailleurs
    dans le vault.
12. Fin d'ingestion : produire un compte-rendu incluant les tensions
    détectées et la question transversale émergente.
13. Template de page source : fixe pour Workflow A (YT Extractor), déduit
    pour Workflow B (Evernote, en V2).
14. Réponse à une requête : depuis le wiki uniquement — jamais depuis la
    connaissance générale du LLM.
15. `wiki/` versionné avec git — commit après chaque ingestion.

---

## Bloc 1 — Vue d'ensemble

### Objectif

Maintenir une base de connaissances persistante en fichiers Markdown,
entre l'utilisateur et ses sources brutes. Le LLM ne lit pas les sources
à la demande — il les intègre progressivement dans un wiki structuré qui
s'enrichit à chaque ingestion. La valeur s'accumule ; elle n'est pas
reconstruite à chaque requête.

Cet outil est **piloté** : chaque opération est déclenchée par l'humain,
supervisée, et s'arrête après avoir rendu la main. Ce n'est pas une
architecture agentique — pas de boucle autonome, pas de décision sans
instruction humaine. L'architecture agentique est une évolution explicitement
reportée en V2-9.

### Problème résolu

Un système RAG classique redécouvre le savoir depuis zéro à chaque
question. Le Wiki LLM compile une fois, maintient à jour, et fait
émerger des connexions transversales que l'humain n'aurait pas formulées
seul. C'est la différence entre un index de documents et une synthèse
vivante.

### Périmètre MVP

- Sources : uniquement les fiches produites par YT Knowledge Extractor
  (format `-reduit.md`), données publiques.
- Opérations : ingestion (Workflow A), requête, contrôle qualité à la
  demande.
- Interface LLM : Claude Code (implémentation) piloté par Claude.ai
  (gouvernance).
- Interface lecture : Obsidian.

### Hors périmètre MVP (reporté en V2)

- Workflow B — ingestion notes Evernote (structures hétérogènes,
  projet Export Evernote).
- RAG vectoriel (qmd ou équivalent) — déclenché quand l'index.md ne
  suffit plus, estimé vers ~500 pages.
- Contrôle qualité automatique après chaque batch.
- Recherche dans les pièces jointes (PDFs, Word, Excel).
- Fine-tuning sur la base de connaissance (V3 hypothétique).

### Évolutions V2 identifiées et délibérément reportées

| # | Évolution | Déclencheur |
|---|---|---|
| V2-1 | Workflow B — Evernote | Après migration Evernote |
| V2-2 | `contradictions.md` → page dédiée avec suivi statut | Volume élevé |
| V2-3 | Contrôle qualité automatique post-batch | Volume le justifie |
| V2-4 | RAG vectoriel | ~500 pages |
| V2-5 | Ollama local pour notes administratives | Après Export Evernote |
| V2-6 | Fine-tuning | Mac M4 Pro insuffisant aujourd'hui |
| V2-7 | Règle création dossiers batch Evernote | Projet Export Evernote |
| V2-8 | Tests contrat Workflow B | Projet Export Evernote |
| V2-9 | Architecture agentique : ingestion et contrôle qualité autonomes | Après validation complète du MVP piloté |
| V2-10 | Provider LLM : couche abstraite, Ollama local par défaut | Phase 2 |
| V2-11 | Synthèse LLM : `## Trois idées principales`, `## Liens vers concepts transversaux` | Phase 2 |

---

## Bloc 2 — Architecture

### Stack

- LLM : Claude (Claude.ai + Claude Code en tandem)
- Interface lecture : Obsidian
- Format : Markdown
- Stockage : local, iCloud sync
- Versioning : git local sur `wiki/`
- Vault path : `~/Projects/wiki-llm/wiki/` (ouvert directement comme vault Obsidian)

### Trois couches

```
Sources brutes (YT-Knowledge/)   → immuables, lues jamais modifiées
         ↓
Agent LLM (Claude Code)          → lit les sources, maintient le wiki
         ↓
Wiki (wiki/)                     → artefact persistant, synthèse vivante
```

### Structure cible du vault

```
Obsidian vault/
    YT-Knowledge/               → sources brutes YT Extractor, immuables
    wiki/
        index.md                → catalogue de toutes les pages
        log.md                  → journal chronologique global, append-only
        contradictions.md       → toutes les contradictions détectées
        sources/                → une page par source ingérée
            deux-philosophies.md
            rationnement.md
            computer-use.md
            [...]
        concepts/               → une page par concept transversal
            agents-ia.md        → inclut ## Journal des mises à jour
            architecture-confiance.md
            [...]
        syntheses/              → pages produites à la demande de l'humain
        a-traiter/              → sources insuffisantes en attente
```

### Flux de traitement — Workflow A

```
Fiche YT Extractor (-reduit.md ou native)
    │
    ├── 1. index.md mis à jour en premier
    ├── 2. Page sources/ créée ou mise à jour
    ├── 3. Pages concepts/ créées ou mises à jour
    ├── 4. log.md — entrée ingest ajoutée
    ├── 5. contradictions.md — mis à jour si nécessaire
    ├── 6. Compte-rendu émis (tensions + question transversale)
    └── 7. Commit git
```

### Modes d'ingestion

Trois modes d'invocation du point d'entrée CLI `ingestwiki.py` :

| Mode | Commande | Comportement |
|---|---|---|
| **1 — Fiche unique** | `./ingestwiki.py <fiche.md>` | Ingère une seule fiche. Chemin complet ou relatif. |
| **2 — Dossier** | `./ingestwiki.py ia-et-strategie-le-samourai` | L'argument est le nom du sous-dossier dans `YT-Knowledge/`. L'outil reconstruit le chemin complet depuis `vault_path` défini dans `config.yml`. |
| **3 — Vault complet** | `./ingestwiki.py` (sans argument) | Ingère tout `YT-Knowledge/`. Le chemin est lu depuis `vault_path` dans `config.yml`. |

**Détection automatique du mode :**
- L'argument est un fichier existant → mode 1.
- L'argument n'est pas un fichier mais correspond à un sous-dossier
  de `YT-Knowledge/` → mode 2.
- Pas d'argument → mode 3.

**Comportement batch (modes 2 et 3) :**
- **Skip automatique** : si `wiki/sources/[slug].md` existe déjà,
  la fiche est ignorée (pas de réingestion).
- **1 commit git** en fin de batch (pas un commit par fiche).
- **Compte-rendu global** affiché dans le terminal ET appendé dans
  `log.md` avec le label `batch`.
- Chaque fiche ingérée produit son entrée `ingest` individuelle dans
  `log.md` avant le compte-rendu batch.

### Mécanisme de l'index

`index.md` remplace le RAG vectoriel à petite et moyenne échelle (~500 pages
maximum avant V2-4). Il est le point d'entrée de toute requête.

Structure d'une entrée :

```markdown
## Sources
- [[sources/deux-philosophies]] — type:source — Les deux philosophies d'Anthropic face à l'AGI

## Concepts
- [[concepts/agents-ia]] — type:concept — Agents IA : stratégie, architecture, risques

## Synthèses
- [[syntheses/strategie-verticale]] — type:synthese — Synthèse : stratégie verticale Anthropic
```

Comportement :
- Avant toute requête : lire l'index pour identifier les pages pertinentes.
- Après toute ingestion : mettre à jour l'index en premier.
- Si l'index n'est pas à jour, le wiki est aveugle à lui-même.

### Formats de fichiers

**log.md** — journal global, append-only, préfixe constant :

```
## [YYYY-MM-DD] ingest | nom-source
## [YYYY-MM-DD] batch | label
## [YYYY-MM-DD] query | sujet-de-la-requête
## [YYYY-MM-DD] contradiction | nom-concept | description courte
## [YYYY-MM-DD] qualite | contrôle santé du wiki
## [YYYY-MM-DD] insuffisant | nom-source
## [YYYY-MM-DD] nouveau-dossier | nom-dossier
```

**contradictions.md** — une entrée par contradiction :

```markdown
## [DATE] NOM-CONCEPT
**Source 1** : nom-source — résumé de la position
**Source 2** : nom-source — résumé de la position contradictoire
**Nature** : contradiction directe / tension d'horizon / nuance
**Statut** : ouvert / résolu par [source]
```

**Template page source (Workflow A)** :

```markdown
# Source — [titre court]
**Fiche d'origine** : [[YT-Knowledge/chaine/nom-fiche]]
**Vidéo** : titre | **Chaîne** : nom | **URL** : lien | **Durée** : durée

## Thèse centrale

## Chapitrage inféré

## Carte des idées

## Concepts clés

## Formulations notables

## Questions ouvertes

## Trois idées principales          ← Phase 2 LLM

## Liens vers concepts transversaux ← Phase 2 LLM

## Note personnelle
```

Section exclue du template : `## Sources & références` (liens bruts,
pas de valeur ajoutée dans le wiki).

**Template page concept** :

```markdown
# Concept — [nom]
**Sources** : [[source-1]] [[source-2]] | **Dernière mise à jour** : YYYY-MM-DD

## Définition synthétique

## Angles par source

## Tensions et contradictions

## Questions ouvertes

---

## Journal des mises à jour
- **[date]** — [source] — [ce qui a changé]
```

**Format de réponse à une requête** :

```markdown
**Réponse** : [prose depuis le wiki]
**Pages mobilisées** : [[page-1]] [[page-2]]
**Lacunes détectées** : le wiki ne couvre pas encore [X]
**Fiche suggérée** : [sujet à ingérer pour combler la lacune]
```

**Compte-rendu de fin d'ingestion (règle 12)** :

```markdown
## Compte-rendu — ingestion [nom-source]
**Pages créées** : [liste]
**Pages mises à jour** : [liste]
**Tensions détectées** : [description]
**Question transversale émergente** : [question]
**Commit** : [hash ou message]
```

---

## Bloc 3 — Prompt système

*En anglais. Ce prompt est injecté en tête de chaque session Claude Code
dédiée au Wiki LLM.*

```
You are a wiki maintenance tool. Your sole role is to read source files
and maintain a structured, persistent Markdown knowledge base (the wiki).
You are not an autonomous agent. Every operation is triggered by a human
instruction. You execute, report, and stop. You do not loop, plan ahead,
or take initiative between instructions.

OPERATING PRINCIPLES

You never generate content from general knowledge. Every claim in the wiki
must trace back to an ingested source. If a source does not establish a
connection, you do not create it.

You never rewrite an existing page when a partial update is sufficient.
You add angles, update sections, append to journals. You do not erase history.

You never modify files outside wiki/sources/, wiki/concepts/,
wiki/syntheses/, wiki/a-traiter/. The YT-Knowledge/ directory and all
other vault directories are read-only.

INGESTION WORKFLOW (Workflow A)

When asked to ingest a source file:
1. Read the source file from YT-Knowledge/ — do not modify it.
2. Update index.md FIRST, before any other file.
3. Create or update the corresponding page in wiki/sources/.
   If the source contains a "Mes notes" section, reproduce it verbatim
   under the label "Note personnelle:" — never paraphrase it.
4. Create or update all relevant pages in wiki/concepts/.
   For each concept page, append an entry to its "## Journal des mises à jour"
   section describing what changed and why.
5. Append an entry to log.md with the prefix:
   ## [YYYY-MM-DD] ingest | [source-name]
6. If the source contradicts an existing page, add an entry to
   contradictions.md and add an "## Tensions et contradictions" entry
   to the relevant concept page. Do NOT overwrite the existing angle —
   add the new one alongside it.
7. Emit the end-of-ingestion report:
   - Pages created
   - Pages updated
   - Tensions detected
   - One emerging cross-cutting question
8. Run: git add wiki/ && git commit -m "ingest: [source-name]"

QUERY WORKFLOW

When asked a question:
1. Read index.md to identify relevant pages.
2. Read those pages in full.
3. Answer using only content from those pages. Cite every claim.
4. Format the response as:
   **Réponse** : [prose]
   **Pages mobilisées** : [[page-1]] [[page-2]]
   **Lacunes détectées** : [what the wiki does not yet cover]
   **Fiche suggérée** : [source to ingest to fill the gap]

QUALITY CONTROL WORKFLOW

When asked to run a quality check:
1. Scan all pages in wiki/ for: broken links, orphan pages (no incoming
   links), contradictions without a contradictions.md entry, stale
   summaries (page not updated after a more recent source on the same
   concept), missing cross-references.
2. Report findings grouped by severity.
3. Do not fix anything automatically. Report and wait for human instruction.

HARD LIMITS

- Never invent a timestamp.
- Never fill "Note personnelle:" with generated content.
- Never answer a query from general knowledge — only from wiki pages.
- Never touch YT-Knowledge/ or any file outside the wiki/ write perimeter.
- If a source is insufficient (missing transcript, too short, unreadable
  structure): move it to wiki/a-traiter/, log it with label "insuffisant",
  report to human. Do not attempt to generate a partial page.
- If a page would become orphaned after an operation: signal it before
  proceeding.
```

---

## Bloc 4 — Comportements aux limites

Chaque cas d'erreur ou situation limite est défini ici. Le comportement
est le résultat d'une décision consciente, pas d'un défaut implicite.

| Situation | Comportement |
|---|---|
| Source insuffisante (transcript absent, < 500 mots utiles, structure illisible) | Déplacer dans `a-traiter/`, log label `insuffisant`, signaler à l'humain. Ne jamais générer de page partielle. |
| Contradiction entre la nouvelle source et une page existante | Ajouter un angle dans la page concept (section "Tensions"), entrée dans `contradictions.md`, log label `contradiction`. Ne jamais écraser l'angle précédent. |
| Page orpheline détectée | Signaler immédiatement dans le compte-rendu. Ne pas supprimer ni déplacer sans instruction. |
| Lien cassé détecté (cible absente) | Signaler dans le compte-rendu ou le contrôle qualité. Ne pas créer la page cible automatiquement. |
| Demande de suppression ou renommage d'une page | Refuser sans instruction explicite de l'humain. Signaler la règle 7. |
| "Mes notes" absentes dans la source | La section "Note personnelle:" reste vide dans la page wiki. Ne pas générer de contenu de substitution. |
| Requête dont la réponse n'est pas couverte par le wiki | Répondre honnêtement : "Le wiki ne couvre pas encore ce sujet." Suggérer la fiche à ingérer. Ne jamais compléter depuis la connaissance générale. |
| Commit git échoue | Signaler l'erreur immédiatement. Ne pas ignorer la règle 15 en silence. |
| Source déjà ingérée (fiche déjà présente dans `sources/`) | Signaler le doublon avant de procéder. Attendre confirmation humaine. |
| Dossier `wiki/` absent au démarrage | Créer la structure complète (index.md, log.md, contradictions.md, sous-dossiers), initialiser git, signaler à l'humain avant toute ingestion. |
| Fichier hors périmètre `wiki/` modifié par erreur | Bloquer immédiatement. Signaler la violation de la règle 11. Rollback git si possible. |

---

## Bloc 5 — Stratégie de tests

**9 tests de contrat + 1 test smoke.**

Les tests de contrat vérifient qu'une règle de la constitution est
respectée à l'issue d'une opération. Ils sont écrits avant le code
des modules concernés. Si un test échoue, on corrige le comportement
de l'agent — jamais le test.

Le test smoke valide un Workflow A complet de bout en bout sur une fiche
de référence fixe.

### Tests de contrat

| # | Règle | Contrat à vérifier |
|---|---|---|
| TC-01 | Règle 1 | Après ingestion d'une source, les sections non concernées d'une page concept existante sont inchangées octet par octet. |
| TC-02 | Règle 2 | Une contradiction détectée déclenche une nouvelle entrée dans `contradictions.md` contenant les deux noms de source, la nature et le statut. |
| TC-03 | Règle 3 | Le contenu du champ « Mes notes » de la fiche source est reproduit verbatim sous « Note personnelle : » dans la page wiki correspondante. Diff = 0. |
| TC-04 | Règle 4 | `index.md` porte un timestamp de modification antérieur ou égal à celui de toute autre page modifiée lors de la même ingestion. |
| TC-05 | Règle 5 | Chaque lien `[[cible]]` ou `[texte](cible.md)` dans les pages produites pointe vers un fichier existant dans `wiki/`. |
| TC-06 | Règle 6 | Le hash SHA256 du dossier `YT-Knowledge/` est identique avant et après une ingestion. |
| TC-07 | Règle 11 | `git diff --name-only HEAD` après ingestion ne liste que des chemins sous `wiki/sources/`, `wiki/concepts/`, `wiki/syntheses/`, `wiki/a-traiter/`. |
| TC-08 | Règle 12 | Le compte-rendu de fin d'ingestion contient au moins une question transversale (champ non vide). |
| TC-09 | Règle 14 | Toute phrase d'une réponse à requête cite explicitement une page du `wiki/`. Aucune affirmation sans citation. |

### Test smoke

**Fiche de référence** : la fiche `-reduit.md` produite sur la vidéo
*"La chute d'Anthropic : Le scandale qui révèle les failles de toute
l'industrie de l'IA"* (Le SamourAI) — fiche validée dans YT Extractor V1.

**Condition initiale** : wiki vide (index.md, log.md, contradictions.md
initialisés mais sans contenu).

**Opération** : ingestion complète Workflow A sur la fiche de référence.

**Assertions** :

```
✓ index.md contient une entrée pour la nouvelle page source
✓ wiki/sources/ contient la page créée avec les 5 sections du template
✓ "Note personnelle:" est présente et non vide (la fiche contient des notes)
✓ Au moins une page wiki/concepts/ a été créée ou mise à jour
✓ log.md contient une entrée ## [date] ingest | [nom-source]
✓ git log --oneline montre un commit "ingest: [nom-source]"
✓ Le compte-rendu contient une question transversale non vide
✓ Aucun fichier hors wiki/ dans git diff
```

### Checklist humaine (validation finale)

À effectuer après le test smoke, avant de déclarer l'implémentation validée :

- [ ] Ouvrir le vault dans Obsidian — la vue graphe montre les liens entre pages
- [ ] La page concept créée contient un « Journal des mises à jour »
- [ ] La réponse à une requête test cite uniquement des pages du wiki
- [ ] `git log` montre l'historique attendu
- [ ] Aucun fichier de `YT-Knowledge/` n'apparaît dans `git diff`
- [ ] La checklist sécurité (section suivante) est passée

---

## Sécurité

### Checklist avant le premier commit

- [ ] Le dépôt git est initialisé à la racine du projet (`~/Projects/wiki-llm/`).
  Il versionne `CLAUDE.md`, `decisions.md`, `SPECS.md` et `wiki/` dans le même historique.
- [ ] `.gitignore` contient : `.env`, `config.yml`, `*.pyc`,
  `__pycache__/`, `.DS_Store`
- [ ] `git status` ne montre aucun fichier de `YT-Knowledge/`
- [ ] Aucune clé API ni chemin absolu hardcodé dans les fichiers wiki

### Responsabilités

- **« Mes notes »** : ne doivent contenir aucune information confidentielle
  (nom de client, clé API, donnée personnelle identifiante). Cette
  responsabilité est celle de l'humain à la source — l'agent reproduit
  verbatim et ne filtre pas.
- **Sources MVP** : uniquement YT Extractor (données publiques).
- **Confidentialité notes Evernote** : traitée dans le projet Export Evernote,
  pas ici.
- **Vault sur iCloud** : choix délibéré documenté dans `decisions.md`.
- **Périmètre d'écriture** (règle 11) : protection structurelle contre tout
  débordement de l'agent hors de `wiki/`.

---

## Corrections pré-Phase 2

Corrections et enrichissements à appliquer avant la Phase 2 (synthèse LLM).
Chaque correction est décrite avec le contrat avant/après et les tests impactés.

### Décision 10 — Provider LLM

Couche abstraite `LLMProvider` à intégrer (même pattern que YT Extractor).

| Paramètre | Valeur |
|---|---|
| Défaut local | Ollama + Qwen 3.5 9B |
| Fallback batch V2 | Gemini 2.5 Flash-Lite |
| Fallback qualité | Claude Haiku 4.5 avec prompt caching |
| Configuration | Section `llm` dans `config.yml` |

Changement de provider = une ligne dans `config.yml`. Pas de modification de code.

### Décision 11 — Lecture des fiches natives

**Module** : `reader.py`

| Contrat | Avant | Après |
|---|---|---|
| Chapitrage inféré | Ignoré | Extrait dans `fiche.chapitrage_infere: str` |
| Placeholder `*(espace libre)*` | Retourné tel quel | Retourné comme `""` (chaîne vide) |
| Format attendu | `-reduit.md` ou natif | Natif uniquement en production |

**Tests impactés** :
- TC-03 : vérifier que `*(espace libre)*` → Note personnelle vide (pas le placeholder)
- Nouveau test : vérifier que `chapitrage_infere` est extrait correctement

### Décision 12 — Nouveau template page source wiki

**Module** : `source_writer.py`

Sections copiées verbatim depuis la fiche :

| Section | Statut |
|---|---|
| `## Thèse centrale` | Déjà présent |
| `## Chapitrage inféré` | **Nouveau** |
| `## Carte des idées` | **Nouveau** |
| `## Concepts clés` | Déjà présent |
| `## Formulations notables` | **Nouveau** |
| `## Questions ouvertes` | **Nouveau** |
| `## Note personnelle` | Déjà présent |

Sections réservées Phase 2 LLM (placeholder) :
- `## Trois idées principales`
- `## Liens vers concepts transversaux`

Lien fiche complète : `**Fiche d'origine** : [[YT-Knowledge/chaine/nom-fiche]]`

Section exclue : `## Sources & références`.

**Tests impactés** :
- TC-03 (verbatim) : inchangé
- Test smoke assertion 2 : mettre à jour la liste des sections du template

### Décision 13 — wiki/questions/

**Module** : `source_writer.py`

Nouveau dossier `wiki/questions/` avec fichier `toutes-les-questions.md`
(append-only).

Format :
```markdown
## [titre court de la source]
[[sources/slug-source]]
- question 1 verbatim
- question 2 verbatim
- question 3 verbatim
```

Alimenté par `source_writer.py` à chaque ingestion.

**Règle 16** (à ajouter à CLAUDE.md) :
`wiki/questions/toutes-les-questions.md` append-only. Chaque ingestion
y ajoute les questions ouvertes verbatim avec lien vers la page source wiki.

**Tests à créer** :
- TC-13 : après ingestion, `toutes-les-questions.md` contient les questions
  de la fiche avec le lien `[[sources/slug]]`
- TC-07 (R11) : ajouter `questions/` au périmètre d'écriture autorisé

### Bug R11 — ingest.log

**Module** : `validator.py`

Exclure `ingest.log` du check R11 (périmètre d'écriture). C'est un log
technique, pas du contenu wiki.

| Contrat | Avant | Après |
|---|---|---|
| `ingest.log` modifié | Warning R11 | Ignoré silencieusement |

**Test impacté** : TC-07 — ajouter `ingest.log` à la liste des fichiers autorisés.

### Ré-ingestion après corrections

Une fois toutes les corrections appliquées :

1. Effacer `wiki/sources/`, `wiki/concepts/`, `wiki/questions/`
2. Vider `index.md`, `log.md`, `contradictions.md` (remettre à l'état bootstrap)
3. Ré-ingérer les sources existantes depuis `YT-Knowledge/` (`./ingestwiki.py`)
4. Vérifier 23/23 tests + validation complète
5. Commit unique : `reingest: post-corrections Phase 2`

---

## Séquence d'implémentation pour Claude Code

Ordre à respecter. Un prompt = un module = vérification avant de passer
au suivant.

```
Prompt 1  — Bootstrap : structure wiki/ complète + fichiers initiaux
            (index.md vide, log.md vide, contradictions.md vide,
            sous-dossiers, .gitignore, git init)
Prompt 2  — Lecteur de sources (lecture fiche -reduit.md, extraction
            champs, détection "Mes notes")
Prompt 3  — Générateur de pages sources/ (template Workflow A)
Prompt 4  — Générateur / metteur à jour de pages concepts/
            (template concept, journal des mises à jour)
Prompt 5  — Gestionnaire index.md (mise à jour catalogue)
Prompt 6  — Gestionnaire log.md (append entrée)
Prompt 7  — Gestionnaire contradictions.md (détection + entrée)
Prompt 8  — Tests de contrat TC-01 à TC-09
            ← écrits AVANT les modules validateur et orchestrateur
Prompt 9  — Validateur (vérifie les règles testables post-ingestion)
Prompt 10 — Orchestrateur Workflow A (appelle les modules dans l'ordre,
            produit le compte-rendu, fait le commit git)
Prompt 11 — Test smoke
Prompt 12 — README.md (anglais) + README.fr.md (français)
```

---

*SPECS.md produit à partir de CLAUDE.md + decisions.md + explication-methode.md*
*Méthode : co-construction en 9 étapes — METHODE_SPECS_CO-CONSTRUCTION.md*
*Prêt pour le premier prompt Claude Code.*
