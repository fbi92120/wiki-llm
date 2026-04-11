#!/usr/bin/env python3
"""
ingestwiki.py — Wiki LLM — Point d'entrée CLI du Workflow A

Orchestre l'ingestion de fiches YT Extractor dans le wiki.
Zéro logique métier — tout est délégué aux modules de src/.

Trois modes d'ingestion (SPECS.md Bloc 2 — Modes d'ingestion) :
    Mode 1 — Fiche unique  : ./ingestwiki.py <fiche.md>
    Mode 2 — Dossier       : ./ingestwiki.py <nom-sous-dossier>
    Mode 3 — Vault complet : ./ingestwiki.py (sans argument)

Détection automatique :
    - Argument = fichier existant → mode 1
    - Argument = sous-dossier de YT-Knowledge/ → mode 2
    - Pas d'argument → mode 3

Modes 2 et 3 : skip si wiki/sources/[slug].md existe déjà,
1 commit git en fin de batch, compte-rendu global terminal + log.md.

Options :
    --wiki-root PATH        Racine du wiki (défaut : ./wiki/)
    --no-commit             Ne pas faire le commit git
    --no-validate           Ne pas lancer la validation post-ingestion
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path

import yaml

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


# --- Log technique -------------------------------------------------------


def _log(msg: str, wiki_root: Path = DEFAULT_WIKI_ROOT) -> None:
    """Append une ligne horodatée dans wiki/ingest.log (log technique)."""
    log_path = Path(wiki_root) / "ingest.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")


# --- Configuration -------------------------------------------------------


def _load_config() -> dict:
    """Charge config.yml depuis la racine du projet.
    Retourne un dict vide si le fichier n'existe pas."""
    config_path = _PROJECT_ROOT / "config.yml"
    if not config_path.is_file():
        return {}
    with config_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _yt_knowledge_path(config: dict) -> Path:
    """Construit le chemin absolu vers YT-Knowledge/ depuis config.yml."""
    vault = config.get("vault_path", "")
    yt_dir = config.get("yt_knowledge_dir", "YT-Knowledge")
    if not vault:
        print("Erreur : vault_path absent de config.yml", file=sys.stderr)
        sys.exit(1)
    return Path(vault) / yt_dir


# --- Découverte de fiches ------------------------------------------------


def _find_fiches_in_dir(directory: Path) -> list[Path]:
    """Liste toutes les fiches .md d'un dossier (non récursif).
    Exclut les fichiers qui ne sont pas des fiches YT Extractor."""
    if not directory.is_dir():
        return []
    return sorted(f for f in directory.glob("*.md") if f.is_file())


def _find_all_fiches(yt_knowledge: Path) -> list[Path]:
    """Liste toutes les fiches de tous les sous-dossiers de YT-Knowledge/."""
    if not yt_knowledge.is_dir():
        print(f"Erreur : dossier introuvable : {yt_knowledge}", file=sys.stderr)
        sys.exit(1)
    fiches: list[Path] = []
    for subdir in sorted(yt_knowledge.iterdir()):
        if subdir.is_dir():
            fiches.extend(_find_fiches_in_dir(subdir))
    return fiches


