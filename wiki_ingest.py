#!/usr/bin/env python3
"""
wiki_ingest.py — Wiki LLM — Point d'entrée CLI du Workflow A

Orchestre l'ingestion d'une fiche -reduit.md dans le wiki.
Zéro logique métier — tout est délégué aux modules de src/.

Ordre d'appel (SPECS.md Bloc 2) :
    1. index.md mis à jour en premier  (src/index_manager)
    2. Page sources/ créée             (src/source_writer)
    3. Pages concepts/ créées ou mises à jour (src/concept_writer)
    4. log.md — entrée ingest ajoutée  (src/log_manager)
    5. contradictions.md — si tensions fournies (src/contradiction_manager)
    6. Compte-rendu émis               (formatage local)
    7. Validation post-ingestion       (src/validator)
    8. Commit git                      (subprocess)

Usage :
    python3 wiki_ingest.py <chemin_fiche_reduit.md> [options]

Options :
    --wiki-root PATH        Racine du wiki (défaut : ./wiki/)
    --source-dir PATH       Dossier des sources brutes pour vérification R6
    --question TEXT          Question transversale pour le compte-rendu
                            (sinon générée depuis les concepts extraits)
    --no-commit             Ne pas faire le commit git
    --no-validate           Ne pas lancer la validation post-ingestion
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.reader import read_fiche  # noqa: E402
from src.source_writer import slugify, write_source_page  # noqa: E402
from src.concept_writer import write_concept_page  # noqa: E402
from src.index_manager import update_index  # noqa: E402
from src.log_manager import append_log_entry  # noqa: E402
from src.contradiction_manager import record_contradiction  # noqa: E402
from src.validator import (  # noqa: E402
    dir_sha256,
    snapshot_wiki,
    validate_post_ingestion,
)

DEFAULT_WIKI_ROOT = _PROJECT_ROOT / "wiki"


# --- Formatage du compte-rendu -------------------------------------------


def _format_report(
    *,
    source_slug: str,
    pages_created: list[str],
    pages_updated: list[str],
    tensions: list[str],
    question: str,
    commit_ref: str,
) -> str:
    """Compose le compte-rendu de fin d'ingestion (SPECS.md Bloc 2)."""
    created = ", ".join(pages_created) if pages_created else "aucune"
    updated = ", ".join(pages_updated) if pages_updated else "aucune"
    tensions_txt = ", ".join(tensions) if tensions else "aucune"

    return (
        f"## Compte-rendu — ingestion {source_slug}\n"
        f"**Pages créées** : {created}\n"
        f"**Pages mises à jour** : {updated}\n"
        f"**Tensions détectées** : {tensions_txt}\n"
        f"**Question transversale émergente** : {question}\n"
        f"**Commit** : {commit_ref}\n"
    )


def _generate_question(concept_names: list[str], these: str) -> str:
    """Génère une question transversale formulaïque depuis les concepts.

    Pas de synthèse LLM — simple template. L'humain peut la remplacer
    via --question.
    """
    if not concept_names:
        return "Quelles connexions transversales émergent de cette source ?"

    if len(concept_names) == 1:
        return (
            f"Comment le concept de {concept_names[0]} "
            f"se connecte-t-il aux autres thèmes du wiki ?"
        )

    noms = ", ".join(concept_names[:-1]) + " et " + concept_names[-1]
    return (
        f"Comment {noms} interagissent-ils à la lumière de cette source ?"
    )


# --- Git -----------------------------------------------------------------


def _git_commit(wiki_root: Path, source_slug: str) -> str:
    """Commit les changements dans wiki/ avec le message conventionnel.

    Returns:
        Le hash court du commit, ou "no-commit" si rien à commiter.
    """
    try:
        # Stage tout le contenu de wiki/
        subprocess.run(
            ["git", "add", "wiki/"],
            cwd=str(wiki_root.parent),
            check=True,
            capture_output=True,
        )

        # Vérifier s'il y a quelque chose à commiter
        status = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=str(wiki_root.parent),
            capture_output=True,
        )
        if status.returncode == 0:
            return "no-commit"

        message = f"ingest: {source_slug}"
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=str(wiki_root.parent),
            check=True,
            capture_output=True,
        )

        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(wiki_root.parent),
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if isinstance(e.stderr, bytes) else str(e.stderr)
        print(f"  ⚠ Erreur git : {stderr.strip()}", file=sys.stderr)
        return "erreur-git"


