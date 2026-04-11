"""
tests/test_smoke.py — Wiki LLM

Test smoke : ingestion complète Workflow A de bout en bout.

Fiche de référence (SPECS.md Bloc 5) : la fiche -reduit.md sur
"La chute d'Anthropic" dans wiki-test/. Si absente, fallback sur la
première fiche *-reduit.md disponible.

Condition initiale : wiki vide — réinitialisé dans un dossier temporaire
avec son propre dépôt git.

Appelle ingest() directement — pas le CLI.

Les 8 assertions de SPECS.md Bloc 5 :
    1. index.md contient une entrée pour la nouvelle page source
    2. wiki/sources/ contient la page créée avec les 5 sections du template
    3. "Note personnelle" est présente et non vide (si la fiche a des notes)
    4. Au moins une page wiki/concepts/ a été créée ou mise à jour
    5. log.md contient une entrée ## [date] ingest | [nom-source]
    6. git log --oneline montre un commit ingest: [nom-source]
    7. Le compte-rendu contient une question transversale non vide
    8. Aucun fichier hors wiki/ dans git diff

Principe : si un test échoue, corriger le module concerné — JAMAIS le test.
"""

from __future__ import annotations

import re
import subprocess
from datetime import date
from pathlib import Path

import pytest

# --- Chemin projet -------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = PROJECT_ROOT / "wiki-test"

import sys

sys.path.insert(0, str(PROJECT_ROOT))

from src.reader import read_fiche  # noqa: E402
from src.source_writer import slugify  # noqa: E402
from ingestwiki import ingest  # noqa: E402


# --- Sélection de la fiche de référence ----------------------------------


def _find_reference_fiche() -> Path:
    """Cherche la fiche 'La chute d'Anthropic', sinon fallback."""
    candidates = sorted(FIXTURES_DIR.glob("*-reduit.md"))
    # Priorité : fiche contenant "chute" ou "anthropic" dans le nom
    for c in candidates:
        name_lower = c.name.lower()
        if "chute" in name_lower or "anthropic" in name_lower:
            return c
    # Fallback : première fiche -reduit.md disponible
    if candidates:
        return candidates[0]
    pytest.fail(
        "Aucune fiche -reduit.md trouvée dans wiki-test/. "
        "Le test smoke nécessite au moins une fiche de référence."
    )


FICHE_REF = _find_reference_fiche()


# --- Bootstrap wiki dans tmp_path ----------------------------------------


def _bootstrap_wiki(project_root: Path) -> Path:
    """Crée la structure wiki/ vide + dépôt git dans un répertoire temporaire.

    Le dépôt git est initialisé dans project_root (pas dans wiki/) car
    _git_commit() utilise wiki_root.parent comme cwd.
    """
    wiki = project_root / "wiki"
    wiki.mkdir(parents=True, exist_ok=True)
    for sub in ("sources", "concepts", "syntheses", "a-traiter"):
        (wiki / sub).mkdir(exist_ok=True)

    (wiki / "index.md").write_text(
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

    (wiki / "log.md").write_text(
        "# Journal du wiki\n", encoding="utf-8"
    )

    (wiki / "contradictions.md").write_text(
        "# Contradictions détectées\n\n*(aucune contradiction enregistrée)*\n",
        encoding="utf-8",
    )

    # Initialiser le dépôt git avec un commit initial
    subprocess.run(
        ["git", "init"], cwd=str(project_root),
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@wiki-llm.local"],
        cwd=str(project_root), check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test Wiki LLM"],
        cwd=str(project_root), check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "add", "wiki/"], cwd=str(project_root),
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "init: structure wiki"],
        cwd=str(project_root), check=True, capture_output=True,
    )

    return wiki


# --- Fixture pytest -------------------------------------------------------


@pytest.fixture(scope="module")
def smoke_result(tmp_path_factory):
    """Exécute une seule ingestion complète et retourne tout le contexte
    nécessaire aux 8 assertions.

    Scope=module pour ne lancer l'ingestion qu'une seule fois.
    """
    project_root = tmp_path_factory.mktemp("smoke")
    wiki = _bootstrap_wiki(project_root)

    fiche = read_fiche(FICHE_REF)
    source_slug = slugify(fiche.titre)

    report = ingest(
        fiche_path=FICHE_REF,
        wiki_root=wiki,
        do_commit=True,
        do_validate=False,  # La validation est testée dans test_contract.py
    )

    return {
        "project_root": project_root,
        "wiki": wiki,
        "fiche": fiche,
        "source_slug": source_slug,
        "report": report,
    }


# === 8 assertions SPECS.md Bloc 5 ========================================


# 1. index.md contient une entrée pour la nouvelle page source

