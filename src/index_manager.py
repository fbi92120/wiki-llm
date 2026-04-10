"""
src/index_manager.py — Wiki LLM

Ajoute ou met à jour une entrée dans wiki/index.md.

Ce module est appelé EN PREMIER dans le workflow d'ingestion (TC-04 :
règle 4 de la constitution — index.md mis à jour avant toute autre page).

Format d'une entrée (SPECS.md Bloc 2) :
    - [[sources/slug]] — type:source — Résumé en une phrase

Catégories supportées : source, concept, synthese.
Le module ne lit aucune page wiki — il reçoit toutes les informations en
paramètre. Il n'infère rien.

Si une entrée avec le même chemin existe déjà : on met à jour le résumé,
on ne crée pas de doublon.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Permettre l'exécution en script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


DEFAULT_WIKI_ROOT = _PROJECT_ROOT / "wiki"

# Mapping type → en-tête de section + placeholder « vide »
_SECTION_HEADERS: dict[str, tuple[str, str]] = {
    "source": ("## Sources", "*(aucune)*"),
    "concept": ("## Concepts", "*(aucun)*"),
    "synthese": ("## Synthèses", "*(aucune)*"),
}

_PLACEHOLDER_RE = re.compile(r"^\s*\*\(aucun[e]?\)\*\s*$")


# --- API publique --------------------------------------------------------


def update_index(
    page_type: str,
    page_name: str,
    summary: str,
    relative_path: str,
    wiki_root: Path | str = DEFAULT_WIKI_ROOT,
) -> dict:
    """Ajoute ou met à jour une entrée dans wiki/index.md.

    Args:
        page_type: "source" | "concept" | "synthese".
        page_name: nom lisible de la page (utilisé pour le retour et le log,
            le format de l'entrée n'inclut que le wikilink + type + résumé).
        summary: résumé en une phrase, intégré tel quel dans l'entrée.
        relative_path: chemin relatif dans wiki/ (avec ou sans extension .md).
            Exemples : "sources/computer-use", "concepts/architecture-confiance.md".
        wiki_root: racine du wiki. Par défaut ~/Projects/wiki-llm/wiki/.

    Returns:
        dict avec :
            "action"   : "added" | "updated"
            "wikilink" : str (ex. "[[sources/computer-use]]")
            "page_name": str
            "section"  : "## Sources" | "## Concepts" | "## Synthèses"

    Raises:
        ValueError: si page_type est inconnu, ou si l'index.md n'existe pas
            ou ne contient pas la section attendue.
    """
    if page_type not in _SECTION_HEADERS:
        raise ValueError(
            f"page_type inconnu : {page_type!r}. "
            f"Valeurs attendues : {list(_SECTION_HEADERS.keys())}"
        )

    section_header, placeholder = _SECTION_HEADERS[page_type]
    norm_path = _strip_md(relative_path)
    wikilink = f"[[{norm_path}]]"
    new_entry = f"- {wikilink} — type:{page_type} — {summary}"

    index_path = Path(wiki_root) / "index.md"
    if not index_path.is_file():
        raise ValueError(
            f"index.md introuvable : {index_path}\n"
            f"Lance d'abord le bootstrap (Prompt 1) pour créer la structure."
        )

    text = index_path.read_text(encoding="utf-8")
    new_text, action = _modify_index_text(
        text=text,
        section_header=section_header,
        placeholder=placeholder,
        wikilink=wikilink,
        new_entry=new_entry,
    )
    index_path.write_text(new_text, encoding="utf-8")

    return {
        "action": action,
        "wikilink": wikilink,
        "page_name": page_name,
        "section": section_header,
    }


# --- Manipulation de texte ----------------------------------------------


def _strip_md(path: str) -> str:
    """Retire l'extension .md si présente."""
    return path[:-3] if path.endswith(".md") else path


def _modify_index_text(
    *,
    text: str,
    section_header: str,
    placeholder: str,
    wikilink: str,
    new_entry: str,
) -> tuple[str, str]:
    """Renvoie (nouveau_texte, action) où action est 'added' ou 'updated'."""
    preamble, sections, order = _parse_sections(text)

    if section_header not in sections:
        raise ValueError(
            f"Section '{section_header}' introuvable dans index.md. "
            f"Sections présentes : {order}"
        )

    section_lines = sections[section_header]
    new_section_lines, action = _modify_section_lines(
        section_lines=section_lines,
        wikilink=wikilink,
        new_entry=new_entry,
        placeholder=placeholder,
    )
    sections[section_header] = new_section_lines

    return _rebuild(preamble, sections, order), action