# --- Orchestration -------------------------------------------------------


def ingest(
    fiche_path: Path,
    *,
    wiki_root: Path = DEFAULT_WIKI_ROOT,
    source_dir: Path | None = None,
    question_override: str | None = None,
    do_commit: bool = True,
    do_validate: bool = True,
) -> str:
    """Exécute le Workflow A complet sur une fiche -reduit.md.

    Args:
        fiche_path: chemin vers la fiche source.
        wiki_root: racine du wiki.
        source_dir: dossier des sources brutes (pour validation R6).
        question_override: question transversale fournie par l'humain.
        do_commit: si True, commit git en fin d'ingestion.
        do_validate: si True, lance la validation post-ingestion.

    Returns:
        Le compte-rendu de fin d'ingestion (texte markdown).
    """
    fiche_path = Path(fiche_path).resolve()
    wiki_root = Path(wiki_root).resolve()

    # --- Lecture de la fiche ---
    print(f"📖 Lecture de {fiche_path.name}")
    fiche = read_fiche(fiche_path)
    source_slug = slugify(fiche.titre)
    source_filename = fiche_path.name

    # --- Snapshots pour la validation ---
    snapshot_before = snapshot_wiki(wiki_root) if do_validate else None
    source_dir_hash = (
        dir_sha256(source_dir) if do_validate and source_dir else None
    )

    # Snapshot des pages concept existantes (pour R1)
    concept_snapshots: dict[str, str] = {}
    if do_validate:
        for concept in fiche.concepts_cles:
            cslug = slugify(concept["nom"])
            cpath = wiki_root / "concepts" / f"{cslug}.md"
            if cpath.is_file():
                concept_snapshots[cslug] = cpath.read_text(encoding="utf-8")

    pages_created: list[str] = []
    pages_updated: list[str] = []
    pages_mtime_ns: dict[str, int] = {}

    # === Étape 1 — index.md mis à jour EN PREMIER (R4) ===
    print("  1. Mise à jour index.md")
    idx_source = update_index(
        page_type="source",
        page_name=fiche.titre,
        summary=fiche.these_centrale[:120],
        relative_path=f"sources/{source_slug}",
        wiki_root=wiki_root,
    )
    index_mtime_ns = (wiki_root / "index.md").stat().st_mtime_ns

    # Petit délai pour garantir la distinction temporelle (R4/TC-04)
    time.sleep(0.05)

    # === Étape 2 — page source ===
    print("  2. Création page source")
    source_page_path = wiki_root / "sources" / f"{source_slug}.md"
    is_new_source = not source_page_path.exists()
    try:
        write_source_page(fiche, source_filename, wiki_root)
        tag = f"sources/{source_slug}"
        pages_created.append(tag)
        pages_mtime_ns[tag] = source_page_path.stat().st_mtime_ns
    except FileExistsError:
        print(f"    ⚠ Doublon détecté : {source_page_path.name}")
        print("      La page source existe déjà — passage aux concepts.")
        tag = f"sources/{source_slug}"
        pages_updated.append(tag)

    # === Étape 3 — pages concepts ===
    print("  3. Mise à jour pages concepts")
    concept_names: list[str] = []
    for concept in fiche.concepts_cles:
        cname = concept["nom"]
        concept_names.append(cname)
        cslug = slugify(cname)

        result = write_concept_page(cname, fiche, source_filename, wiki_root)
        tag = f"concepts/{cslug}"

        if result["action"] == "created":
            pages_created.append(tag)
        elif result["action"] == "updated":
            pages_updated.append(tag)
        # "duplicate" → aucune modification

        cpath = wiki_root / "concepts" / f"{cslug}.md"
        if cpath.is_file():
            pages_mtime_ns[tag] = cpath.stat().st_mtime_ns

        # Entrée index pour chaque concept
        update_index(
            page_type="concept",
            page_name=cname,
            summary=concept.get("definition", "")[:120],
            relative_path=f"concepts/{cslug}",
            wiki_root=wiki_root,
        )
        print(f"    - {cname} : {result['action']}")

    # === Étape 4 — log.md ===
    print("  4. Entrée log.md")
    log_desc = (
        f"Ingestion de {source_filename} : "
        f"{len(pages_created)} page(s) créée(s), "
        f"{len(pages_updated)} page(s) mise(s) à jour."
    )
    append_log_entry(
        event_type="ingest",
        name=source_slug,
        description=log_desc,
        wiki_root=wiki_root,
    )

    # === Étape 5 — contradictions (si signalées par l'humain) ===
    # Dans le MVP piloté, la détection de contradictions est faite
    # par le LLM en amont. L'orchestrateur n'a pas de logique de
    # détection sémantique. Si des contradictions sont à enregistrer,
    # l'humain appelle contradiction_manager séparément ou via un
    # futur flag CLI.
    tensions: list[str] = []
    print("  5. Contradictions : aucune détection automatique (MVP piloté)")

    # === Étape 6 — compte-rendu ===
    print("  6. Génération compte-rendu")
    question = question_override or _generate_question(
        concept_names, fiche.these_centrale
    )
    # Le commit_ref sera injecté après le commit
    commit_ref = "en attente"

    # === Étape 7 — commit git ===
    if do_commit:
        print("  7. Commit git")
        commit_ref = _git_commit(wiki_root, source_slug)
        print(f"    → {commit_ref}")
    else:
        print("  7. Commit git : désactivé (--no-commit)")
        commit_ref = "no-commit"

    report = _format_report(
        source_slug=source_slug,
        pages_created=pages_created,
        pages_updated=pages_updated,
        tensions=tensions,
        question=question,
        commit_ref=commit_ref,
    )

    # === Étape 8 — validation post-ingestion ===
    if do_validate:
        print("  8. Validation post-ingestion")
        warnings = validate_post_ingestion(
            wiki_root=wiki_root,
            fiche=fiche,
            source_slug=source_slug,
            report=report,
            concept_snapshots_before=concept_snapshots,
            index_mtime_ns=index_mtime_ns,
            pages_mtime_ns=pages_mtime_ns,
            source_dir=source_dir,
            source_dir_hash_before=source_dir_hash,
            snapshot_before=snapshot_before,
        )
        if warnings:
            print(f"    ⚠ {len(warnings)} warning(s) :")
            for w in warnings:
                print(f"      - {w}")
        else:
            print("    ✅ Aucun warning.")
    else:
        print("  8. Validation : désactivée (--no-validate)")

    # === Affichage du compte-rendu ===
    print()
    print(report)

    return report