def _is_already_ingested(fiche_path: Path, wiki_root: Path) -> bool:
    """Vérifie si une fiche a déjà été ingérée (page source existante)."""
    fiche = read_fiche(fiche_path)
    source_slug = slugify(fiche.titre)
    return (wiki_root / "sources" / f"{source_slug}.md").is_file()


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
    _log(f"START {fiche_path.name}", wiki_root)
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
    _log("  1. index.md", wiki_root)
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
    source_page_path = wiki_root / "sources" / f"{source_slug}.md"
    is_new_source = not source_page_path.exists()
    try:
        write_source_page(fiche, source_filename, wiki_root)
        tag = f"sources/{source_slug}"
        pages_created.append(tag)
        pages_mtime_ns[tag] = source_page_path.stat().st_mtime_ns
        _log(f"  2. source created: {tag}", wiki_root)
    except FileExistsError:
        tag = f"sources/{source_slug}"
        pages_updated.append(tag)
        _log(f"  2. source duplicate: {tag}", wiki_root)

    # === Étape 3 — pages concepts ===
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

        cpath = wiki_root / "concepts" / f"{cslug}.md"
        if cpath.is_file():
            pages_mtime_ns[tag] = cpath.stat().st_mtime_ns

        update_index(
            page_type="concept",
            page_name=cname,
            summary=concept.get("definition", "")[:120],
            relative_path=f"concepts/{cslug}",
            wiki_root=wiki_root,
        )
        _log(f"  3. concept {result['action']}: {cname}", wiki_root)

    # === Étape 4 — log.md ===
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
    _log(f"  4. log.md: {log_desc}", wiki_root)

    # === Étape 5 — contradictions ===
    tensions: list[str] = []
    _log("  5. contradictions: aucune (MVP pilote)", wiki_root)

    # === Étape 6 — compte-rendu ===
    question = question_override or _generate_question(
        concept_names, fiche.these_centrale
    )
    commit_ref = "en attente"

    # === Étape 7 — commit git ===
    if do_commit:
        commit_ref = _git_commit(wiki_root, source_slug)
        _log(f"  7. commit: {commit_ref}", wiki_root)
    else:
        commit_ref = "no-commit"
        _log("  7. commit: disabled", wiki_root)

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
            _log(f"  8. validation: {len(warnings)} warning(s)", wiki_root)
            for w in warnings:
                _log(f"     - {w}", wiki_root)
        else:
            _log("  8. validation: OK", wiki_root)

    _log(f"END {source_slug} | created={len(pages_created)} updated={len(pages_updated)}", wiki_root)
    _log(report, wiki_root)

    # === Terminal : résumé uniquement ===
    print(
        f"  {source_slug} : "
        f"{len(pages_created)} created, {len(pages_updated)} updated"
        f"{f', commit {commit_ref}' if do_commit else ''}"
    )

    return report


# --- Batch ---------------------------------------------------------------


def ingest_batch(
    fiches: list[Path],
    *,
    wiki_root: Path = DEFAULT_WIKI_ROOT,
    do_commit: bool = True,
    do_validate: bool = True,
    batch_label: str = "batch",
) -> str:
    """Ingère une liste de fiches en mode batch.

    - Skip automatique des fiches déjà ingérées.
    - 1 commit git en fin de batch.
    - Compte-rendu global dans le terminal + log.md label batch.
    """
    wiki_root = Path(wiki_root).resolve()
    total = len(fiches)
    ingested: list[str] = []
    skipped: list[str] = []
    errors: list[str] = []

    _log(f"BATCH START label={batch_label} fiches={total}", wiki_root)

    for i, fiche_path in enumerate(fiches, 1):
        fiche_name = fiche_path.name

        # Skip si déjà ingéré
        try:
            if _is_already_ingested(fiche_path, wiki_root):
                fiche = read_fiche(fiche_path)
                slug = slugify(fiche.titre)
                _log(f"  [{i}/{total}] SKIP {fiche_name} (sources/{slug}.md exists)", wiki_root)
                skipped.append(fiche_name)
                continue
        except Exception as e:
            _log(f"  [{i}/{total}] ERROR read {fiche_name}: {e}", wiki_root)
            errors.append(fiche_name)
            continue

        # Ingestion sans commit individuel
        try:
            _log(f"  [{i}/{total}] INGEST {fiche_name}", wiki_root)
            ingest(
                fiche_path=fiche_path,
                wiki_root=wiki_root,
                do_commit=False,
                do_validate=do_validate,
            )
            ingested.append(fiche_name)
        except Exception as e:
            _log(f"  [{i}/{total}] ERROR ingest {fiche_name}: {e}", wiki_root)
            errors.append(fiche_name)

    # 1 commit en fin de batch
    commit_ref = "no-commit"
    if do_commit and ingested:
        commit_ref = _git_commit(wiki_root, f"batch-{len(ingested)}-fiches")
        _log(f"BATCH COMMIT {commit_ref}", wiki_root)

    # Compte-rendu global
    report = (
        f"## Compte-rendu batch — {batch_label}\n"
        f"**Fiches traitées** : {len(ingested)}/{total}\n"
        f"**Fiches ignorées (déjà ingérées)** : {len(skipped)}\n"
        f"**Erreurs** : {len(errors)}\n"
        f"**Commit** : {commit_ref}\n"
    )
    if ingested:
        report += f"**Ingérées** : {', '.join(ingested)}\n"
    if skipped:
        report += f"**Ignorées** : {', '.join(skipped)}\n"
    if errors:
        report += f"**En erreur** : {', '.join(errors)}\n"

    _log(f"BATCH END\n{report}", wiki_root)

    # Terminal : résumé uniquement
    print(
        f"Batch {batch_label} : "
        f"{len(ingested)} ingérée(s), {len(skipped)} ignorée(s), "
        f"{len(errors)} erreur(s)"
        f"{f', commit {commit_ref}' if do_commit and ingested else ''}"
    )

    # Log batch dans log.md
    if ingested:
        append_log_entry(
            event_type="batch",
            name=batch_label,
            description=(
                f"{len(ingested)} ingérée(s), {len(skipped)} ignorée(s), "
                f"{len(errors)} erreur(s). Commit: {commit_ref}"
            ),
            wiki_root=wiki_root,
        )

    return report


