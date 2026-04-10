"""
src/concept_writer.py — Wiki LLM

Crée ou met à jour une page wiki/concepts/[slug].md selon le template
concept défini dans SPECS.md Bloc 2.

Deux modes :
- Création (page absente)  : génère la page complète, ajoute un premier
  angle depuis la source, initialise le journal des mises à jour.
- Mise à jour (page existante) : append un nouvel angle dans
  ## Angles par source SANS écraser les angles existants. Met à jour
  le header (sources + date). Append une entrée au journal. Les sections
  ## Définition synthétique, ## Tensions et contradictions et
  ## Questions ouvertes restent inchangées octet par octet (TC-01).

Détection de doublon :
- Si la source courante a déjà un angle dans la page (détecté via le slug
  de la source), aucune modification de ## Angles par source. Une entrée
  est tout de même ajoutée au journal pour tracer la tentative.

Limites assumées :
- Aucune génération de contenu LLM. Le module formate ce que reader.py a
  extrait, point.
- La détection de tensions entre sources appartient au Prompt 7
  (contradiction_manager.py). Ici ## Tensions et contradictions est
  vide à la création et inchangé en update.

Règles de la constitution appliquées :
- Règle 1 : pas de réécriture de page entière en mode update.
- Règle 7 : on ne supprime ni ne renomme — append-only.
- Règle 8 : nouvelle source qui contredit → ajouter un angle, jamais écraser.
- Règle 11 : écriture uniquement dans wiki/concepts/.
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

# Permettre `from src.* import …` quand le fichier est exécuté en script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.reader import SourceFiche, read_fiche  # noqa: E402
from src.source_writer import slugify  # noqa: E402


DEFAULT_WIKI_ROOT = _PROJECT_ROOT / "wiki"

# Nettoyage défensif : retire les timestamps résiduels des noms de concepts.
# Couvre les formes [▶ HH:MM:SS](url), [▶ HH:MM:SS], et ▶ HH:MM:SS.
_TIMESTAMP_RE = re.compile(
    r"\s*(?:\[▶[^\]]*\](?:\([^)]*\))?|▶\s*\d{2}:\d{2}:\d{2})\s*$"
)


def _clean_concept_name(name: str) -> str:
    """Retire un éventuel timestamp en fin de nom de concept."""
    return _TIMESTAMP_RE.sub("", name).strip()


# --- API publique --------------------------------------------------------


def write_concept_page(
    concept_name: str,
    fiche: SourceFiche,
    source_filename: str,
    wiki_root: Path | str = DEFAULT_WIKI_ROOT,
) -> dict:
    """Crée ou met à jour la page wiki/concepts/[slug].md.

    Args:
        concept_name: nom du concept tel qu'il apparaît dans
            fiche.concepts_cles. Doit correspondre exactement à une entrée.
        fiche: SourceFiche produit par reader.read_fiche().
        source_filename: nom du fichier source (sans chemin), pour les
            entrées de journal.
        wiki_root: racine du wiki. Par défaut ~/Projects/wiki-llm/wiki/.

    Returns:
        dict avec les clés :
            "path"          : Path absolu de la page concept
            "action"        : "created" | "updated" | "duplicate"
            "concept_slug"  : slug ASCII du concept

    Raises:
        ValueError: si le concept n'est pas dans fiche.concepts_cles.
    """
    concept_name = _clean_concept_name(concept_name)

    matching = next(
        (
            c
            for c in fiche.concepts_cles
            if _clean_concept_name(c.get("nom", "")) == concept_name
        ),
        None,
    )
    if matching is None:
        available = [_clean_concept_name(c.get("nom", "")) for c in fiche.concepts_cles]
        raise ValueError(
            f"Concept '{concept_name}' introuvable dans la fiche source.\n"
            f"Concepts disponibles : {available}"
        )

    concept_slug = slugify(concept_name)
    source_slug = slugify(fiche.titre)
    today = date.today().isoformat()

    concepts_dir = Path(wiki_root) / "concepts"
    concepts_dir.mkdir(parents=True, exist_ok=True)
    target = concepts_dir / f"{concept_slug}.md"

    # --- Création ---
    if not target.exists():
        content = _create_page(
            concept_name=concept_name,
            concept_dict=matching,
            source_slug=source_slug,
            source_filename=source_filename,
            today=today,
        )
        target.write_text(content, encoding="utf-8")
        return {"path": target, "action": "created", "concept_slug": concept_slug}

    # --- Mise à jour ---
    existing = target.read_text(encoding="utf-8")

    # Doublon : la source a déjà un angle
    angle_marker = f"### Selon [[sources/{source_slug}]]"
    if angle_marker in existing:
        new_content = _append_journal_entry(
            existing,
            today,
            source_filename,
            "doublon détecté — angle déjà présent, aucune modification de la section Angles",
        )
        target.write_text(new_content, encoding="utf-8")
        return {"path": target, "action": "duplicate", "concept_slug": concept_slug}

    # Mise à jour réelle : append d'un angle, header rafraîchi, journal
    new_content = _append_angle(existing, matching, source_slug)
    new_content = _update_header(new_content, source_slug, today)
    new_content = _append_journal_entry(
        new_content,
        today,
        source_filename,
        "ajout d'un angle",
    )
    target.write_text(new_content, encoding="utf-8")
    return {"path": target, "action": "updated", "concept_slug": concept_slug}


# --- Création de page ----------------------------------------------------


def _create_page(
    *,
    concept_name: str,
    concept_dict: dict,
    source_slug: str,
    source_filename: str,
    today: str,
) -> str:
    """Compose le contenu markdown initial selon le template SPECS.md."""
    lines: list[str] = []

    lines.append(f"# Concept — {concept_name}")
    lines.append(
        f"**Sources** : [[sources/{source_slug}]] | "
        f"**Dernière mise à jour** : {today}"
    )
    lines.append("")

    lines.append("## Définition synthétique")
    lines.append("")
    lines.append("*(section à compléter par le module de synthèse LLM)*")
    lines.append("")

    lines.append("## Angles par source")
    lines.append("")
    lines.extend(_render_angle(concept_dict, source_slug))
    lines.append("")

    lines.append("## Tensions et contradictions")
    lines.append("")
    lines.append(
        "*(section gérée par contradiction_manager — vide à la création)*"
    )
    lines.append("")

    lines.append("## Questions ouvertes")
    lines.append("")
    lines.append("*(section à compléter par le module de synthèse LLM)*")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Journal des mises à jour")
    lines.append(f"- **{today}** — {source_filename} — création initiale")
    lines.append("")

    return "\n".join(lines)


def _render_angle(concept_dict: dict, source_slug: str) -> list[str]:
    """Construit le bloc d'angle pour une source donnée."""
    block = [f"### Selon [[sources/{source_slug}]]"]
    if concept_dict.get("definition"):
        block.append(f"**Définition** : {concept_dict['definition']}")
    if concept_dict.get("exemple"):
        block.append(f"**Exemple** : {concept_dict['exemple']}")
    return block


