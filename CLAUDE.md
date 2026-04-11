# CLAUDE.md — Wiki LLM
# Emplacement : ~/Projects/wiki-llm/CLAUDE.md
# Portée : projet Wiki LLM uniquement

---

## Contexte du projet

Outil LLM piloté qui maintient une base de connaissances persistante
en fichiers Markdown, entre l'utilisateur et ses sources brutes.
Concept source : [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

Architecture agentique : reportée en V2-9 — voir SPECS.md.

Statut : spécifications validées — prêt pour implémentation.

---

## Constitution — règles spécifiques au Wiki LLM

1. Ne jamais réécrire une page existante si une mise à jour partielle suffit
2. Signaler explicitement toute contradiction entre sources
3. "Mes notes" dans les fiches sources : aspirer automatiquement
   à chaque ingestion. Reproduire tel quel sans modifier ni paraphraser.
   Afficher sous le label "Note personnelle :" dans les pages wiki
   pour distinguer du contenu généré par le LLM.
4. index.md mis à jour à chaque ingestion sans exception
5. Ne jamais inventer un lien non établi par les sources
6. Sources brutes immuables — lire uniquement, jamais modifier
7. Ne jamais supprimer, renommer ou déplacer une page sans instruction
   explicite de l'humain
8. Nouvelle source qui contredit une page existante : **ajouter un angle**,
   jamais écraser l'ancien
9. Page orpheline détectée (sans lien entrant) : **signaler immédiatement**
10. Source insuffisante : déplacer dans `wiki/a-traiter/` et enregistrer
    dans `log.md` avec le label `insuffisant`
11. Périmètre d'écriture : `sources/`, `concepts/`, `syntheses/`,
    `a-traiter/`, `questions/` uniquement — jamais dans `YT-Knowledge/`
    ni ailleurs dans le vault
12. Fin d'ingestion : produire un **compte-rendu** incluant les tensions
    détectées et la question transversale émergente
13. Template de page source : **fixe** pour Workflow A (YT Extractor),
    **déduit** pour Workflow B (Evernote, en V2)
14. Réponse à une requête : depuis le **wiki uniquement**, jamais depuis
    la connaissance générale du LLM
15. `wiki/` **versionné avec git** — commit après chaque ingestion
16. `wiki/questions/toutes-les-questions.md` — **append-only**.
    Chaque ingestion y ajoute les questions ouvertes verbatim
    avec lien `[[sources/slug]]` vers la page source wiki.

---

## Mécanisme de l'index

index.md est le fichier central du wiki. Il remplace le RAG vectoriel
à petite et moyenne échelle.

Rôle :
- Catalogue de toutes les pages du wiki
- Une entrée par page : lien, type (source/concept/synthèse),
  résumé en une phrase
- Organisé par catégorie : Sources | Concepts | Synthèses
- Mis à jour à chaque ingestion sans exception

Comportement attendu :
- Avant toute requête : lire l'index pour identifier les pages pertinentes
- Après toute ingestion : mettre à jour l'index en premier
- Si l'index n'est pas à jour, le wiki est aveugle à lui-même

## Documents de référence à lire au démarrage de chaque session

- CLAUDE.md — constitution et règles du wiki
- decisions.md — décisions d'architecture et évolutions V2
- explication-methode.md — pourquoi les choix architecturaux ont été faits
- wiki/index.md — état courant du wiki, toutes les pages disponibles

## Vault Obsidian

~/Projects/wiki-llm/wiki/ — ouvert directement comme vault Obsidian
via "Open folder as vault". Git et Obsidian cohabitent sans friction.

## Stack

- LLM : Claude (Claude.ai + Claude Code en tandem)
- Interface lecture : Obsidian (vault = wiki/)
- Format : Markdown
- Stockage : local, versionné avec git

---

## Structure cible du vault

```
wiki/   ← vault Obsidian (~/Projects/wiki-llm/wiki/)
    index.md                → catalogue de toutes les pages
    log.md                  → journal chronologique global, append-only
    contradictions.md       → toutes les contradictions détectées
    sources/
        deux-philosophies.md
        rationnement.md
        computer-use.md
        [...]
    concepts/
        agents-ia.md        → inclut ## Journal des mises à jour
        architecture-confiance.md
        [...]
    a-traiter/              → sources insuffisantes en attente
    syntheses/              → pages produites à la demande de l'humain
    questions/
        toutes-les-questions.md → append-only, questions ouvertes de chaque source
```

Claude Code n'a le droit d'écrire **que** dans `wiki/`.
Les fiches sources brutes (wiki-test/, YT-Knowledge/) sont en lecture seule.

---

## Format de log.md

Journal global, append-only. Chaque entrée commence par un préfixe constant
pour permettre une recherche simple avec les outils Unix :

```
## [2026-04-09] ingest | deux-philosophies
## [2026-04-09] ingest | rationnement
## [2026-04-09] ingest | computer-use
## [2026-04-09] contradiction | concept-agents-ia | tension stratégie vs énergie
## [2026-04-09] query | stratégie verticale Anthropic
## [2026-04-09] qualite | contrôle santé du wiki
```

Types d'événements : `ingest`, `batch`, `query`, `contradiction`, `qualite`,
`insuffisant`, `nouveau-dossier`.

---

## Format de contradictions.md

Une entrée par contradiction détectée :

```markdown
## [DATE] NOM-CONCEPT
**Source 1** : nom-source — résumé de la position
**Source 2** : nom-source — résumé de la position contradictoire
**Nature** : contradiction directe / tension d'horizon / nuance
**Statut** : ouvert / résolu par [source]
```

---

## Template de page source (Workflow A)

```markdown
# Source — [titre court]
**Fiche d'origine** : [[YT-Knowledge/chaine/nom-fiche]]
**Vidéo** : titre | **Chaîne** : nom | **URL** : lien | **Durée** : durée

## Thèse centrale                   ← verbatim

## Chapitrage inféré                ← verbatim

## Carte des idées                  ← verbatim

## Concepts clés                    ← verbatim

## Formulations notables            ← verbatim

## Questions ouvertes               ← verbatim

## Trois idées principales          ← réservé Phase 2 LLM

## Liens vers concepts transversaux ← réservé Phase 2 LLM

## Note personnelle                 ← verbatim
```

Section exclue : `## Sources & références` (liens bruts, pas de valeur
ajoutée dans le wiki).

---

## Template de page concept

```markdown
# Concept — [nom]
**Sources** : liens | **Dernière mise à jour** : date

## Définition synthétique

## Angles par source

## Tensions et contradictions

## Questions ouvertes

---

## Journal des mises à jour
- **[date]** — [source] — [ce qui a changé]
```

---

## Format de réponse à une requête

```markdown
**Réponse** : [prose depuis le wiki]
**Pages mobilisées** : [[page-1]] [[page-2]]
**Lacunes détectées** : le wiki ne couvre pas encore [X]
**Fiche suggérée** : [sujet à ingérer]
```

---

## Workflow A — Ingestion d'une fiche YT Extractor (MVP)

1. Copier la fiche `-reduit.md` dans `YT-Knowledge/` si pas déjà présente
2. Demander au LLM d'ingérer la fiche
3. Le LLM met à jour `index.md` **en premier**
4. Le LLM crée ou met à jour les pages `sources/` et `concepts/` concernées
5. Le LLM ajoute une entrée dans `log.md`
6. Le LLM met à jour `contradictions.md` si nécessaire
7. Le LLM produit le **compte-rendu** de fin d'ingestion (règle 12)
8. Le LLM fait un **commit git** (règle 15)
9. L'humain évalue et décide si une synthèse mérite d'être
   sauvegardée dans `syntheses/`

Workflow B (notes Evernote) : reporté en V2 — structure hétérogène,
workflow distinct à définir après la migration Evernote.

---

## Stratégie de tests

**9 tests de contrat + 1 test smoke**, dérivés des règles testables
de la constitution.

### Tests de contrat

| # | Règle testée | Contrat |
|---|---|---|
| 1 | Règle 1 | Après ingestion, les sections non concernées d'une page existante sont **inchangées octet par octet** |
| 2 | Règle 2 | Une tension/contradiction détectée déclenche une nouvelle entrée dans `contradictions.md` |
| 3 | Règle 3 | Le contenu de « Mes notes » de la source est reproduit **verbatim** sous « Note personnelle : » dans la page wiki |
| 4 | Règle 4 | `index.md` est mis à jour **avant** toute autre page (timestamp ou ordre d'écriture) |
| 5 | Règle 5 | Chaque lien `[texte](cible.md)` pointe vers un fichier existant dans `wiki/` |
| 6 | Règle 6 | Hash du dossier `YT-Knowledge/` **inchangé** après une ingestion |
| 7 | Règle 11 | `git diff` après ingestion ne montre des changements **que** dans `wiki/sources|concepts|syntheses|a-traiter/` |
| 8 | Règle 12 | Le compte-rendu de fin d'ingestion contient au moins une **question transversale** |
| 9 | Règle 14 | Toute affirmation d'une réponse à requête cite une page du `wiki/` (aucune connaissance externe) |

### Test smoke

Ingestion complète d'une fiche `-reduit.md` de référence → vérifie que
tous les effets du Workflow A sont produits : `index.md` mis à jour,
page source créée, concepts concernés mis à jour, entrée dans `log.md`,
commit git, compte-rendu émis.

---

## Sécurité

- **"Mes notes"** : ne doivent contenir **aucune information confidentielle**
  (nom de client, clé API, donnée personnelle identifiante). Cette
  responsabilité est celle de l'humain à la source — l'agent ne filtre pas.
- Les sources MVP (YT Extractor) ne contiennent que des **données publiques**.
- Confidentialité des notes Evernote : traitée dans le projet *Export Evernote*.
- Le vault Obsidian est sur **iCloud** — choix délibéré, documenté dans
  `decisions.md`, pas un oubli.
- Claude Code ne sort pas du périmètre d'écriture défini par la règle 11.

---

## .gitignore

Le dépôt git de `wiki/` doit exclure a minima :

```
.env
config.yml
*.pyc
__pycache__/
.DS_Store
```

Aucun secret ni configuration locale ne doit entrer dans l'historique git.
