# Retour d'expérience — YT Knowledge Extractor
## Document de transmission vers le projet Wiki LLM

**Auteur** : François Biller  
**Date** : 2026-04-09  
**Repo** : https://github.com/fbi92120/yt-knowledge-extractor  
**Statut** : Projet V1 terminé et validé

---

## 1. Ce que l'appli fait

Script CLI Python (`python extract.py [URL]`) qui prend une URL YouTube,
extrait le transcript horodaté et les métadonnées via API, envoie le tout
à un LLM, et génère une fiche de connaissance structurée en Markdown
sauvegardée dans un vault Obsidian ou un dossier local.

Une vidéo → une fiche. Traitement unitaire, pas de batch.

---

## 2. Architecture retenue

### Principe directeur
Flux de données linéaire, modules indépendants, orchestrateur passif.

```
URL
 │
 ├── src/metadata.py      → titre, chaîne, durée, description, chapitres natifs
 ├── src/transcript.py    → liste de segments {start, text}
 │
 ├── src/llm/
 │   ├── base.py          → interface abstraite LLMProvider
 │   └── groq.py          → implémentation Groq (provider par défaut)
 │       [+ anthropic.py, openai.py, ollama.py — stubs]
 │
 ├── src/generator.py     → orchestre metadata + transcript + LLM → fiche brute
 ├── src/validator.py     → vérifie la structure de la fiche, retourne warnings
 ├── src/writer.py        → génère slug, construit chemin, écrit le fichier
 │
 └── extract.py           → point d'entrée CLI — orchestration pure, zéro logique métier
```

### Décision clé : orchestrateur passif
`extract.py` ne contient aucune logique métier. Il appelle les modules
dans l'ordre, transmet les données, gère les erreurs terminales.
Toute la logique est dans `src/`. Cette décision prépare une V3 SaaS
sans migration : on branche une autre interface sur `src/` sans toucher au code.

### Couche LLM abstraite
`base.py` définit l'interface `LLMProvider`. Chaque provider implémente
`generate(system_prompt, user_prompt) -> LLMResponse`.
Changer de provider = une ligne dans `config.yml`. Pas de modification de code.

---

## 3. Décisions clés et leurs raisons

| Décision | Option retenue | Raison |
|---|---|---|
| Transcript → LLM | Envoi complet en une fois | Cohérence globale. Le chunking fragmente l'analyse. |
| Contexte insuffisant | Blocage explicite | Ne jamais tronquer silencieusement — constitutionnel |
| Fiche incomplète | Sauvegarder + avertir | Mieux qu'un blocage qui perd le travail |
| Provider par défaut | Gemini (free tier 1M tokens) | Groq free tier ~6k tokens/requête — inutilisable vidéos > 5 min |
| Section "Mes notes" | Toujours vide | Si le LLM la remplit, c'est lui qui retient, pas l'utilisateur |
| Sources | Filtrées strictement | Auteur ou titre identifiable uniquement — pas de liens génériques |
| Timestamps | Jamais inventés | Règle constitutionnelle n°1 — un lien approximatif est pire qu'absent |
| Slug | python-slugify | ASCII garanti, portable tous systèmes, toutes langues |

---

## 4. Constitution — les 8 règles non négociables

Ces règles ont été définies **avant** le code. Elles ont guidé chaque
décision d'implémentation. Le validateur les vérifie automatiquement.

1. Jamais inventer un timestamp
2. Citations textuelles ou absentes — jamais paraphrasées
3. "Mes notes" toujours vide — jamais générée par le LLM
4. Définitions de l'auteur uniquement — jamais génériques
5. Sources filtrées strictement — auteur ou titre identifiable
6. Transcript complet envoyé en une seule fois — pas de chunking
7. Fiche incomplète : sauvegarder + avertissement en tête
8. Contexte insuffisant : bloquer avec message explicite

**Leçon** : sans constitution définie avant le code, ces règles auraient
été découvertes comme des bugs en cours de route. Définies en amont,
elles deviennent des contraintes de conception qui simplifient les décisions.

---

## 5. Séquence d'implémentation suivie