# --- Mise à jour de page ------------------------------------------------


# Capture la section ## Angles par source jusqu'au prochain ##.
_ANGLES_SECTION_RE = re.compile(
    r"(## Angles par source\n)(.*?)(\n## )", re.DOTALL
)

# Capture la ligne d'en-tête **Sources** : ... | **Dernière mise à jour** : YYYY-MM-DD
_HEADER_RE = re.compile(
    r"^(\*\*Sources\*\* : )(.+?)( \| \*\*Dernière mise à jour\*\* : )(\d{4}-\d{2}-\d{2})",
    re.MULTILINE,
)


def _append_angle(existing: str, concept_dict: dict, source_slug: str) -> str:
    """Append un nouvel angle à la fin de ## Angles par source.

    Ne touche pas aux angles existants (TC-01).
    """
    m = _ANGLES_SECTION_RE.search(existing)
    if not m:
        raise ValueError(
            "Section '## Angles par source' introuvable dans la page concept."
        )

    new_block = "\n".join(_render_angle(concept_dict, source_slug))
    section_content = m.group(2)
    # Ajout après les angles existants, séparé par une ligne blanche
    new_section_content = section_content.rstrip("\n") + "\n\n" + new_block + "\n"
    return existing.replace(
        m.group(0),
        m.group(1) + new_section_content + m.group(3),
        1,
    )


