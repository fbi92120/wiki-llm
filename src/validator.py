"""
src/validator.py — Wiki LLM

Vérifie les règles testables de la constitution après une ingestion.

Retourne une liste de warnings (chaînes). Liste vide = tout est conforme.
Ne lève jamais d'exception pour une violation de règle — les violations
sont signalées, pas bloquantes. Seules les erreurs d'usage (fichier
manquant, argument invalide) lèvent des exceptions.

Deux points d'entrée :
    validate_post_ingestion()  — vérifie R1–R7 / R11–R12 après un workflow A
    validate_query_response()  — vérifie R14 sur une réponse à requête

Certaines vérifications sont « post-hoc » (état courant du wiki seul).
D'autres sont « comparatives » (nécessitent un snapshot avant/après,
fourni par l'orchestrateur). Les arguments comparatifs sont optionnels :
s'ils sont absents, le check correspondant est sauté silencieusement.

Mapping règles → checks :
    R1  (TC-01) : sections non concernées inchangées       [comparatif]
    R2  (TC-02) : contradictions.md contient les entrées    [post-hoc]
    R3  (TC-03) : Mes notes → Note personnelle verbatim    [post-hoc]
    R4  (TC-04) : index.md modifié en premier              [comparatif]
    R5  (TC-05) : tous les liens résolvent                 [post-hoc]
    R6  (TC-06) : sources brutes immuables                 [comparatif]
    R11 (TC-07) : périmètre d'écriture respecté            [comparatif]
    R12 (TC-08) : compte-rendu avec question transversale  [post-hoc]
    R14 (TC-09) : réponse à requête cite le wiki           [post-hoc]
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.reader import SourceFiche  # noqa: E402
from src.source_writer import slugify  # noqa: E402

DEFAULT_WIKI_ROOT = _PROJECT_ROOT / "wiki"


# --- Regex ---------------------------------------------------------------

_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+\.md)\)")

_REPORT_QUESTION_RE = re.compile(
    r"\*\*Question transversale émergente\*\* *: *(.*)", re.MULTILINE
)
_RESPONSE_FIELD_RE = re.compile(
    r"\*\*Réponse\*\*\s*:\s*(.+?)(?=\n\*\*)", re.DOTALL
)


# --- Helpers -------------------------------------------------------------


def _extract_section(text: str, header: str) -> str:
    """Extrait le contenu brut d'une section ## jusqu'à la prochaine ##."""
    pattern = re.compile(
        rf"^{re.escape(header)}\n(.*?)(?=\n## |\Z)", re.DOTALL | re.MULTILINE
    )
    m = pattern.search(text)
    return m.group(1) if m else ""


def dir_sha256(directory: Path) -> str:
    """Hash déterministe d'un dossier (fichiers triés par chemin relatif).

    Exposé en API publique pour que l'orchestrateur puisse capturer le
    hash avant ingestion et le transmettre au validateur après.
    """
    h = hashlib.sha256()
    for f in sorted(directory.rglob("*")):
        if f.is_file():
            h.update(str(f.relative_to(directory)).encode())
            h.update(f.read_bytes())
    return h.hexdigest()


def snapshot_wiki(wiki_root: Path) -> dict[str, bytes]:
    """Capture le contenu de chaque fichier du wiki.

    Exposé en API publique pour que l'orchestrateur puisse capturer
    l'état avant ingestion et le transmettre au validateur après.
    """
    snap: dict[str, bytes] = {}
    for f in Path(wiki_root).rglob("*"):
        if f.is_file():
            snap[str(f.relative_to(wiki_root))] = f.read_bytes()
    return snap


# --- R1 — Sections non concernées inchangées (comparatif) ----------------


