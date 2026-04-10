"""
src/source_writer.py — Wiki LLM

Génère une page wiki/sources/[slug].md à partir d'un SourceFiche produit
par reader.py, en suivant le template Workflow A défini dans SPECS.md Bloc 2.

Le module ne fait QUE formater. Il n'appelle pas de LLM, ne synthétise rien
de nouveau. Les sections qui exigent une synthèse LLM (Trois idées principales,
Liens vers concepts transversaux) sont laissées en placeholder pour qu'un
module ultérieur les complète.

Règles de la constitution appliquées :
- Règle 3 : "Mes notes" reproduit VERBATIM sous "## Note personnelle".
  Jamais paraphrasé, jamais remplacé par du contenu généré.
- Règle 6 : la fiche source n'est jamais modifiée.
- Règle 7 : ne jamais écraser une page existante sans instruction explicite.
  Refus par défaut, paramètre overwrite=True pour forcer après confirmation.
- Règle 11 : écriture uniquement dans wiki/sources/.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

# Permettre `from src.reader import …` quand le fichier est exécuté en script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.reader import SourceFiche, read_fiche  # noqa: E402


# Racine par défaut du wiki — surchargeable pour les tests
DEFAULT_WIKI_ROOT = _PROJECT_ROOT / "wiki"


# --- API publique --------------------------------------------------------


def write_source_page(
    fiche: SourceFiche,
    source_filename: str,
    wiki_root: Path | str = DEFAULT_WIKI_ROOT,
    overwrite: bool = False,
) -> Path:
    """Génère la page wiki/sources/[slug].md correspondant à la fiche.

    Args:
        fiche: objet SourceFiche produit par reader.read_fiche().
        source_filename: nom du fichier source d'origine (sans chemin),
            utilisé pour le champ "Fiche d'origine" de la page.
        wiki_root: racine du wiki. Par défaut ~/Projects/wiki-llm/wiki/.
        overwrite: si False (défaut), lève FileExistsError si la cible
            existe déjà. Mettre à True uniquement après confirmation
            humaine explicite (règle 7).

    Returns:
        Le Path absolu de la page créée.

    Raises:
        ValueError: si la fiche n'a pas de titre — slug impossible à générer.
        FileExistsError: si la page existe déjà et overwrite=False. Le message
            indique le chemin et rappelle la règle 7.
    """
    if not fiche.titre:
        raise ValueError(
            "Impossible de générer la page : la fiche source n'a pas de titre. "
            "Vérifie que reader.read_fiche() a bien extrait le titre."
        )

    slug = slugify(fiche.titre)
    sources_dir = Path(wiki_root) / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)
    target = sources_dir / f"{slug}.md"

    if target.exists() and not overwrite:
        raise FileExistsError(
            f"DOUBLON : la page source existe déjà : {target}\n"
            f"Refus d'écraser sans confirmation explicite (règle 7).\n"
            f"Pour forcer après vérification humaine, appelle "
            f"write_source_page(..., overwrite=True)."
        )

    content = _format_page(fiche, source_filename)
    target.write_text(content, encoding="utf-8")
    return target


def slugify(text: str) -> str:
    """Convertit un titre en slug ASCII : minuscules, tirets, sans accents."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


# --- Formatage interne ---------------------------------------------------


def _format_page(fiche: SourceFiche, source_filename: str) -> str:
    """Compose le contenu markdown de la page source selon SPECS.md Bloc 2."""
    lines: list[str] = []

    lines.append(f"# Source — {fiche.titre}")
    lines.append(f"**Fiche d'origine** : {source_filename}")
    lines.append(
        f"**Vidéo** : {fiche.titre} | **Chaîne** : {fiche.chaine} | "
        f"**URL** : {fiche.url} | **Durée** : {fiche.duree}"
    )
    lines.append("")

    lines.append("## Thèse centrale")
    lines.append("")
    lines.append(fiche.these_centrale)
    lines.append("")

    lines.append("## Concepts clés")
    lines.append("")
    if fiche.concepts_cles:
        for concept in fiche.concepts_cles:
            lines.append(f"### {concept['nom']}")
            if concept.get("definition"):
                lines.append(
                    f"**Définition selon l'auteur** : {concept['definition']}"
                )
            if concept.get("exemple"):
                lines.append(f"**Exemple utilisé** : {concept['exemple']}")
            lines.append("")
    else:
        lines.append("*(aucun concept extrait de la fiche source)*")
        lines.append("")

    lines.append("## Trois idées principales")
    lines.append("")
    lines.append(
        "*(section à compléter par le module de synthèse LLM — "
        "non générée par source_writer)*"
    )
    lines.append("")

    lines.append("## Liens vers concepts transversaux")
    lines.append("")
    lines.append(
        "*(section à compléter par le module de liens transversaux — "
        "non générée par source_writer)*"
    )
    lines.append("")

    # Règle 3 — reproduction verbatim de "Mes notes"
    lines.append("## Note personnelle")
    lines.append("")
    if fiche.mes_notes:
        lines.append(fiche.mes_notes)
    else:
        lines.append("*(aucune note dans la fiche source)*")
    lines.append("")

    return "\n".join(lines)


# --- Test manuel ---------------------------------------------------------

if __name__ == "__main__":
    default_test = (
        _PROJECT_ROOT
        / "wiki-test"
        / "2026-03-24-40-millions-de-vues-en-12h-claude-computer-use-enterre-le-travail-de-bureau-reduit.md"
    )
    test_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_test

    fiche = read_fiche(test_path)

    # overwrite=True ici parce qu'on rejoue le test plusieurs fois pendant
    # le développement. En production, l'orchestrateur demandera confirmation.
    page_path = write_source_page(fiche, test_path.name, overwrite=True)

    print(f"=== Page générée : {page_path} ===\n")
    print(page_path.read_text(encoding="utf-8"))

    print("=== Vérification verbatim de Note personnelle ===")
    print(f"reader.mes_notes  ({len(fiche.mes_notes)} chars) :")
    print(f"  {fiche.mes_notes!r}")

    page_text = page_path.read_text(encoding="utf-8")
    marker = "## Note personnelle\n\n"
    idx = page_text.find(marker)
    if idx == -1:
        print("❌ ERREUR : section ## Note personnelle absente de la page générée")
        sys.exit(1)
    note_in_page = page_text[idx + len(marker):].rstrip("\n")
    print(f"page note         ({len(note_in_page)} chars) :")
    print(f"  {note_in_page!r}")

    if note_in_page == fiche.mes_notes:
        print("\n✅ MATCH PARFAIT — la note personnelle est reproduite verbatim.")
    else:
        print("\n❌ DIFFÉRENCE DÉTECTÉE entre reader.mes_notes et page note")
        sys.exit(1)
