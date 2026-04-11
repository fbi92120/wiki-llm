# Explication de la méthode — Wiki LLM
**Projet** : Wiki LLM
**Date** : 2026-04-09
**Contexte** : Bilan après les Étapes 1-3 de la méthode de co-construction

---

> **Note sur la terminologie** : le terme « agent » utilisé dans ce document
> est hérité du vocabulaire de Karpathy et désigne un **outil LLM piloté** —
> pas un agent autonome au sens de l'IA agentique. Chaque opération est
> déclenchée par l'humain, supervisée, et s'arrête après avoir rendu la main.
> L'architecture agentique est une évolution explicitement reportée en **V2-9**
> de `SPECS.md`.

---

## Ce que [Karpathy](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) dit qui a tout structuré

> *"Le wiki est un artefact persistant qui s'enrichit par accumulation. Les renvois entre pages sont déjà en place. Les contradictions ont déjà été signalées. La synthèse reflète déjà tout ce que vous avez lu."*

C'est la phrase centrale. Elle dit que le wiki n'est pas un stockage — c'est une synthèse vivante. Ça a guidé chaque décision.

---

## Les 4 choix concrets tirés de Karpathy

### 1. Trois couches séparées

Karpathy distingue explicitement sources brutes / wiki / schéma. Traduit en :
- `wiki-test/` = sources brutes immuables
- `wiki/` = pages maintenues par le LLM
- `CLAUDE.md` = le schéma qui gouverne le comportement

La règle "sources immuables" vient directement de là — *"le LLM les lit mais ne les modifie jamais"*.

### 2. L'index comme substitut au RAG

Karpathy dit explicitement :

> *"Le LLM lit d'abord l'index pour trouver les pages pertinentes, puis approfondit. Cela fonctionne étonnamment bien à échelle modérée et évite une infrastructure de RAG par embeddings."*

C'est pourquoi le RAG vectoriel a été refusé au MVP. À l'échelle de ce projet — 25 fiches aujourd'hui, quelques centaines demain — l'index suffit. Le RAG est une complexité inutile au MVP.

### 3. Les pages concepts comme cœur du wiki

Karpathy parle de *"pages d'entités, pages de concepts, comparaisons, vue d'ensemble, synthèse"*. Le choix a été de commencer par les concepts plutôt que par des résumés de fiches — parce que c'est là que la valeur s'accumule.

Une page source est un résumé.
Une page concept est une synthèse transversale qui n'existe nulle part ailleurs.

C'est pour ça que `concept-agents-ia.md` était le fichier le plus important à évaluer dans le test — pas `source-deux-philosophies.md`.

### 4. Le journal des mises à jour dans les pages

Karpathy mentionne `log.md` comme journal chronologique global. Le LLM a été guidé pour ajouter un journal local dans `concept-agents-ia.md` — ce qui signale exactement ce qui a changé et pourquoi à chaque ingestion.

C'est la traduction opérationnelle de sa phrase : *"la synthèse reflète déjà tout ce que vous avez lu"*. On sait non seulement ce qu'il y a dans la page, mais comment elle a évolué.

---

## Ce qui a été délibérément mis de côté

Karpathy mentionne Marp, Dataview, qmd, Obsidian Web Clipper. Tout ignoré pour le MVP — il dit lui-même :

> *"Tout ce qui est mentionné ci-dessus est optionnel et modulaire : prenez ce qui vous est utile, ignorez le reste."*

Le principe de non-raccourci de la méthode s'applique ici : on ne construit pas ce dont on n'a pas encore besoin.

---

## Ce que le test a confirmé que Karpathy promettait

Sa phrase la plus forte :

> *"Le rôle de l'humain est de sélectionner les sources, orienter l'analyse, poser de bonnes questions et réfléchir à ce que tout cela signifie. Le rôle du LLM est tout le reste."*

La question transversale qui a émergé dans `concept-agents-ia.md` — *"la stratégie verticale d'Anthropic peut-elle tenir si le calcul est rationné ?"* — illustre exactement ça. Elle n'a pas été posée par l'humain. Le LLM ne l'a pas inventée. Elle a émergé de la juxtaposition de deux sources. C'est le wiki qui travaille.

---

## Bilan des étapes réalisées

### Étape 1 — Dissociation des problèmes ✅

Trois problèmes distincts identifiés :
- **Wiki LLM** — base de connaissance persistante en Markdown, LLM comme mainteneur
- **Migration Evernote** — 8212 notes à extraire, projet séparé créé
- **Recherche dans les pièces jointes** — problème documentaire à part, non traité ici

Décision : commencer le Wiki LLM maintenant avec les 25 fiches YT Extractor existantes.

### Étape 2 — Usage réel ✅ (partielle)

Usage concret identifié : raisonner sur la stratégie IA gen en s'appuyant sur ce qui a été accumulé, sans recommencer depuis zéro à chaque conversation. Produire des interventions, conseiller, former.

### Étape 3 — Test de l'hypothèse technique risquée ✅

