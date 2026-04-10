"""
src/contradiction_manager.py — Wiki LLM

Enregistre une contradiction détectée entre deux sources sur un même
concept. Le module ne fait PAS de détection sémantique — c'est le LLM
qui pilote l'appel quand il a identifié une tension lors d'une ingestion.
Ici on formate et on persiste, point.

Deux écritures coordonnées par appel :
1. Append d'une entrée dans wiki/contradictions.md (format SPECS.md Bloc 2).
2. Append d'un bloc dans la section ## Tensions et contradictions de
   wiki/concepts/[slug].md, sans toucher aux blocs précédents.

Contrat (règle 8 de la constitution + cahier des charges Prompt 7) :
- Jamais écraser l'angle précédent. Toute tension déjà enregistrée dans
  la page concept reste inchangée octet par octet.
- Append-only sur contradictions.md : aucune lecture-relecture-réécriture.

Détection de doublon :
- Si une tension entre exactement les deux mêmes sources existe déjà sur
  ce concept (clé : paire de slugs source, ordonnée), aucune modification
  n'est faite et le résultat indique action="duplicate". L'humain reste
  seul juge de la pertinence d'enregistrer une seconde tension entre les
  mêmes sources avec un angle différent — dans ce cas il appellera le
  module avec l'argument force=True.

Règles de la constitution appliquées :
- Règle 2  : toute tension détectée déclenche une nouvelle entrée dans
             contradictions.md (TC-02).
- Règle 7  : jamais supprimer ni renommer.
- Règle 8  : nouvelle source qui contredit → ajouter un angle.
- Règle 11 : écriture uniquement dans wiki/contradictions.md et
             wiki/concepts/.
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

# Permettre l'exécution en script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.source_writer import slugify  # noqa: E402


DEFAULT_WIKI_ROOT = _PROJECT_ROOT / "wiki"

VALID_NATURES: frozenset[str] = frozenset(
    {
        "contradiction directe",
        "tension d'horizon",
        "nuance",
    }
)

# Placeholder écrit par concept_writer à la création d'une page concept.
_TENSIONS_PLACEHOLDER = (
    "*(section gérée par contradiction_manager — vide à la création)*"
)


# --- API publique --------------------------------------------------------


def record_contradiction(
    *,
    concept_name: str,
    source_a_slug: str,
    position_a: str,
    source_b_slug: str,
    position_b: str,
    nature: str,
    statut: str = "ouvert",
    force: bool = False,
    wiki_root: Path | str = DEFAULT_WIKI_ROOT,
) -> dict:
    """Enregistre une contradiction sur un concept donné.

    Args:
        concept_name: nom du concept tel qu'il apparaît dans la page concept
            (le titre humain, pas le slug).
        source_a_slug: slug de la première source (sans extension, sans
            préfixe `sources/`).
        position_a: résumé en une phrase de la position de la source A.
        source_b_slug: slug de la seconde source.
        position_b: résumé en une phrase de la position contradictoire.
        nature: l'une de VALID_NATURES.
        statut: "ouvert" par défaut, ou "résolu par [source]".
        force: si True, ajoute la tension même si une tension entre les
            deux mêmes sources existe déjà sur ce concept.
        wiki_root: racine du wiki.

    Returns:
        dict avec :
            "action"             : "recorded" | "duplicate"
            "concept_slug"       : slug ASCII du concept
            "concept_path"       : Path absolu de la page concept
            "contradictions_path": Path absolu de contradictions.md
            "date"               : str (YYYY-MM-DD)

    Raises:
        ValueError: si nature invalide, si la page concept n'existe pas,
            ou si contradictions.md est absent.
    """
    if nature not in VALID_NATURES:
        raise ValueError(
            f"Nature invalide : {nature!r}.\n"
            f"Natures acceptées : {sorted(VALID_NATURES)}."
        )

    if source_a_slug == source_b_slug:
        raise ValueError(
            "Une contradiction oppose deux sources distinctes — "
            f"slug A et slug B sont identiques ({source_a_slug!r})."
        )

    today = date.today().isoformat()
    concept_slug = slugify(concept_name)

    wiki_root = Path(wiki_root)
    concept_path = wiki_root / "concepts" / f"{concept_slug}.md"
    contradictions_path = wiki_root / "contradictions.md"

    if not concept_path.is_file():
        raise ValueError(
            f"Page concept introuvable : {concept_path}\n"
            f"La page doit avoir été créée par concept_writer avant "
            f"d'enregistrer une tension."
        )
    if not contradictions_path.is_file():
        raise ValueError(
            f"contradictions.md introuvable : {contradictions_path}\n"
            f"Lance d'abord le bootstrap (Prompt 1) pour créer la structure."
        )

    # --- Détection de doublon sur la page concept ---
    existing = concept_path.read_text(encoding="utf-8")
    if not force and _tension_already_present(
        existing, source_a_slug, source_b_slug
    ):
        return {
            "action": "duplicate",
            "concept_slug": concept_slug,
            "concept_path": concept_path,
            "contradictions_path": contradictions_path,
            "date": today,
        }

    # --- Écriture 1 : append dans contradictions.md (append-only strict) ---
    entry_md = _format_contradictions_entry(
        today=today,
        concept_name=concept_name,
        source_a_slug=source_a_slug,
        position_a=position_a,
        source_b_slug=source_b_slug,
        position_b=position_b,
        nature=nature,
        statut=statut,
    )
    with contradictions_path.open("a", encoding="utf-8") as f:
        f.write("\n" + entry_md)

    # --- Écriture 2 : append d'un bloc dans la page concept ---
    new_concept_content = _append_tension_block(
        existing,
        today=today,
        source_a_slug=source_a_slug,
        position_a=position_a,
        source_b_slug=source_b_slug,
        position_b=position_b,
        nature=nature,
    )
    concept_path.write_text(new_concept_content, encoding="utf-8")

    return {
        "action": "recorded",
        "concept_slug": concept_slug,
        "concept_path": concept_path,
        "contradictions_path": contradictions_path,
        "date": today,
    }


# --- Formatage contradictions.md ----------------------------------------


def _format_contradictions_entry(
    *,
    today: str,
    concept_name: str,
    source_a_slug: str,
    position_a: str,
    source_b_slug: str,
    position_b: str,
    nature: str,
    statut: str,
) -> str:
    """Construit l'entrée markdown selon le template SPECS.md Bloc 2."""
    lines = [
        f"## [{today}] {concept_name}",
        f"**Source 1** : [[sources/{source_a_slug}]] — {position_a}",
        f"**Source 2** : [[sources/{source_b_slug}]] — {position_b}",
        f"**Nature** : {nature}",
        f"**Statut** : {statut}",
        "",
    ]
    return "\n".join(lines)


