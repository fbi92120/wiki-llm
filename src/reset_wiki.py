#!/usr/bin/env python3
"""
src/reset_wiki.py — Wiki LLM

Remet le wiki à l'état bootstrap (vide).
Efface wiki/sources/, wiki/concepts/, wiki/questions/.
Réinitialise index.md, log.md, contradictions.md, toutes-les-questions.md.

Ne touche jamais à YT-Knowledge/ ni aux sources brutes.
Demande confirmation humaine avant d'exécuter.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

DEFAULT_WIKI_ROOT = _PROJECT_ROOT / "wiki"


def reset_wiki(wiki_root: Path | str = DEFAULT_WIKI_ROOT, force: bool = False) -> None:
    """Remet le wiki à l'état bootstrap.

    Args:
        wiki_root: racine du wiki.
        force: si True, pas de confirmation interactive (pour les scripts).
    """
    wiki_root = Path(wiki_root).resolve()

    if not wiki_root.is_dir():
        print(f"Erreur : wiki introuvable : {wiki_root}", file=sys.stderr)
        sys.exit(1)

    # Compter ce qui va être effacé
    sources = list((wiki_root / "sources").glob("*.md"))
    concepts = list((wiki_root / "concepts").glob("*.md"))
    questions_file = wiki_root / "questions" / "toutes-les-questions.md"
    has_questions = questions_file.is_file() and questions_file.stat().st_size > 100

    total = len(sources) + len(concepts)
    print(f"Wiki : {len(sources)} sources, {len(concepts)} concepts")

    if total == 0 and not has_questions:
        print("Le wiki est déjà vide.")
        return

    # Confirmation humaine
    if not force:
        response = input(
            "Cette opération efface tout le wiki. "
            "Voulez-vous continuer ? [oui/non] "
        ).strip().lower()
        if response != "oui":
            print("Abandon — aucune modification.")
            return

    # Effacement
    for f in sources:
        f.unlink()
    for f in concepts:
        f.unlink()

    # Bootstrap index.md
    (wiki_root / "index.md").write_text(
        "# Index du wiki\n"
        "\n"
        "Catalogue de toutes les pages — une entrée par page : "
        "titre, type, résumé.\n"
        "Mis à jour à chaque ingestion.\n"
        "\n"
        "## Sources\n"
        "\n"
        "*(aucune)*\n"
        "\n"
        "## Concepts\n"
        "\n"
        "*(aucun)*\n"
        "\n"
        "## Synthèses\n"
        "\n"
        "*(aucune)*\n",
        encoding="utf-8",
    )

    # Bootstrap contradictions.md
    (wiki_root / "contradictions.md").write_text(
        "# Contradictions détectées\n\n*(aucune contradiction enregistrée)*\n",
        encoding="utf-8",
    )

    # Bootstrap toutes-les-questions.md
    questions_dir = wiki_root / "questions"
    questions_dir.mkdir(exist_ok=True)
    (questions_dir / "toutes-les-questions.md").write_text(
        "# Questions ouvertes — toutes les sources\n"
        "\n"
        "*(append-only — alimenté par source_writer.py à chaque ingestion)*\n",
        encoding="utf-8",
    )

    # Log dans log.md (append, pas reset — le log trace l'effacement)
    today = date.today().isoformat()
    log_path = wiki_root / "log.md"
    if not log_path.is_file():
        log_path.write_text("# Journal du wiki\n", encoding="utf-8")
    with log_path.open("a", encoding="utf-8") as f:
        f.write(
            f"\n## [{today}] reset | effacement complet pré-réingestion\n"
            f"{len(sources)} sources et {len(concepts)} concepts effacés.\n"
        )

    print(
        f"Reset terminé : {len(sources)} sources et {len(concepts)} concepts "
        f"effacés. Wiki prêt pour réingestion."
    )


if __name__ == "__main__":
    reset_wiki()