Test réalisé sur 3 fiches SamourAI. Trois hypothèses validées :
- Le LLM met à jour sans tout réécrire
- Les liens croisés sont maintenus automatiquement
- Des questions transversales émergent que l'humain n'aurait pas formulées seul

### Étape 4 — Décisions tranchées ✅

Neuf décisions architecturales prises une par une, avec leurs alternatives
nommées et leurs raisons. Le détail complet — tableau des choix, structure
cible du vault, formats de fichiers, workflows d'ingestion, sécurité,
évolutions V2, décisions reportées à d'autres projets — figure dans
`decisions.md`.

Trois lignes de force se dégagent du récapitulatif :

- **Le vault Obsidian comme socle unique** — sources brutes et wiki
  cohabitent dans le même vault pour permettre la vue graphe et la
  navigation visuelle, mais sont strictement séparés en sous-dossiers
  (`YT-Knowledge/` immuable, `wiki/` maintenu par le LLM).
- **Trois niveaux de traçabilité** — log global (`log.md`), journal local
  par concept, fichier dédié aux contradictions (`contradictions.md`).
  Aucun changement ne disparaît.
- **L'humain garde la main sur ce qui entre durablement dans le wiki** —
  workflow d'ingestion supervisé (Workflow A), synthèses validées
  manuellement, contrôle qualité à la demande, périmètre d'écriture
  restreint à `wiki/` uniquement.

### Étape 5 — Constitution complète ✅

La constitution est passée de 6 à **15 règles**. Les 6 premières portent
sur la fidélité aux sources ; les 9 suivantes (7-15) portent sur la
gouvernance des évolutions du wiki et la discipline opérationnelle.

1. Ne jamais réécrire une page existante si une mise à jour partielle suffit
2. Signaler explicitement toute contradiction entre sources
3. « Mes notes » : aspirer verbatim à chaque ingestion, sous le label « Note personnelle : »
4. `index.md` mis à jour à chaque ingestion sans exception
5. Ne jamais inventer un lien non établi par les sources
6. Sources brutes immuables — lire uniquement, jamais modifier
7. Ne jamais supprimer, renommer ou déplacer une page sans instruction explicite
8. Nouvelle source qui contredit : ajouter un angle, jamais écraser
9. Page orpheline détectée : signaler immédiatement
10. Source insuffisante : déplacer dans `wiki/a-traiter/`, log.md label « insuffisant »
11. Périmètre d'écriture : `sources/` `concepts/` `syntheses/` `a-traiter/` uniquement
12. Fin d'ingestion : compte-rendu + tensions + question transversale émergente
13. Template page source : fixe pour Workflow A, déduit pour Workflow B
14. Réponse à une requête : depuis le wiki uniquement, jamais connaissance générale
15. `wiki/` versionné avec git — commit après chaque ingestion

Les règles 1-6 protègent la **fidélité** ; les règles 7-10 protègent
l'**intégrité** du wiki dans le temps ; les règles 11-15 garantissent la
**discipline d'exécution** (périmètre, sortie d'ingestion, origine des
réponses, traçabilité git).

### Étape 6 — Audit des zones grises ✅

Audit effectué avant l'implémentation. Toutes les décisions de l'Étape 4
ont été reprises et leurs zones grises tranchées :

- **Alternatives encore ouvertes** — choix confirmé ou écarté pour chacune.
- **Comportements aux limites non définis** — cas d'erreur, cas de source
  insuffisante, cas de page orpheline — désormais couverts par les règles
  7 à 12 de la constitution.
- **Décisions reportables à V2** — explicitement listées dans `decisions.md`
  (Workflow B, RAG vectoriel, contrôle qualité automatique, etc.) pour
  éviter qu'elles polluent le MVP.

Résultat : aucune zone grise ne reste ouverte au périmètre MVP. Ce qui est
reporté l'est **délibérément**, pas par oubli.

### Étape 7 — Distinguer la pensée du livrable ✅

Appliquée tout au long de la session. Le test initial sur 3 fiches SamourAI
(Étape 3) n'était **pas un livrable** — c'était une validation d'hypothèse.
Les pages wiki générées pendant ce test ont servi à observer le comportement
de l'agent, pas à constituer un wiki de travail. La constitution et les
workflows ont été définis *après* ce test, une fois la pensée suffisamment
avancée.

Règle appliquée : chaque fois qu'une tentation de « produire maintenant »
est apparue, elle a été ramenée à la co-construction.

### Étape 8 — Stratégie de tests ✅

**9 tests de contrat + 1 test smoke**, dérivés des règles testables de la
constitution. Détail complet dans `CLAUDE.md`. Principe :

- Les tests de contrat vérifient qu'une règle de la constitution est
  respectée à l'issue d'une opération (ingestion, requête).
- Le test smoke valide un Workflow A complet de bout en bout sur une fiche
  de référence.
- Si un test échoue, on corrige le comportement de l'agent ou le prompt —
  **jamais** le test.