def _update_header(existing: str, source_slug: str, today: str) -> str:
    """Met à jour la liste des sources et la date dans la ligne d'en-tête."""

    def _replace(match: re.Match) -> str:
        prefix, sources, sep, _old_date = match.groups()
        new_link = f"[[sources/{source_slug}]]"
        if new_link not in sources:
            sources = f"{sources} {new_link}"
        return f"{prefix}{sources}{sep}{today}"

    return _HEADER_RE.sub(_replace, existing, count=1)


def _append_journal_entry(
    existing: str,
    today: str,
    source_filename: str,
    change_description: str,
) -> str:
    """Append une nouvelle ligne à la fin de ## Journal des mises à jour.

    Le journal est par convention la dernière section du fichier (template).
    On append donc à la fin du fichier, en garantissant un saut de ligne.
    """
    if "## Journal des mises à jour" not in existing:
        raise ValueError(
            "Section '## Journal des mises à jour' introuvable dans la page concept."
        )
    if not existing.endswith("\n"):
        existing += "\n"
    return existing + f"- **{today}** — {source_filename} — {change_description}\n"


# --- Test manuel ---------------------------------------------------------

if __name__ == "__main__":
    fiche_path = (
        _PROJECT_ROOT
        / "wiki-test"
        / "2026-03-24-40-millions-de-vues-en-12h-claude-computer-use-enterre-le-travail-de-bureau-reduit.md"
    )
    fiche = read_fiche(fiche_path)

    # On prend le premier concept de la fiche pour le test
    concept_name = fiche.concepts_cles[0]["nom"]
    concept_slug = slugify(concept_name)
    page_path = DEFAULT_WIKI_ROOT / "concepts" / f"{concept_slug}.md"

    # Nettoyage avant test pour partir d'un état propre
    if page_path.exists():
        page_path.unlink()

    print(f"=== Run 1 — création (concept '{concept_name}') ===")
    result1 = write_concept_page(concept_name, fiche, fiche_path.name)
    print(f"  action : {result1['action']}")
    print(f"  path   : {result1['path']}")

    # Snapshot des angles après création
    page_after_run1 = page_path.read_text(encoding="utf-8")
    angles_match = _ANGLES_SECTION_RE.search(page_after_run1)
    angles_after_run1 = angles_match.group(2) if angles_match else ""

    print(f"\n=== Run 2 — réingestion de la même fiche (test doublon) ===")
    result2 = write_concept_page(concept_name, fiche, fiche_path.name)
    print(f"  action : {result2['action']}")

    page_after_run2 = page_path.read_text(encoding="utf-8")
    angles_match_2 = _ANGLES_SECTION_RE.search(page_after_run2)
    angles_after_run2 = angles_match_2.group(2) if angles_match_2 else ""

    print(f"\n=== Vérification TC-01 sur la section ## Angles par source ===")
    print(f"  bytes après run 1 : {len(angles_after_run1)}")
    print(f"  bytes après run 2 : {len(angles_after_run2)}")
    if angles_after_run1 == angles_after_run2:
        print("  ✅ Section ## Angles par source inchangée octet par octet.")
    else:
        print("  ❌ La section a été modifiée — TC-01 violé.")
        sys.exit(1)

    print(f"\n=== ## Journal des mises à jour ===")
    journal_idx = page_after_run2.find("## Journal des mises à jour")
    print(page_after_run2[journal_idx:].rstrip())