# --- Mise à jour de la page concept --------------------------------------


# Capture la section ## Tensions et contradictions jusqu'au prochain ##
_TENSIONS_SECTION_RE = re.compile(
    r"(## Tensions et contradictions\n)(.*?)(\n## )", re.DOTALL
)


def _tension_already_present(
    concept_content: str, source_a_slug: str, source_b_slug: str
) -> bool:
    """Vrai si une tension entre ces deux sources existe déjà sur la page.

    On regarde uniquement la section ## Tensions et contradictions et on
    cherche les deux liens [[sources/...]] dans un même sous-bloc ###.
    """
    m = _TENSIONS_SECTION_RE.search(concept_content)
    if not m:
        return False
    section = m.group(2)

    link_a = f"[[sources/{source_a_slug}]]"
    link_b = f"[[sources/{source_b_slug}]]"

    # Découpe en sous-blocs ### ; un sous-bloc qui contient les deux liens
    # est considéré comme un doublon, indépendamment de l'ordre A/B.
    sub_blocks = re.split(r"\n(?=### )", section)
    for block in sub_blocks:
        if link_a in block and link_b in block:
            return True
    return False


def _append_tension_block(
    existing: str,
    *,
    today: str,
    source_a_slug: str,
    position_a: str,
    source_b_slug: str,
    position_b: str,
    nature: str,
) -> str:
    """Append un bloc de tension à la fin de ## Tensions et contradictions.

    - Si la section ne contient que le placeholder de création, on remplace
      le placeholder par le premier bloc.
    - Sinon on append après les blocs existants, sans en modifier un seul.
    """
    m = _TENSIONS_SECTION_RE.search(existing)
    if not m:
        raise ValueError(
            "Section '## Tensions et contradictions' introuvable dans la "
            "page concept."
        )

    block_lines = [
        f"### [{today}] [[sources/{source_a_slug}]] vs [[sources/{source_b_slug}]]",
        f"**Position [[sources/{source_a_slug}]]** : {position_a}",
        f"**Position [[sources/{source_b_slug}]]** : {position_b}",
        f"**Nature** : {nature}",
        f"**Voir** : [[contradictions]]",
    ]
    new_block = "\n".join(block_lines)

    section_content = m.group(2)
    section_stripped = section_content.strip()

    if section_stripped == "" or section_stripped == _TENSIONS_PLACEHOLDER:
        # Première tension : on remplace le placeholder.
        new_section_content = "\n" + new_block + "\n"
    else:
        # Append après les blocs existants — jamais d'écrasement.
        new_section_content = (
            section_content.rstrip("\n") + "\n\n" + new_block + "\n"
        )

    return existing.replace(
        m.group(0),
        m.group(1) + new_section_content + m.group(3),
        1,
    )


