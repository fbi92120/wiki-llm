# Décisions d'architecture — Wiki LLM
**Projet** : Wiki LLM
**Date** : 2026-04-09
**Étape** : 4 — Décisions avant SPECS.md

---

## Décisions tranchées

| # | Décision | Choix retenu | Raison |
|---|---|---|---|
| 1 | Structure des dossiers | Tout dans le vault Obsidian | Vue graphe complète, sources et wiki reliés visuellement |
| 2 | Convention de nommage | Dossiers par type dans `wiki/` | Séparation claire sources brutes / wiki |
| 3 | Nommage des pages wiki | Sous-dossiers `sources/` `concepts/` `syntheses/` | Volume prévu élevé, structure qui tient dans la durée |
| 4 | Gestion du log | Log global + journal local dans chaque concept | Deux niveaux complémentaires : chronologie globale + historique par page |
| 5 | Contradictions | Page concept + log + `contradictions.md` | Traçabilité complète à trois niveaux |
| 6 | Ingestion | Workflow A (YT Extractor) maintenant, Workflow B (Evernote) en V2 | Structures hétérogènes — workflows distincts |
| 7 | Outputs | L'humain décide ce qui va dans `syntheses/` | L'humain exerce son jugement sur ce qui mérite d'entrer dans le wiki |
| 8 | Contrôle qualité | À la demande | Suffisant au MVP, complexité inutile en automatique |
| 9 | Sécurité | Claude Code écrit uniquement dans `wiki/` | Protéger `YT-Knowledge/` et le reste du vault |

---

## Structure cible du vault Obsidian

```
Obsidian vault/
    YT-Knowledge/               → sources brutes YT Extractor, immuables
    wiki/
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
        syntheses/              → pages produites à la demande de l'humain
```

---

## Format du log global

Chaque entrée commence par un préfixe constant pour faciliter la recherche :

```
## [2026-04-09] ingest | deux-philosophies
## [2026-04-09] ingest | rationnement
## [2026-04-09] ingest | computer-use
## [2026-04-09] contradiction | concept-agents-ia | tension stratégie vs énergie
## [2026-04-09] query | stratégie verticale Anthropic
## [2026-04-09] qualite | contrôle santé du wiki
```

---

## Format de contradictions.md

```markdown
## [DATE] NOM-CONCEPT
**Source 1** : nom-source — résumé de la position
**Source 2** : nom-source — résumé de la position contradictoire
**Nature** : contradiction directe / tension d'horizon / nuance
**Statut** : ouvert / résolu par [source]
```

---

## Workflows d'ingestion

### Workflow A — Fiches YT Extractor (MVP)
1. Copier la fiche `-reduit.md` dans `YT-Knowledge/` si pas déjà présente
2. Demander au LLM d'ingérer la fiche
3. Le LLM met à jour `index.md` en premier
4. Le LLM crée ou met à jour les pages `sources/` et `concepts/` concernées
5. Le LLM ajoute une entrée dans `log.md`
6. Le LLM met à jour `contradictions.md` si nécessaire
7. L'humain évalue le résultat et décide si une synthèse mérite d'être sauvegardée

### Workflow B — Notes Evernote (V2)
À définir dans le projet Export Evernote après la migration.
Structure hétérogène — workflow distinct du Workflow A.

---

## Sécurité — règles inscrites dans la constitution

- Claude Code écrit **uniquement** dans `wiki/` — jamais dans `YT-Knowledge/` ni ailleurs dans le vault
- Les sources brutes sont immuables — Claude Code lit, jamais modifie
- Le vault Obsidian est sur iCloud — choix délibéré documenté ici, pas un oubli
- Pour le MVP : sources uniquement issues de YT Extractor (données publiques)
- Notes Evernote : confidentialité traitée dans le projet Export Evernote

---

## Évolutions prévues en V2

Ces décisions ont été identifiées pendant l'Étape 4 et délibérément reportées.

| # | Évolution | Déclencheur |
|---|---|---|
| V2-1 | Workflow B — ingestion notes Evernote | Après migration Evernote |
| V2-2 | `contradictions.md` → page dédiée avec suivi statut | Quand les contradictions se multiplient |
| V2-3 | Contrôle qualité automatique après chaque batch | Quand le volume le justifie |
| V2-4 | RAG vectoriel (qmd ou équivalent) | Quand l'index.md ne suffit plus (~500 pages) |
| V2-5 | Ollama en local pour notes administratives | Après projet Export Evernote |
| V2-6 | Fine-tuning sur la base de connaissance | V3 hypothétique, Mac M4 Pro insuffisant aujourd'hui |
| V2-7 | Règle création dossiers batch Evernote | Projet Export Evernote |
| V2-8 | Tests contrat Workflow B | Projet Export Evernote |
| V2-9 | Architecture agentique : ingestion et contrôle qualité autonomes | Après validation complète du MVP piloté |

---

## Décisions reportées à d'autres projets

- **Recherche dans les pièces jointes** (PDFs, Word, Excel) → projet Export Evernote
- **Migration des 8212 notes Evernote** → projet Export Evernote
- **Confidentialité des notes personnelles** → projet Export Evernote
