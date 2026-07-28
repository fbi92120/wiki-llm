# Wiki LLM

Outil LLM piloté qui maintient une base de connaissances persistante en Markdown à partir de fichiers sources. Contrairement aux systèmes RAG classiques qui redécouvrent le savoir à chaque requête, Wiki LLM compile une fois, maintient dans le temps, et fait émerger des connexions transversales que l'utilisateur n'aurait pas formulées seul.

Ce n'est **pas** un agent autonome. Chaque opération est déclenchée par l'humain, supervisée, et s'arrête après avoir rendu la main. L'architecture agentique est explicitement reportée en V2-9. Voir [SPECS.md](SPECS.md) pour l'architecture complète.

## Fonctionnement

Concept inspiré par le [LLM Wiki d'Andrej Karpathy](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

Les fichiers sources (résumés de transcripts YouTube au format `-reduit.md`) sont ingérés dans un wiki structuré. Chaque ingestion crée ou met à jour des pages source, des pages concept, un index, un journal et un suivi des contradictions. Le wiki est conçu pour être lu dans [Obsidian](https://obsidian.md/) (vue graphe, liens cliquables).

## Prérequis

- Python 3.9+
- git
- PyYAML (runtime — lecture de la config)
- pytest + pytest-cov (uniquement pour les tests)

## Installation

```bash
git clone <url-du-repo> && cd wiki-llm
pip install -r requirements.txt
```

Dépendance runtime : PyYAML (lecture de `config.yml`). Dépendances de test :
pytest et pytest-cov. Voir `requirements.txt`.

## Utilisation

Trois modes d'ingestion, detectes automatiquement depuis l'argument :

```bash
./ingestwiki.py <fichier.md>        # mode 1 — fiche unique (chemin complet ou nom)
./ingestwiki.py <nom-dossier>       # mode 2 — sous-dossier YT-Knowledge/
./ingestwiki.py                     # mode 3 — vault complet
```

Le mode 1 accepte un chemin complet, un chemin relatif, ou juste un nom de fichier. Si le fichier n'est pas trouve localement, l'outil cherche dans tous les sous-dossiers de `YT-Knowledge/` (chemin depuis `config.yml`). Si plusieurs correspondances sont trouvees, il affiche une liste numerotee et demande confirmation.

Les modes 2 et 3 ignorent automatiquement les fiches deja ingerees, produisent un seul commit git en fin de batch, et ajoutent un resume batch dans `log.md`.

| Option | Description |
|---|---|
| `--wiki-root PATH` | Racine du wiki (defaut : `./wiki/`) |
| `--no-commit` | Ne pas faire le commit git |
| `--no-validate` | Ne pas lancer la validation post-ingestion |

### Exemples

```bash
./ingestwiki.py fiche.md                     # recherche par nom dans YT-Knowledge/
./ingestwiki.py ia-et-strategie-le-samourai   # ingere tout le sous-dossier
./ingestwiki.py                               # ingere le vault entier (skip existants)
```

### Lancer les tests

```bash
python3 -m pytest tests/ -v
```

## Structure du projet

```
wiki-llm/
    ingestwiki.py          # Point d'entrée CLI (orchestrateur Workflow A)
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

## Méthode

Ce projet a été construit avec la méthode [Vibe Coding, Governed](https://github.com/fbi92120/vibe-coding-governed) — specs avant le code, l'humain décide, le LLM exécute.

## Architecture

Voir [SPECS.md](SPECS.md) pour la spécification complète : constitution (Bloc 0), architecture (Bloc 2), prompt système (Bloc 3), comportements aux limites (Bloc 4) et stratégie de tests (Bloc 5).

## Licence

Non spécifiée.