def test_index_has_source_entry(smoke_result):
    wiki = smoke_result["wiki"]
    source_slug = smoke_result["source_slug"]

    index_text = (wiki / "index.md").read_text(encoding="utf-8")
    wikilink = f"[[sources/{source_slug}]]"
    assert wikilink in index_text, (
        f"Assertion 1 : index.md ne contient pas {wikilink}"
    )


# 2. wiki/sources/ contient la page créée avec les 5 sections du template

_TEMPLATE_SECTIONS = [
    "## Thèse centrale",
    "## Concepts clés",
    "## Trois idées principales",
    "## Liens vers concepts transversaux",
    "## Note personnelle",
]


def test_source_page_has_template_sections(smoke_result):
    wiki = smoke_result["wiki"]
    source_slug = smoke_result["source_slug"]

    source_page = wiki / "sources" / f"{source_slug}.md"
    assert source_page.is_file(), (
        f"Assertion 2 : page source absente : {source_page.name}"
    )

    text = source_page.read_text(encoding="utf-8")
    for section in _TEMPLATE_SECTIONS:
        assert section in text, (
            f"Assertion 2 : section '{section}' absente de la page source"
        )


# 3. "Note personnelle" est présente et non vide si la fiche contient des notes

def test_note_personnelle_present(smoke_result):
    wiki = smoke_result["wiki"]
    fiche = smoke_result["fiche"]
    source_slug = smoke_result["source_slug"]

    source_page = wiki / "sources" / f"{source_slug}.md"
    text = source_page.read_text(encoding="utf-8")

    marker = "## Note personnelle\n\n"
    idx = text.find(marker)
    assert idx != -1, (
        "Assertion 3 : section '## Note personnelle' absente"
    )

    note_content = text[idx + len(marker):].rstrip("\n")

    if fiche.mes_notes:
        assert note_content != "", (
            "Assertion 3 : Note personnelle vide alors que la fiche "
            "contient des notes"
        )
        assert note_content != "*(aucune note dans la fiche source)*", (
            "Assertion 3 : Note personnelle contient le placeholder "
            "alors que la fiche a des notes"
        )


# 4. Au moins une page wiki/concepts/ a été créée ou mise à jour

def test_at_least_one_concept_page(smoke_result):
    wiki = smoke_result["wiki"]

    concept_pages = list((wiki / "concepts").glob("*.md"))
    assert len(concept_pages) >= 1, (
        "Assertion 4 : aucune page concept créée dans wiki/concepts/"
    )


# 5. log.md contient une entrée ## [date] ingest | [nom-source]

def test_log_has_ingest_entry(smoke_result):
    wiki = smoke_result["wiki"]
    source_slug = smoke_result["source_slug"]

    log_text = (wiki / "log.md").read_text(encoding="utf-8")
    today = date.today().isoformat()

    expected_prefix = f"## [{today}] ingest | {source_slug}"
    assert expected_prefix in log_text, (
        f"Assertion 5 : log.md ne contient pas l'entrée attendue :\n"
        f"  attendu : {expected_prefix}\n"
        f"  log.md  : {log_text[:500]}"
    )


# 6. git log --oneline montre un commit ingest: [nom-source]

def test_git_commit_exists(smoke_result):
    project_root = smoke_result["project_root"]
    source_slug = smoke_result["source_slug"]

    result = subprocess.run(
        ["git", "log", "--oneline"],
        cwd=str(project_root),
        check=True,
        capture_output=True,
        text=True,
    )
    expected_msg = f"ingest: {source_slug}"
    assert expected_msg in result.stdout, (
        f"Assertion 6 : commit '{expected_msg}' absent de git log :\n"
        f"  git log : {result.stdout.strip()}"
    )


# 7. Le compte-rendu contient une question transversale non vide

_REPORT_QUESTION_RE = re.compile(
    r"\*\*Question transversale émergente\*\* *: *(.*)", re.MULTILINE
)


def test_report_has_transversal_question(smoke_result):
    report = smoke_result["report"]

    m = _REPORT_QUESTION_RE.search(report)
    assert m is not None, (
        "Assertion 7 : champ 'Question transversale émergente' "
        "absent du compte-rendu"
    )
    question = m.group(1).strip()
    assert question != "", (
        "Assertion 7 : question transversale vide dans le compte-rendu"
    )


# 8. Aucun fichier hors wiki/ dans git diff

def test_no_files_outside_wiki(smoke_result):
    project_root = smoke_result["project_root"]

    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1..HEAD"],
        cwd=str(project_root),
        check=True,
        capture_output=True,
        text=True,
    )
    changed_files = [
        f for f in result.stdout.strip().splitlines() if f.strip()
    ]

    outside = [f for f in changed_files if not f.startswith("wiki/")]
    assert outside == [], (
        f"Assertion 8 : fichiers modifiés hors wiki/ :\n"
        + "\n".join(f"  • {f}" for f in outside)
    )