# --- CLI -----------------------------------------------------------------


def _detect_mode(arg: str | None, config: dict, wiki_root: Path) -> tuple[str, list[Path]]:
    """Détecte le mode d'ingestion depuis l'argument CLI.

    Returns:
        (mode, fiches) où mode est "single", "folder" ou "vault".
    """
    # Mode 3 — pas d'argument → vault complet
    if arg is None:
        yt_path = _yt_knowledge_path(config)
        fiches = _find_all_fiches(yt_path)
        return "vault", fiches

    path = Path(arg)

    # Mode 1 — fichier existant
    if path.is_file():
        return "single", [path]

    # Mode 2 — nom de sous-dossier dans YT-Knowledge/
    yt_path = _yt_knowledge_path(config)
    subdir = yt_path / arg
    if subdir.is_dir():
        fiches = _find_fiches_in_dir(subdir)
        return "folder", fiches

    # Essayer comme chemin complet de dossier
    if path.is_dir():
        fiches = _find_fiches_in_dir(path)
        return "folder", fiches

    print(f"Erreur : '{arg}' n'est ni un fichier, ni un sous-dossier "
          f"de {yt_path}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Wiki LLM — Ingestion Workflow A",
        epilog=(
            "Exemples :\n"
            "  ./ingestwiki.py fiche.md                    # mode 1 — fiche unique\n"
            "  ./ingestwiki.py ia-et-strategie-le-samourai  # mode 2 — dossier\n"
            "  ./ingestwiki.py                              # mode 3 — vault complet"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=None,
        help="Fiche .md, nom de sous-dossier YT-Knowledge/, ou rien (vault complet)",
    )
    parser.add_argument(
        "--wiki-root",
        type=Path,
        default=DEFAULT_WIKI_ROOT,
        help="Racine du wiki (défaut : ./wiki/)",
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
    config = _load_config()

    mode, fiches = _detect_mode(args.target, config, args.wiki_root)

    if not fiches:
        print("Aucune fiche trouvée.", file=sys.stderr)
        sys.exit(1)

    if mode == "single":
        # Mode 1 — fiche unique (comportement original)
        ingest(
            fiche_path=fiches[0],
            wiki_root=args.wiki_root,
            do_commit=not args.no_commit,
            do_validate=not args.no_validate,
        )
    else:
        # Modes 2 et 3 — batch
        label = args.target if args.target else "vault-complet"
        ingest_batch(
            fiches,
            wiki_root=args.wiki_root,
            do_commit=not args.no_commit,
            do_validate=not args.no_validate,
            batch_label=label,
        )


if __name__ == "__main__":
    main()