```
Prompt 1  — Bootstrap : structure complète + fichiers vides + docstrings
Prompt 2  — src/transcript.py
Prompt 3  — src/metadata.py
Prompt 4  — src/llm/base.py + src/llm/groq.py
Prompt 5  — src/generator.py
Prompt 6  — src/validator.py
Prompt 7  — src/writer.py
Prompt 8  — extract.py (orchestrateur)
Prompt 9  — tests/
Prompt 10 — README.md + README.fr.md
```

**Règle validée** : l'orchestrateur en avant-dernier. On ne câble
que quand tous les modules qu'il appelle existent et sont testés.

---

## 6. Ce qui a bien fonctionné

**Le prompt 1 squelette complet** : créer tous les fichiers vides avec
docstrings avant d'écrire une ligne de logique force à valider
l'architecture complète en amont. Les incohérences de structure
sont visibles immédiatement, avant que le code les cache.

**1 prompt = 1 module = 1 livrable testable** : chaque module
validé indépendamment avant de passer au suivant. Aucune régression
silencieuse. Les bugs sont localisés immédiatement.

**La couche LLM abstraite** : changer Groq pour Gemini (décision
prise après avoir découvert la limite du free tier) a demandé
30 minutes, pas une réécriture.

**La constitution en amont** : le validateur est simple à écrire
quand les règles sont déjà définies. Il n'invente rien — il vérifie
ce qui a été décidé.

---

## 7. Ce qui aurait dû être fait différemment

**Tests de contrat avant les modules** : les tests ont été écrits
après le code. La méthode cible (documentée dans CLAUDE.md) prévoit
d'écrire les tests de contrat avant les modules à contrat fixe.
Ce projet a servi à extraire cette règle — elle n'était pas
appliquée dès le départ.

**Provider par défaut mal choisi** : Groq était le provider initial.
La limite du free tier (~6k tokens/requête) n'a été découverte
qu'au test réel. Tester l'hypothèse technique risquée avant
de spécifier (Étape 3 de la méthode) aurait évité ce pivot.

**Python 3.9 sur Mac système** : la syntaxe `str | None` (Python 3.10+)
a causé des erreurs répétées. Solution systématique : `from __future__ import annotations`
en tête de chaque fichier. Migration vers Python 3.12 prévue post-projet.

---

## 8. Patterns réutilisables pour le Wiki LLM

### Pattern : flux de données directionnel
```
Sources brutes → Traitement → Validation → Écriture
```
Ne jamais mélanger les couches. Le module qui lit ne valide pas.
Le module qui valide n'écrit pas. Chaque module a une responsabilité unique.

### Pattern : interface abstraite pour les providers externes
Si le Wiki LLM appelle un LLM, isoler l'appel derrière une interface.
Réutiliser directement `src/llm/base.py` de YT Extractor comme modèle —
ou l'importer si les projets partagent la même stack.

### Pattern : constitution avant code
Définir les règles non négociables de l'output **avant** d'écrire
le premier module. Pour le Wiki LLM : quelles règles sur la mise à jour
des pages existantes ? Sur les contradictions entre sources ?
Sur ce que le LLM ne doit jamais faire automatiquement ?

### Pattern : validateur séparé
Ne pas mélanger génération et validation. Le générateur produit,
le validateur vérifie. Cela permet de sauvegarder avec avertissement
plutôt que de bloquer — décision de constitution à prendre en amont.

### Pattern : orchestrateur passif
Le point d'entrée (CLI, API, interface web) ne contient aucune logique.
Il appelle les modules dans l'ordre. La logique est dans les modules.
Cette décision est gratuite à prendre en amont et coûteuse à refaire après.

### Différence structurelle avec le Wiki LLM
YT Extractor est **stateless** : chaque exécution est indépendante.
Le Wiki LLM est **stateful** : chaque ingestion modifie un état persistant
(les fichiers Markdown du wiki). Cette différence change tout — notamment
la gestion des conflits, des mises à jour, et de la cohérence entre pages.
C'est la première décision d'architecture à trancher dans SPECS.md.

---

*Ce document est destiné à être attaché au projet Claude.ai Wiki LLM*
*comme référence de méthode et d'architecture issue du projet précédent.*