def _check_r1(
    warnings: list[str],
    concept_snapshots_before: dict[str, str],
    wiki_root: Path,
    source_slug: str,
) -> None:
    """Vérifie que les sections non touchées par l'ingestion sont
    inchangées octet par octet sur chaque page concept modifiée."""
    # Sections qui ne doivent pas bouger lors d'un ajout d'angle
    protected_sections = (
        "## Définition synthétique",
        "## Tensions et contradictions",
        "## Questions ouvertes",
    )
    concepts_dir = wiki_root / "concepts"
    for slug, old_content in concept_snapshots_before.items():
        page = concepts_dir / f"{slug}.md"
        if not page.is_file():
            continue
        new_content = page.read_text(encoding="utf-8")
        # Vérifier uniquement si la source actuelle n'a pas ajouté de tension
        # (contradiction_manager touche légitimement ## Tensions)
        for section_header in protected_sections:
            old_section = _extract_section(old_content, section_header)
            new_section = _extract_section(new_content, section_header)
            # Si la section a été touchée par contradiction_manager,
            # la modification est légitime — on ne la signale pas ici
            if section_header == "## Tensions et contradictions":
                if f"[[sources/{source_slug}]]" in new_section:
                    continue
            if old_section != new_section:
                warnings.append(
                    f"R1 : section '{section_header}' modifiée dans "
                    f"concepts/{slug}.md alors qu'elle ne devait pas l'être"
                )


# --- R2 — Contradictions enregistrées (post-hoc) -------------------------


def _check_r2(
    warnings: list[str],
    wiki_root: Path,
    contradictions_recorded: list[dict] | None,
) -> None:
    """Vérifie que chaque contradiction signalée par l'orchestrateur est
    présente dans contradictions.md avec les champs obligatoires."""
    if not contradictions_recorded:
        return
    path = wiki_root / "contradictions.md"
    if not path.is_file():
        warnings.append("R2 : contradictions.md introuvable")
        return
    text = path.read_text(encoding="utf-8")
    for c in contradictions_recorded:
        source_a = c.get("source_a_slug", "")
        source_b = c.get("source_b_slug", "")
        if f"[[sources/{source_a}]]" not in text:
            warnings.append(
                f"R2 : source A '{source_a}' absente de contradictions.md"
            )
        if f"[[sources/{source_b}]]" not in text:
            warnings.append(
                f"R2 : source B '{source_b}' absente de contradictions.md"
            )
    if "**Nature**" not in text:
        warnings.append("R2 : champ Nature absent de contradictions.md")
    if "**Statut**" not in text:
        warnings.append("R2 : champ Statut absent de contradictions.md")


# --- R3 — Mes notes verbatim (post-hoc) ----------------------------------


def _check_r3(
    warnings: list[str],
    wiki_root: Path,
    fiche: SourceFiche,
    source_slug: str,
) -> None:
    """Vérifie que le champ Mes notes est reproduit verbatim."""
    page = wiki_root / "sources" / f"{source_slug}.md"
    if not page.is_file():
        warnings.append(f"R3 : page source absente : sources/{source_slug}.md")
        return
    text = page.read_text(encoding="utf-8")
    marker = "## Note personnelle\n\n"
    idx = text.find(marker)
    if idx == -1:
        warnings.append(
            f"R3 : section '## Note personnelle' absente de sources/{source_slug}.md"
        )
        return
    note_in_page = text[idx + len(marker) :].rstrip("\n")
    if note_in_page != fiche.mes_notes:
        warnings.append(
            f"R3 : Note personnelle ≠ Mes notes (diff ≠ 0) dans "
            f"sources/{source_slug}.md"
        )


# --- R4 — index.md modifié en premier (comparatif) -----------------------


def _check_r4(
    warnings: list[str],
    index_mtime_ns: int,
    pages_mtime_ns: dict[str, int],
) -> None:
    """Vérifie que index.md a un mtime ≤ à toutes les autres pages."""
    for rel_path, mtime in pages_mtime_ns.items():
        if mtime < index_mtime_ns:
            warnings.append(
                f"R4 : index.md modifié APRÈS {rel_path}"
            )


# --- R5 — Tous les liens résolvent (post-hoc) ----------------------------


def _check_r5(
    warnings: list[str],
    wiki_root: Path,
) -> None:
    """Vérifie que chaque wikilink et lien markdown pointe vers un fichier
    existant dans wiki/."""
    for md_file in wiki_root.rglob("*.md"):
        text = md_file.read_text(encoding="utf-8")
        rel = str(md_file.relative_to(wiki_root))

        for m in _WIKILINK_RE.finditer(text):
            target = m.group(1)
            if target == "contradictions":
                target_path = wiki_root / "contradictions.md"
            elif target.startswith("YT-Knowledge/"):
                continue
            else:
                target_path = wiki_root / f"{target}.md"
            if not target_path.is_file():
                warnings.append(f"R5 : lien cassé dans {rel} : [[{target}]]")

        for m in _MD_LINK_RE.finditer(text):
            href = m.group(2)
            target_path = (md_file.parent / href).resolve()
            if not target_path.is_file():
                warnings.append(
                    f"R5 : lien cassé dans {rel} : [{m.group(1)}]({href})"
                )


