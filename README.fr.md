# Wiki LLM

Outil LLM piloté qui maintient une base de connaissances persistante en Markdown à partir de fichiers sources. Contrairement aux systèmes RAG classiques qui redécouvrent le savoir à chaque requête, Wiki LLM compile une fois, maintient dans le temps, et fait émerger des connexions transversales que l'utilisateur n'aurait pas formulées seul.

Ce n'est **pas** un agent autonome. Chaque opération est déclenchée par l'humain, supervisée, et s'arrête après avoir rendu la main. L'architecture agentique est explicitement reportée en V2-9. Voir [SPECS.md](SPECS.md) pour l'architecture complète.

## Fonctionnement

Concept inspiré par le [LLM Wiki d'Andrej Karpathy](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

Les fichiers sources (résumés de transcripts YouTube au format `-reduit.md`) sont ingérés dans un wiki structuré. Chaque ingestion crée ou met à jour des pages source, des pages concept, un index, un journal et un suivi des contradictions. Le wiki est conçu pour être lu dans [Obsidian](https://obsidian.md/) (vue graphe, liens cliquables).

## Prérequis

- Python 3.9+
- git
- pytest (uniquement pour les tests)

## Installation

```bash
git clone <url-du-repo> && cd wiki-llm
pip install pytest  # uniquement pour lancer les tests
```

Aucune dépendance runtime en dehors de la bibliothèque standard Python.

## Utilisation

```bash
python3 wiki_ingest.py <chemin-vers-fiche-reduit.md>
```

| Option | Description |
|---|---|
| `--wiki-root PATH` | Racine du wiki (défaut : `./wiki/`) |
| `--source-dir PATH` | Dossier des sources brutes pour la vérification d'intégrité R6 |
| `--question TEXT` | Remplace la question transversale auto-générée |
| `--no-commit` | Ne pas faire le commit git |
| `--no-validate` | Ne pas lancer la validation post-ingestion |

### Exemple

```bash
python3 wiki_ingest.py wiki-test/2026-03-24-40-millions-de-vues-en-12h-claude-computer-use-enterre-le-travail-de-bureau-reduit.md
```

### Lancer les tests

```bash
python3 -m pytest tests/ -v
```

## Structure du projet

```
wiki-llm/
    wiki_ingest.py          # Point d'entrée CLI (orchestrateur Workflow A)
    SPECS.md                # Spécifications complètes
    CLAUDE.md               # Constitution et règles du projet
    src/
        reader.py           # Lecture des fiches -reduit.md
        source_writer.py    # Génération des pages wiki/sources/
        concept_writer.py   # Création/mise à jour des pages wiki/concepts/
        index_manager.py    # Maintenance de wiki/index.md
        log_manager.py      # Écriture dans wiki/log.md
        contradiction_manager.py  # Suivi des contradictions entre sources
        validator.py        # Vérification des règles post-ingestion
    wiki/
        index.md            # Catalogue des pages (remplace le RAG vectoriel)
        log.md              # Journal chronologique
        contradictions.md   # Contradictions détectées
        sources/            # Une page par source ingérée
        concepts/           # Une page par concept transversal
        syntheses/          # Pages de synthèse produites à la demande
        a-traiter/          # Sources insuffisantes en attente
    tests/
        test_contract.py    # 9 tests de contrat (SPECS.md Bloc 5)
        test_smoke.py       # Test bout en bout du Workflow A
    wiki-test/              # Fixtures de test (fiches -reduit.md)
```

## Architecture

Voir [SPECS.md](SPECS.md) pour la spécification complète : constitution (Bloc 0), architecture (Bloc 2), prompt système (Bloc 3), comportements aux limites (Bloc 4) et stratégie de tests (Bloc 5).

## Licence

Non spécifiée.
