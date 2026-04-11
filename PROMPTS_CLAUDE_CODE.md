# Prompts Claude Code — Wiki LLM
**Date** : 2026-04-09
**Ordre** : exécuter dans la séquence ci-dessous, un prompt à la fois

---

## Phase 0 — Corrections de terminologie (avant toute implémentation)

### Prompt 0-A — CLAUDE.md

Dans `CLAUDE.md`, section "Contexte du projet" :
- Remplace "Agent LLM qui maintient" par "Outil LLM piloté qui maintient"
- Ajoute une ligne : "Architecture agentique : reportée en V2-9 — voir SPECS.md."

### Prompt 0-B — decisions.md

Dans `decisions.md`, tableau des évolutions V2 :
- Ajoute la ligne : `| V2-9 | Architecture agentique : ingestion et contrôle qualité autonomes | Après validation complète du MVP piloté |`

### Prompt 0-C — explication-methode.md

Dans `explication-methode.md`, ajoute une note en début de document,
après le titre et avant la première section, avec ce contenu :

> **Note sur la terminologie** : le terme "agent" utilisé dans ce document
> est hérité du vocabulaire de Karpathy et désigne un outil LLM piloté —
> pas un agent autonome au sens de l'IA agentique. Chaque opération est
> déclenchée par l'humain, supervisée, et s'arrête après avoir rendu la main.
> L'architecture agentique est une évolution explicitement reportée en V2-9
> de SPECS.md.

---

## Phase 1 — Implémentation (séquence définie dans SPECS.md Bloc 5)

### Prompt 1 — Bootstrap

Crée la structure complète de `wiki/` :
- `index.md` initialisé (catalogue vide avec les trois catégories)
- `log.md` initialisé (journal vide)
- `contradictions.md` initialisé (fichier vide avec le format d'entrée en commentaire)
- Sous-dossiers : `sources/`, `concepts/`, `syntheses/`, `a-traiter/`
- `.gitignore` : `.env`, `config.yml`, `*.pyc`, `__pycache__/`, `.DS_Store`
- `git init` + premier commit "init: structure wiki"

### Prompt 2 — Lecteur de sources

Écris `src/reader.py` :
- Lit une fiche `-reduit.md` depuis `YT-Knowledge/`
- Extrait les champs : titre, URL, chaîne, durée, thèse centrale,
  concepts clés, trois idées principales, contenu "Mes notes"
- Retourne un objet structuré
- Contrat : si "Mes notes" est absent, retourner champ vide — jamais None

### Prompt 3 — Générateur page source

Écris `src/source_writer.py` :
- Prend l'objet structuré de reader.py
- Génère la page `wiki/sources/[slug].md` selon le template Workflow A
- "Mes notes" → reproduit verbatim sous "Note personnelle :"
- Contrat : si la page existe déjà, signaler doublon et attendre confirmation

### Prompt 4 — Générateur / metteur à jour page concept

Écris `src/concept_writer.py` :
- Crée une page `wiki/concepts/[slug].md` si elle n'existe pas
- Si elle existe : ajoute un angle dans "Angles par source",
  appende au "Journal des mises à jour" — ne réécrit jamais les sections existantes
- Contrat : les sections non concernées sont inchangées octet par octet

### Prompt 5 — Gestionnaire index.md

Écris `src/index_manager.py` :
- Ajoute ou met à jour une entrée dans `index.md`
- Organisé par catégorie : Sources | Concepts | Synthèses
- Contrat : appelé en premier dans tout workflow d'ingestion

### Prompt 6 — Gestionnaire log.md

Écris `src/log_manager.py` :
- Appende une entrée dans `log.md` avec le préfixe constant
- Types : `ingest`, `query`, `contradiction`, `qualite`, `insuffisant`, `nouveau-dossier`
- Contrat : append-only, jamais de modification d'une entrée existante

### Prompt 7 — Gestionnaire contradictions.md

Écris `src/contradiction_manager.py` :
- Détecte une contradiction entre une nouvelle source et une page concept existante
- Ajoute une entrée dans `contradictions.md`
- Ajoute un angle dans la section "Tensions et contradictions" de la page concept
- Contrat : jamais écraser l'angle précédent

### Prompt 8 — Tests de contrat TC-01 à TC-09

Écris `tests/test_contract.py` avec les 9 tests de contrat définis
dans SPECS.md Bloc 5. Ces tests sont écrits AVANT les modules
validateur et orchestrateur. Si un test échoue, corriger le module
concerné — jamais le test.

### Prompt 9 — Validateur

Écris `src/validator.py` :
- Vérifie les règles testables après une ingestion
- Retourne une liste de warnings, pas d'exceptions
- Les tests TC-01 à TC-09 doivent passer

### Prompt 10 — Orchestrateur Workflow A

Écris `ingestwiki.py` (point d'entrée CLI) :
- Appelle les modules dans l'ordre défini dans SPECS.md Bloc 2
- Zéro logique métier dans l'orchestrateur — tout est dans `src/`
- Produit le compte-rendu de fin d'ingestion (tensions + question transversale)
- Fait le commit git en dernier

### Prompt 11 — Test smoke

Écris `tests/test_smoke.py` :
- Ingestion complète de la fiche de référence (La chute d'Anthropic)
- Vérifie les 8 assertions définies dans SPECS.md Bloc 5

### Prompt 12 — Documentation

Écris `README.md` (anglais) et `README.fr.md` (français).

---

Chemin wiki/ : ~/Projects/wiki-llm/wiki/ — local, versionné avec git. Sync vers le vault Obsidian : étape ultérieure, non bloquante pour le MVP.