# --- Test manuel ---------------------------------------------------------

if __name__ == "__main__":
    # Test sur la page concept existante : controle-machine-computer-use.
    # On enregistre une tension fictive entre la source réelle et une
    # seconde source imaginaire pour vérifier les deux écritures.

    concept_name = "Contrôle machine (Computer Use)"
    concept_path = DEFAULT_WIKI_ROOT / "concepts" / "controle-machine-computer-use.md"

    if not concept_path.exists():
        print(f"❌ Page concept absente : {concept_path}")
        print("   Lance d'abord concept_writer pour la créer.")
        sys.exit(1)

    # Snapshot de la section Tensions avant
    before = concept_path.read_text(encoding="utf-8")
    m_before = _TENSIONS_SECTION_RE.search(before)
    tensions_before = m_before.group(2) if m_before else ""

    print("=== Run 1 — enregistrement d'une tension ===")
    r1 = record_contradiction(
        concept_name=concept_name,
        source_a_slug="claude-vient-de-prendre-le-controle-de-votre-mac",
        position_a="le contrôle machine est un palier émancipateur qui débloque les apps sans API",
        source_b_slug="rationnement-energie-ia",
        position_b="le contrôle machine se heurte à la contrainte énergétique avant la généralisation",
        nature="tension d'horizon",
    )
    print(f"  action : {r1['action']}")
    print(f"  concept_path        : {r1['concept_path']}")
    print(f"  contradictions_path : {r1['contradictions_path']}")

    # Vérification : les blocs existants restent intacts (TC-01 esprit)
    after_run1 = concept_path.read_text(encoding="utf-8")

    print("\n=== Run 2 — réenregistrement de la même tension (test doublon) ===")
    r2 = record_contradiction(
        concept_name=concept_name,
        source_a_slug="claude-vient-de-prendre-le-controle-de-votre-mac",
        position_a="autre formulation",
        source_b_slug="rationnement-energie-ia",
        position_b="autre formulation",
        nature="tension d'horizon",
    )
    print(f"  action : {r2['action']}")
    if r2["action"] != "duplicate":
        print("  ❌ Doublon non détecté.")
        sys.exit(1)
    print("  ✅ Doublon détecté, aucune modification appliquée.")

    after_run2 = concept_path.read_text(encoding="utf-8")
    if after_run1 != after_run2:
        print("  ❌ La page concept a été modifiée lors du run doublon.")
        sys.exit(1)
    print("  ✅ Page concept inchangée octet par octet entre run 1 et run 2.")

    print("\n=== Run 3 — seconde tension (paire de sources différente) ===")
    r3 = record_contradiction(
        concept_name=concept_name,
        source_a_slug="claude-vient-de-prendre-le-controle-de-votre-mac",
        position_a="le contrôle machine élimine les saisies manuelles",
        source_b_slug="deux-philosophies-anthropic-openai",
        position_b="Anthropic privilégie le rail vertical, pas l'autonomie sur poste",
        nature="nuance",
    )
    print(f"  action : {r3['action']}")

    after_run3 = concept_path.read_text(encoding="utf-8")

    # Vérification cruciale : le bloc de tension ajouté au run 1 doit être
    # toujours présent intact dans la page après run 3.
    m_after_run1 = _TENSIONS_SECTION_RE.search(after_run1)
    m_after_run3 = _TENSIONS_SECTION_RE.search(after_run3)
    assert m_after_run1 and m_after_run3
    section_run1 = m_after_run1.group(2)
    section_run3 = m_after_run3.group(2)

    if section_run1.strip() not in section_run3:
        print("  ❌ La première tension a été altérée par le run 3.")
        sys.exit(1)
    print("  ✅ Bloc de la première tension préservé intégralement.")

    print("\n=== Section ## Tensions et contradictions après run 3 ===")
    print(section_run3.rstrip())

    print("\n=== Contenu de wiki/contradictions.md ===")
    print((DEFAULT_WIKI_ROOT / "contradictions.md").read_text(encoding="utf-8"))