# --- R6 — Sources brutes immuables (comparatif) --------------------------


def _check_r6(
    warnings: list[str],
    source_dir: Path,
    hash_before: str,
) -> None:
    """Vérifie que le hash du dossier de sources brutes n'a pas changé."""
    hash_after = dir_sha256(source_dir)
    if hash_before != hash_after:
        warnings.append(
            f"R6 : le dossier de sources brutes a été modifié "
            f"(hash avant={hash_before[:12]}… après={hash_after[:12]}…)"
        )


# --- R11 — Périmètre d'écriture (comparatif) -----------------------------

_ALLOWED_PREFIXES = ("sources/", "concepts/", "syntheses/", "a-traiter/", "questions/")
_ALLOWED_ROOT_FILES = ("index.md", "log.md", "contradictions.md", "ingest.log")


def _check_r11(
    warnings: list[str],
    wiki_root: Path,
    snapshot_before: dict[str, bytes],
) -> None:
    """Vérifie que seuls les chemins autorisés ont été modifiés."""
    for f in wiki_root.rglob("*"):
        if not f.is_file():
            continue
        rel = str(f.relative_to(wiki_root))
        current = f.read_bytes()
        # Fichier existait et n'a pas changé → ok
        if rel in snapshot_before and snapshot_before[rel] == current:
            continue
        # Nouveau fichier ou fichier modifié — vérifier le périmètre
        if rel in _ALLOWED_ROOT_FILES:
            continue
        if any(rel.startswith(p) for p in _ALLOWED_PREFIXES):
            continue
        warnings.append(f"R11 : fichier modifié hors périmètre : {rel}")


# --- R12 — Compte-rendu avec question transversale (post-hoc) ------------


def _check_r12(
    warnings: list[str],
    report: str,
) -> None:
    """Vérifie que le compte-rendu contient une question transversale non vide."""
    m = _REPORT_QUESTION_RE.search(report)
    if m is None:
        warnings.append(
            "R12 : champ 'Question transversale émergente' "
            "absent du compte-rendu"
        )
        return
    question = m.group(1).strip()
    if not question:
        warnings.append(
            "R12 : question transversale vide dans le compte-rendu"
        )


# --- R14 — Réponse à requête cite le wiki (post-hoc) ---------------------


def _check_r14(
    warnings: list[str],
    response: str,
) -> None:
    """Vérifie que chaque phrase du champ Réponse cite au moins un [[page]]."""
    m = _RESPONSE_FIELD_RE.search(response)
    if m is None:
        warnings.append("R14 : champ **Réponse** absent de la réponse")
        return
    prose = m.group(1).strip()
    sentences = [s.strip() for s in re.split(r"(?<=\.)\s+", prose) if s.strip()]
    uncited = [s for s in sentences if "[[" not in s]
    for s in uncited:
        warnings.append(
            f"R14 : phrase sans citation : {s[:80]}{'…' if len(s) > 80 else ''}"
        )


# === API publique ========================================================