Les tests concernant le Workflow B (Evernote) sont reportés en V2
(décision V2-8 dans `decisions.md`).

### Étape 9 — Sécurité, git et GitHub ✅

**Angle mort couvert explicitement** — la sécurité n'est plus laissée
à l'interprétation.

- **« Mes notes »** : ne doivent contenir **aucune information
  confidentielle** (nom de client, clé API, donnée personnelle). Responsabilité
  humaine à la source — l'agent reproduit verbatim et ne filtre pas.
- **Sources MVP** : uniquement YT Extractor (données publiques).
- **Notes Evernote** : confidentialité traitée dans le projet *Export Evernote*,
  pas ici.
- **Vault Obsidian sur iCloud** : choix délibéré documenté, pas un oubli.
- **Périmètre d'écriture** (règle 11) : protection structurelle contre les
  dérapages de l'agent hors de `wiki/`.
- **Git local** : `wiki/` versionné, commit après chaque ingestion (règle 15).
  Historique complet, rollback possible, traçabilité des évolutions.
- **GitHub** : publication envisagée pour partage/backup. Avant tout push,
  `.gitignore` doit exclure `.env`, `config.yml`, `*.pyc`, `__pycache__/`,
  `.DS_Store`. Aucune clé ni configuration locale dans l'historique.

---

## Infrastructure mise en place

```
~/.claude/CLAUDE.md              → principes universels (depuis YT Extractor)
~/Projects/CLAUDE.projects.md    → conventions communes
~/Projects/wiki-llm/CLAUDE.md   → constitution Wiki LLM
~/Projects/wiki-llm/wiki-test/  → 3 fiches sources de test
~/Projects/wiki-llm/wiki/       → premier wiki vivant
    index.md
    source-deux-philosophies.md
    source-rationnement.md
    source-computer-use.md
    concept-agents-ia.md
    concept-architecture-confiance.md
```

## Validation par la communauté SamourAI (Discord, 2026-04-08)

Trois retours de membres de la communauté ont confirmé ou enrichi les choix architecturaux.

**axelaxel** — utilisateur Obsidian depuis plusieurs années, connecté à Claude Code :
> *"L'avantage clé : le contexte illimité. Chaque étape documentée dans mon coffre Obsidian me donne un historique complet. Je peux déprécier une version, tracer les mises à jour, retrouver l'état de chaque tâche — sans jamais avoir à tout réexpliquer à l'IA depuis zéro."*

C'est la validation directe de l'architecture retenue : CLAUDE.md comme mémoire persistante, wiki comme contexte accumulé, Obsidian comme interface de lecture. Sa formule *"Claude pour la réflexion, Claude Code pour l'exécution"* est exactement la gouvernance Claude.ai / Claude Code de la méthode.

**axelaxel** — sur le Zettelkasten et Luhmann :
> *"Ce qui ressort des deux livres, c'est un principe central : réduire la friction. On doit pouvoir retrouver n'importe quelle note sans effort, avec une classification libre et simple."*

C'est ce qui a guidé le choix de l'index.md simple plutôt qu'un RAG vectoriel complexe. La friction zéro prime sur la sophistication technique.

**Le SamourAI** — fondateur de la communauté, au moment même de la co-construction :
> *"Depuis quelques jours je m'interroge et je teste le système de Karpathy avec une base LLM wiki personnelle."*

Confirmation externe que la direction choisie est la bonne — pas une expérimentation marginale, mais une piste activement explorée par un acteur de référence sur la stratégie IA.

---

## Bilan chiffré du MVP

| Catégorie | Total |
|---|---|
| Lignes Python | 3 533 |
| Fonctions Python | 77 (42 src/ + 5 orchestrateur + 30 tests) |
| Lignes de specs | 1 286 |

Ratio specs/code : **1 ligne de spec pour 2.7 lignes de Python**. Les specs cadrent, le code exécute. Tests : 20/20 (12 contrats + 8 smoke).

### Mesure du temps de vibe coding

Le temps passé dans Claude Code est mesuré automatiquement par deux hooks
configurés dans `~/.claude/settings.json` :

- **`UserPromptSubmit`** : chaque envoi de prompt enregistre un timestamp
  dans `/tmp/claude-prompt-times`.
- **`Stop`** : à la fin de session, calcule le temps actif = somme des
  intervalles entre prompts consécutifs **inférieurs à 10 minutes**.
  Les pauses longues (nuit, repas, réflexion) sont ignorées.
  Affiche : `Vibe coding: X min (HH:MM -> HH:MM)`.

Ce mécanisme résiste aux sessions laissées ouvertes pendant la nuit —
seul le temps d'interaction réel est compté.

Le temps de co-construction des specs (sur Claude.ai) est mesuré
séparément, par l'humain.

---

## Ce qui reste à faire avant SPECS.md

- Étape 2 suite — usage réel complet (interventions, conseil, formation)
- Rédaction de `SPECS.md` à partir de `CLAUDE.md` + `decisions.md` + `explication-methode.md`