def _modify_section_lines(
    *,
    section_lines: list[str],
    wikilink: str,
    new_entry: str,
    placeholder: str,
) -> tuple[list[str], str]:
    """Calcule les lignes de la section après ajout / mise à jour.

    La section sortante est toujours normalisée à : ['', entries..., ''].
    """
    # Extraire les entrées existantes (lignes commençant par "- [[")
    entries = [
        line for line in section_lines if line.lstrip().startswith("- [[")
    ]

    # Recherche d'une entrée existante par wikilink exact
    updated = False
    for i, entry in enumerate(entries):
        if wikilink in entry:
            entries[i] = new_entry
            updated = True
            break

    if not updated:
        entries.append(new_entry)

    if entries:
        # Format normalisé : blank, entries, blank
        new_lines = ["", *entries, ""]
    else:
        # Théoriquement impossible — on vient d'ajouter une entrée
        new_lines = ["", placeholder, ""]

    return new_lines, ("updated" if updated else "added")


def _parse_sections(
    text: str,
) -> tuple[list[str], dict[str, list[str]], list[str]]:
    """Découpe l'index en (preamble, sections{header: lines}, order)."""
    lines = text.splitlines()
    preamble: list[str] = []
    sections: dict[str, list[str]] = {}
    order: list[str] = []

    current_header: str | None = None
    current_lines: list[str] = []

    for line in lines:
        if line.startswith("## "):
            if current_header is None:
                preamble = current_lines
            else:
                sections[current_header] = current_lines
            current_header = line
            order.append(current_header)
            current_lines = []
        else:
            current_lines.append(line)

    if current_header is None:
        preamble = current_lines
    else:
        sections[current_header] = current_lines

    return preamble, sections, order


def _rebuild(
    preamble: list[str],
    sections: dict[str, list[str]],
    order: list[str],
) -> str:
    """Reconstruit le texte de l'index. Termine toujours par un \\n."""
    parts: list[str] = list(preamble)
    for header in order:
        parts.append(header)
        parts.extend(sections[header])
    text = "\n".join(parts)
    if not text.endswith("\n"):
        text += "\n"
    return text


# --- Test manuel ---------------------------------------------------------

if __name__ == "__main__":
    # On part d'un index propre (vide) pour que le test soit reproductible
    template = (
        "# Index du wiki\n"
        "\n"
        "Catalogue de toutes les pages — une entrée par page : titre, type, résumé.\n"
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
        "*(aucune)*\n"
    )
    index_path = DEFAULT_WIKI_ROOT / "index.md"
    index_path.write_text(template, encoding="utf-8")

    print("=== Run 1 — ajout entrée source (computer-use) ===")
    r1 = update_index(
        page_type="source",
        page_name="Claude vient de prendre le contrôle de votre Mac",
        summary="Claude prend le contrôle direct du Mac : l'intelligence devient commodité, la bataille devient la gestion du risque.",
        relative_path="sources/claude-vient-de-prendre-le-controle-de-votre-mac",
    )
    print(f"  action   : {r1['action']}")
    print(f"  wikilink : {r1['wikilink']}")

    print("\n=== Run 2 — ajout entrée concept (architecture de confiance) ===")
    r2 = update_index(
        page_type="concept",
        page_name="Architecture de confiance",
        summary="Le compromis qu'on accepte en donnant à un agent autonome accès à son environnement de travail.",
        relative_path="concepts/architecture-de-confiance",
    )
    print(f"  action   : {r2['action']}")
    print(f"  wikilink : {r2['wikilink']}")

    print("\n=== Contenu de wiki/index.md ===")
    print(index_path.read_text(encoding="utf-8"))

    print("=== Run 3 — réajout de la même entrée source (test doublon) ===")
    r3 = update_index(
        page_type="source",
        page_name="Claude vient de prendre le contrôle de votre Mac",
        summary="Claude prend le contrôle direct du Mac : l'intelligence devient commodité, la bataille devient la gestion du risque.",
        relative_path="sources/claude-vient-de-prendre-le-controle-de-votre-mac",
    )
    print(f"  action   : {r3['action']}")
    if r3["action"] == "updated":
        print("  ✅ Doublon évité — l'entrée a été mise à jour, pas dupliquée.")
    else:
        print("  ❌ DOUBLON CRÉÉ — comportement incorrect.")
        sys.exit(1)

    # Vérification : combien de lignes "- [[sources/" dans la section Sources ?
    final_text = index_path.read_text(encoding="utf-8")
    sources_count = final_text.count("[[sources/claude-vient-de-prendre-le-controle-de-votre-mac]]")
    print(f"\n  Nombre d'occurrences du wikilink source : {sources_count}")
    if sources_count == 1:
        print("  ✅ Une seule entrée — pas de doublon.")
    else:
        print(f"  ❌ {sources_count} occurrences — duplication détectée.")
        sys.exit(1)