def validate_post_ingestion(
    *,
    wiki_root: Path | str = DEFAULT_WIKI_ROOT,
    fiche: SourceFiche,
    source_slug: str,
    report: str | None = None,
    # --- Arguments comparatifs (optionnels) ---
    concept_snapshots_before: dict[str, str] | None = None,
    index_mtime_ns: int | None = None,
    pages_mtime_ns: dict[str, int] | None = None,
    source_dir: Path | None = None,
    source_dir_hash_before: str | None = None,
    snapshot_before: dict[str, bytes] | None = None,
    contradictions_recorded: list[dict] | None = None,
) -> list[str]:
    """Vérifie les règles testables après une ingestion Workflow A.

    Args:
        wiki_root: racine du wiki.
        fiche: SourceFiche de la source ingérée.
        source_slug: slug de la source ingérée.
        report: compte-rendu de fin d'ingestion (texte markdown).
        concept_snapshots_before: dict {slug_concept: contenu_avant} pour R1.
        index_mtime_ns: mtime en nanosecondes de index.md JUSTE après
            sa mise à jour, pour R4.
        pages_mtime_ns: dict {chemin_relatif: mtime_ns} des pages modifiées
            après index, pour R4.
        source_dir: dossier des sources brutes, pour R6.
        source_dir_hash_before: hash SHA256 du dossier avant ingestion, pour R6.
        snapshot_before: dict {chemin_relatif: bytes} du wiki avant ingestion,
            pour R11.
        contradictions_recorded: liste de dicts décrivant les contradictions
            enregistrées (champs source_a_slug, source_b_slug), pour R2.

    Returns:
        Liste de warnings. Vide si tout est conforme.
    """
    wiki_root = Path(wiki_root)
    warnings: list[str] = []

    # --- Checks comparatifs (si les données avant sont fournies) ---

    # R1 — sections non concernées inchangées
    if concept_snapshots_before is not None:
        _check_r1(warnings, concept_snapshots_before, wiki_root, source_slug)

    # R4 — index modifié en premier
    if index_mtime_ns is not None and pages_mtime_ns is not None:
        _check_r4(warnings, index_mtime_ns, pages_mtime_ns)

    # R6 — sources brutes immuables
    if source_dir is not None and source_dir_hash_before is not None:
        _check_r6(warnings, source_dir, source_dir_hash_before)

    # R11 — périmètre d'écriture
    if snapshot_before is not None:
        _check_r11(warnings, wiki_root, snapshot_before)

    # --- Checks post-hoc (état courant du wiki seul) ---

    # R2 — contradictions enregistrées
    _check_r2(warnings, wiki_root, contradictions_recorded)

    # R3 — Mes notes verbatim
    _check_r3(warnings, wiki_root, fiche, source_slug)

    # R5 — tous les liens résolvent
    _check_r5(warnings, wiki_root)

    # R12 — compte-rendu avec question transversale
    if report is not None:
        _check_r12(warnings, report)

    return warnings


def validate_query_response(response: str) -> list[str]:
    """Vérifie R14 sur une réponse à requête.

    Args:
        response: texte markdown complet de la réponse.

    Returns:
        Liste de warnings. Vide si tout est conforme.
    """
    warnings: list[str] = []
    _check_r14(warnings, response)
    return warnings


# --- Test manuel ---------------------------------------------------------

if __name__ == "__main__":
    from src.reader import read_fiche

    fiche_path = (
        _PROJECT_ROOT
        / "wiki-test"
        / "2026-03-24-40-millions-de-vues-en-12h-claude-computer-use-enterre-le-travail-de-bureau-reduit.md"
    )
    fiche = read_fiche(fiche_path)
    source_slug = slugify(fiche.titre)

    print("=== Validation post-ingestion sur le wiki actuel ===")
    ws = validate_post_ingestion(
        fiche=fiche,
        source_slug=source_slug,
        report=(
            "## Compte-rendu — ingestion computer-use\n"
            "**Pages créées** : sources/computer-use\n"
            "**Pages mises à jour** : aucune\n"
            "**Tensions détectées** : aucune\n"
            "**Question transversale émergente** : Comment la généralisation "
            "du contrôle machine redéfinit-elle les architectures de confiance ?\n"
            "**Commit** : abc1234\n"
        ),
    )
    if ws:
        print(f"  {len(ws)} warning(s) :")
        for w in ws:
            print(f"    ⚠ {w}")
    else:
        print("  ✅ Aucun warning.")

    print("\n=== Validation réponse conforme ===")
    ws2 = validate_query_response(
        "**Réponse** : Le contrôle machine permet à l'agent de naviguer "
        "dans l'environnement réel ([[concepts/controle-machine-computer-use]]).\n"
        "**Pages mobilisées** : [[concepts/controle-machine-computer-use]]\n"
        "**Lacunes détectées** : aucune\n"
        "**Fiche suggérée** : aucune\n"
    )
    if ws2:
        for w in ws2:
            print(f"    ⚠ {w}")
    else:
        print("  ✅ Aucun warning.")

    print("\n=== Validation réponse non conforme (phrase sans citation) ===")
    ws3 = validate_query_response(
        "**Réponse** : Le contrôle machine est important ([[concepts/controle-machine-computer-use]]). "
        "Les agents IA vont tout changer.\n"
        "**Pages mobilisées** : [[concepts/controle-machine-computer-use]]\n"
        "**Lacunes détectées** : aucune\n"
        "**Fiche suggérée** : aucune\n"
    )
    if ws3:
        for w in ws3:
            print(f"    ⚠ {w}")
    else:
        print("  ❌ Devrait avoir un warning.")