# --- CLI -----------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Wiki LLM — Ingestion Workflow A",
        epilog="Exemple : python3 wiki_ingest.py wiki-test/fiche-reduit.md",
    )
    parser.add_argument(
        "fiche",
        type=Path,
        help="Chemin vers la fiche -reduit.md à ingérer",
    )
    parser.add_argument(
        "--wiki-root",
        type=Path,
        default=DEFAULT_WIKI_ROOT,
        help="Racine du wiki (défaut : ./wiki/)",
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=None,
        help="Dossier des sources brutes pour vérification R6",
    )
    parser.add_argument(
        "--question",
        type=str,
        default=None,
        help="Question transversale pour le compte-rendu",
    )
    parser.add_argument(
        "--no-commit",
        action="store_true",
        help="Ne pas faire le commit git",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Ne pas lancer la validation post-ingestion",
    )

    args = parser.parse_args()

    if not args.fiche.is_file():
        print(f"Erreur : fiche introuvable : {args.fiche}", file=sys.stderr)
        sys.exit(1)

    ingest(
        fiche_path=args.fiche,
        wiki_root=args.wiki_root,
        source_dir=args.source_dir,
        question_override=args.question,
        do_commit=not args.no_commit,
        do_validate=not args.no_validate,
    )


if __name__ == "__main__":
    main()
