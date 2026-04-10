"""
tests/test_contract.py — Wiki LLM

9 tests de contrat dérivés de SPECS.md Bloc 5.
Écrits AVANT les modules validateur et orchestrateur.

Principe : si un test échoue, on corrige le module concerné — JAMAIS le test.

Chaque test opère sur un wiki temporaire (tmp_path) pour garantir
l'isolation. Les fixtures sont les fiches -reduit.md de wiki-test/.
"""

from __future__ import annotations

import hashlib
import re
import shutil
import time
from pathlib import Path

import pytest

# --- Chemin projet -------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = PROJECT_ROOT / "wiki-test"

# Fiche de test principale (computer-use)
FICHE_COMPUTER_USE = (
    FIXTURES_DIR
    / "2026-03-24-40-millions-de-vues-en-12h-claude-computer-use-enterre-le-travail-de-bureau-reduit.md"
)
# Seconde fiche (deux-philosophies) — pour tests multi-sources
FICHE_DEUX_PHILO = (
    FIXTURES_DIR
    / "2026-01-26-deux-philosophies-deux-trajectoires-et-un-basculement-vers-l-economie-des-agents-reduit.md"
)

import sys

sys.path.insert(0, str(PROJECT_ROOT))

from src.reader import read_fiche  # noqa: E402
from src.source_writer import slugify, write_source_page  # noqa: E402
from src.concept_writer import write_concept_page  # noqa: E402
from src.index_manager import update_index  # noqa: E402
from src.log_manager import append_log_entry  # noqa: E402
from src.contradiction_manager import record_contradiction  # noqa: E402


# --- Helpers--------------------------------------------------------------


def _bootstrap_wiki(wiki_root: Path) -> None:
    """Crée la structure wiki minimale dans un répertoire temporaire."""
    wiki_root.mkdir(parents=True, exist_ok=True)
    for sub in ("sources", "concepts", "syntheses", "a-traiter"):
        (wiki_root / sub).mkdir(exist_ok=True)

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

    (wiki_root / "log.md").write_text(
        "# Journal du wiki\n", encoding="utf-8"
    )

    (wiki_root / "contradictions.md").write_text(
        "# Contradictions détectées\n\n*(aucune contradiction enregistrée)*\n",
        encoding="utf-8",
    )


def _dir_sha256(directory: Path) -> str:
    """Calcule un hash déterministe d'un dossier (contenu de tous les fichiers,
    triés par chemin relatif)."""
    h = hashlib.sha256()
    for f in sorted(directory.rglob("*")):
        if f.is_file():
            h.update(str(f.relative_to(directory)).encode())
            h.update(f.read_bytes())
    return h.hexdigest()


def _extract_section(text: str, header: str) -> str:
    """Extrait le contenu d'une section ## header jusqu'à la prochaine ##."""
    pattern = re.compile(
        rf"^{re.escape(header)}\n(.*?)(?=\n## |\Z)", re.DOTALL | re.MULTILINE
    )
    m = pattern.search(text)
    return m.group(1) if m else ""


# Regex pour les wikilinks [[cible]] et liens markdown [texte](cible.md)
_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+\.md)\)")


# === TC-01 — Règle 1 =====================================================
# Après ingestion d'une source, les sections non concernées d'une page
# concept existante sont inchangées octet par octet.


class TestTC01:
    def test_unchanged_sections_after_second_ingestion(self, tmp_path):
        wiki = tmp_path / "wiki"
        _bootstrap_wiki(wiki)

        fiche = read_fiche(FICHE_COMPUTER_USE)
        concept_name = fiche.concepts_cles[0]["nom"]
        concept_slug = slugify(concept_name)

        # Run 1 — création de la page concept
        write_concept_page(concept_name, fiche, FICHE_COMPUTER_USE.name, wiki)
        page_path = wiki / "concepts" / f"{concept_slug}.md"
        after_run1 = page_path.read_text(encoding="utf-8")

        # Snapshot des sections qui ne doivent PAS bouger
        def_section_1 = _extract_section(after_run1, "## Définition synthétique")
        tensions_1 = _extract_section(after_run1, "## Tensions et contradictions")
        questions_1 = _extract_section(after_run1, "## Questions ouvertes")

        # Run 2 — réingestion de la même fiche (mode doublon)
        write_concept_page(concept_name, fiche, FICHE_COMPUTER_USE.name, wiki)
        after_run2 = page_path.read_text(encoding="utf-8")

        def_section_2 = _extract_section(after_run2, "## Définition synthétique")
        tensions_2 = _extract_section(after_run2, "## Tensions et contradictions")
        questions_2 = _extract_section(after_run2, "## Questions ouvertes")

        assert def_section_1 == def_section_2, (
            "TC-01 : ## Définition synthétique modifiée après réingestion"
        )
        assert tensions_1 == tensions_2, (
            "TC-01 : ## Tensions et contradictions modifiée après réingestion"
        )
        assert questions_1 == questions_2, (
            "TC-01 : ## Questions ouvertes modifiée après réingestion"
        )


# === TC-02 — Règle 2 =====================================================
# Une contradiction détectée déclenche une nouvelle entrée dans
# contradictions.md contenant les deux noms de source, la nature et le statut.


class TestTC02:
    def test_contradiction_entry_complete(self, tmp_path):
        wiki = tmp_path / "wiki"
        _bootstrap_wiki(wiki)

        # Prérequis : créer la page concept cible
        fiche = read_fiche(FICHE_COMPUTER_USE)
        concept_name = fiche.concepts_cles[0]["nom"]
        write_concept_page(concept_name, fiche, FICHE_COMPUTER_USE.name, wiki)

        source_a = slugify(fiche.titre)
        source_b = "rationnement-energie-ia"

        result = record_contradiction(
            concept_name=concept_name,
            source_a_slug=source_a,
            position_a="le contrôle machine libère les apps sans API",
            source_b_slug=source_b,
            position_b="la contrainte énergétique bloque la généralisation",
            nature="tension d'horizon",
            wiki_root=wiki,
        )
        assert result["action"] == "recorded"

        text = (wiki / "contradictions.md").read_text(encoding="utf-8")

        # Vérifie la présence des éléments structurels obligatoires
        assert f"[[sources/{source_a}]]" in text, (
            "TC-02 : source A absente de contradictions.md"
        )
        assert f"[[sources/{source_b}]]" in text, (
            "TC-02 : source B absente de contradictions.md"
        )
        assert "**Nature** : tension d'horizon" in text, (
            "TC-02 : nature absente de contradictions.md"
        )
        assert "**Statut** : ouvert" in text, (
            "TC-02 : statut absent de contradictions.md"
        )


# === TC-03 — Règle 3 =====================================================
# « Mes notes » reproduit verbatim sous « Note personnelle : ».
# Diff = 0.


class TestTC03:
    def test_mes_notes_verbatim(self, tmp_path):
        wiki = tmp_path / "wiki"
        _bootstrap_wiki(wiki)

        fiche = read_fiche(FICHE_COMPUTER_USE)
        # Prérequis : la fiche doit contenir des notes
        assert fiche.mes_notes, (
            "TC-03 : la fiche de test ne contient pas de section Mes notes"
        )

        page_path = write_source_page(fiche, FICHE_COMPUTER_USE.name, wiki)
        page_text = page_path.read_text(encoding="utf-8")

        # Extraire ce qui se trouve après "## Note personnelle\n\n"
        marker = "## Note personnelle\n\n"
        idx = page_text.find(marker)
        assert idx != -1, (
            "TC-03 : section ## Note personnelle absente de la page source"
        )
        # Le contenu va du marker à la fin du fichier (dernière section)
        note_in_page = page_text[idx + len(marker) :].rstrip("\n")

        assert note_in_page == fiche.mes_notes, (
            "TC-03 : Note personnelle ≠ Mes notes (diff ≠ 0)\n"
            f"  attendu ({len(fiche.mes_notes)} chars) : {fiche.mes_notes!r}\n"
            f"  obtenu  ({len(note_in_page)} chars) : {note_in_page!r}"
        )


# === TC-04 — Règle 4 =====================================================
# index.md porte un timestamp de modification antérieur ou égal à celui
# de toute autre page modifiée lors de la même ingestion.


class TestTC04:
    def test_index_modified_first(self, tmp_path):
        wiki = tmp_path / "wiki"
        _bootstrap_wiki(wiki)

        fiche = read_fiche(FICHE_COMPUTER_USE)
        source_slug = slugify(fiche.titre)
        concept_name = fiche.concepts_cles[0]["nom"]

        # Étape 1 — index AVANT toute autre page (contrat Workflow A)
        update_index(
            page_type="source",
            page_name=fiche.titre,
            summary=fiche.these_centrale[:80],
            relative_path=f"sources/{source_slug}",
            wiki_root=wiki,
        )
        index_mtime = (wiki / "index.md").stat().st_mtime_ns

        # Petite pause pour garantir une résolution temporelle distincte
        time.sleep(0.05)

        # Étape 2 — page source
        write_source_page(fiche, FICHE_COMPUTER_USE.name, wiki)
        source_mtime = (wiki / "sources" / f"{source_slug}.md").stat().st_mtime_ns

        # Étape 3 — page concept
        write_concept_page(concept_name, fiche, FICHE_COMPUTER_USE.name, wiki)
        concept_slug = slugify(concept_name)
        concept_mtime = (wiki / "concepts" / f"{concept_slug}.md").stat().st_mtime_ns

        assert index_mtime <= source_mtime, (
            "TC-04 : index.md modifié APRÈS la page source"
        )
        assert index_mtime <= concept_mtime, (
            "TC-04 : index.md modifié APRÈS la page concept"
        )


# === TC-05 — Règle 5 =====================================================
# Chaque lien [[cible]] ou [texte](cible.md) pointe vers un fichier
# existant dans wiki/.


class TestTC05:
    def test_all_links_resolve(self, tmp_path):
        wiki = tmp_path / "wiki"
        _bootstrap_wiki(wiki)

        fiche = read_fiche(FICHE_COMPUTER_USE)
        source_slug = slugify(fiche.titre)

        # Simuler une ingestion minimale
        update_index(
            page_type="source",
            page_name=fiche.titre,
            summary=fiche.these_centrale[:80],
            relative_path=f"sources/{source_slug}",
            wiki_root=wiki,
        )
        write_source_page(fiche, FICHE_COMPUTER_USE.name, wiki)

        for concept in fiche.concepts_cles:
            cname = concept["nom"]
            cslug = slugify(cname)
            write_concept_page(cname, fiche, FICHE_COMPUTER_USE.name, wiki)
            update_index(
                page_type="concept",
                page_name=cname,
                summary=concept.get("definition", "")[:80],
                relative_path=f"concepts/{cslug}",
                wiki_root=wiki,
            )

        # Vérification : scanner tous les fichiers .md du wiki
        broken: list[str] = []
        for md_file in wiki.rglob("*.md"):
            text = md_file.read_text(encoding="utf-8")
            rel = md_file.relative_to(wiki)

            # Wikilinks [[cible]]
            for m in _WIKILINK_RE.finditer(text):
                target = m.group(1)
                # Ignorer les wikilinks vers contradictions (fichier racine)
                if target == "contradictions":
                    target_path = wiki / "contradictions.md"
                else:
                    target_path = wiki / f"{target}.md"
                if not target_path.is_file():
                    broken.append(f"{rel}: [[{target}]] → {target_path}")

            # Liens markdown [texte](cible.md)
            for m in _MD_LINK_RE.finditer(text):
                href = m.group(2)
                # Chemin relatif au fichier qui contient le lien
                target_path = (md_file.parent / href).resolve()
                if not target_path.is_file():
                    broken.append(f"{rel}: [{m.group(1)}]({href}) → {target_path}")

        assert broken == [], (
            "TC-05 : liens cassés détectés :\n" + "\n".join(f"  • {b}" for b in broken)
        )


# === TC-06 — Règle 6 =====================================================
# Le hash SHA256 du dossier de sources brutes est identique avant et après
# une ingestion. On utilise wiki-test/ comme proxy de YT-Knowledge/.


class TestTC06:
    def test_source_dir_immutable(self, tmp_path):
        wiki = tmp_path / "wiki"
        _bootstrap_wiki(wiki)

        # Copier les fixtures dans un dossier isolé pour contrôler le hash
        sources_dir = tmp_path / "YT-Knowledge"
        shutil.copytree(FIXTURES_DIR, sources_dir)

        hash_before = _dir_sha256(sources_dir)

        # Opérations de lecture sur la fiche
        fiche_path = (
            sources_dir
            / FICHE_COMPUTER_USE.name
        )
        fiche = read_fiche(fiche_path)

        # Opérations d'écriture dans le wiki (ne doivent pas toucher sources)
        write_source_page(fiche, fiche_path.name, wiki)
        for concept in fiche.concepts_cles:
            write_concept_page(
                concept["nom"], fiche, fiche_path.name, wiki
            )

        hash_after = _dir_sha256(sources_dir)

        assert hash_before == hash_after, (
            "TC-06 : le dossier de sources brutes a été modifié par l'ingestion\n"
            f"  avant : {hash_before}\n"
            f"  après : {hash_after}"
        )


# === TC-07 — Règle 11 ====================================================
# Après une ingestion, seuls des fichiers sous wiki/sources/,
# wiki/concepts/, wiki/syntheses/, wiki/a-traiter/ (+ fichiers racine
# index.md, log.md, contradictions.md) ont été modifiés.


class TestTC07:
    def test_write_perimeter(self, tmp_path):
        wiki = tmp_path / "wiki"
        _bootstrap_wiki(wiki)

        # Snapshot des fichiers avant
        before: dict[Path, bytes] = {}
        for f in wiki.rglob("*"):
            if f.is_file():
                before[f] = f.read_bytes()

        fiche = read_fiche(FICHE_COMPUTER_USE)
        source_slug = slugify(fiche.titre)

        # Ingestion complète
        update_index(
            page_type="source",
            page_name=fiche.titre,
            summary=fiche.these_centrale[:80],
            relative_path=f"sources/{source_slug}",
            wiki_root=wiki,
        )
        write_source_page(fiche, FICHE_COMPUTER_USE.name, wiki)
        for concept in fiche.concepts_cles:
            cname = concept["nom"]
            cslug = slugify(cname)
            write_concept_page(cname, fiche, FICHE_COMPUTER_USE.name, wiki)
            update_index(
                page_type="concept",
                page_name=cname,
                summary=concept.get("definition", "")[:80],
                relative_path=f"concepts/{cslug}",
                wiki_root=wiki,
            )
        append_log_entry(
            event_type="ingest",
            name=source_slug,
            wiki_root=wiki,
        )

        # Identifier tous les fichiers créés ou modifiés
        allowed_prefixes = ("sources/", "concepts/", "syntheses/", "a-traiter/")
        allowed_root_files = ("index.md", "log.md", "contradictions.md")

        violations: list[str] = []
        for f in wiki.rglob("*"):
            if not f.is_file():
                continue
            rel = str(f.relative_to(wiki))
            # Fichier existait avant et n'a pas changé → ok
            if f in before and before[f] == f.read_bytes():
                continue
            # Fichier nouveau ou modifié — vérifier le périmètre
            if rel in allowed_root_files:
                continue
            if any(rel.startswith(p) for p in allowed_prefixes):
                continue
            violations.append(rel)

        assert violations == [], (
            "TC-07 : fichiers modifiés hors périmètre :\n"
            + "\n".join(f"  • {v}" for v in violations)
        )


# === TC-08 — Règle 12 ====================================================
# Le compte-rendu de fin d'ingestion contient au moins une question
# transversale (champ non vide).
#
# Le module orchestrateur n'existe pas encore. Ce test valide le FORMAT
# du compte-rendu : toute chaîne retournée comme compte-rendu doit
# contenir le champ « Question transversale émergente » non vide.


_REPORT_FIELD_RE = re.compile(
    r"\*\*Question transversale émergente\*\* *: *(.*)", re.MULTILINE
)


class TestTC08:
    def test_report_has_transversal_question(self):
        # Compte-rendu conforme : champ rempli
        report_ok = (
            "## Compte-rendu — ingestion computer-use\n"
            "**Pages créées** : sources/computer-use, concepts/controle-machine\n"
            "**Pages mises à jour** : aucune\n"
            "**Tensions détectées** : aucune\n"
            "**Question transversale émergente** : Comment la généralisation "
            "du contrôle machine affecte-t-elle l'architecture de confiance ?\n"
            "**Commit** : abc1234\n"
        )
        m = _REPORT_FIELD_RE.search(report_ok)
        assert m is not None, (
            "TC-08 : champ 'Question transversale émergente' absent du compte-rendu"
        )
        question = m.group(1).strip()
        assert question != "", (
            "TC-08 : question transversale vide dans le compte-rendu"
        )

    def test_report_rejects_empty_question(self):
        # Compte-rendu non conforme : champ vide
        report_empty = (
            "## Compte-rendu — ingestion test\n"
            "**Pages créées** : aucune\n"
            "**Pages mises à jour** : aucune\n"
            "**Tensions détectées** : aucune\n"
            "**Question transversale émergente** :   \n"
            "**Commit** : def5678\n"
        )
        m = _REPORT_FIELD_RE.search(report_empty)
        if m is not None:
            question = m.group(1).strip()
            assert question == "", (
                "TC-08 : un compte-rendu avec question vide doit être rejeté "
                "par le validateur (à implémenter dans Prompt 9)"
            )

    def test_report_rejects_missing_field(self):
        # Compte-rendu non conforme : champ absent
        report_missing = (
            "## Compte-rendu — ingestion test\n"
            "**Pages créées** : aucune\n"
            "**Pages mises à jour** : aucune\n"
            "**Tensions détectées** : aucune\n"
            "**Commit** : ghi9012\n"
        )
        m = _REPORT_FIELD_RE.search(report_missing)
        assert m is None, (
            "TC-08 : un compte-rendu sans le champ question transversale "
            "ne doit pas matcher la regex de validation"
        )


# === TC-09 — Règle 14 ====================================================
# Toute affirmation d'une réponse à requête cite explicitement une page
# du wiki/. Aucune affirmation sans citation.
#
# Le module de requête n'existe pas encore. Ce test valide le FORMAT
# de réponse : chaque phrase du champ **Réponse** doit contenir au
# moins un wikilink [[page]].

_RESPONSE_FIELD_RE = re.compile(
    r"\*\*Réponse\*\*\s*:\s*(.+?)(?=\n\*\*)", re.DOTALL
)


def _sentences_without_citation(response_text: str) -> list[str]:
    """Retourne les phrases du champ Réponse qui ne citent aucune page wiki."""
    m = _RESPONSE_FIELD_RE.search(response_text)
    if not m:
        return ["CHAMP **Réponse** ABSENT"]
    prose = m.group(1).strip()
    # Découper en phrases (point suivi d'espace ou fin de texte)
    sentences = [s.strip() for s in re.split(r"(?<=\.)\s+", prose) if s.strip()]
    return [s for s in sentences if "[[" not in s]


class TestTC09:
    def test_response_all_citations(self):
        # Réponse conforme
        response_ok = (
            "**Réponse** : Le contrôle machine permet à l'agent de naviguer "
            "dans l'environnement réel de l'utilisateur ([[concepts/controle-machine-computer-use]]). "
            "L'architecture de confiance pose la question du compromis entre "
            "souveraineté et puissance ([[concepts/architecture-de-confiance]]).\n"
            "**Pages mobilisées** : [[concepts/controle-machine-computer-use]] "
            "[[concepts/architecture-de-confiance]]\n"
            "**Lacunes détectées** : le wiki ne couvre pas encore les benchmarks\n"
            "**Fiche suggérée** : benchmarks agents IA\n"
        )
        uncited = _sentences_without_citation(response_ok)
        assert uncited == [], (
            "TC-09 : phrases sans citation dans une réponse conforme :\n"
            + "\n".join(f"  • {s}" for s in uncited)
        )

    def test_response_rejects_uncited_sentence(self):
        # Réponse non conforme : seconde phrase sans citation
        response_bad = (
            "**Réponse** : Le contrôle machine est important ([[concepts/controle-machine-computer-use]]). "
            "Les agents IA vont transformer le travail de bureau.\n"
            "**Pages mobilisées** : [[concepts/controle-machine-computer-use]]\n"
            "**Lacunes détectées** : aucune\n"
            "**Fiche suggérée** : aucune\n"
        )
        uncited = _sentences_without_citation(response_bad)
        assert len(uncited) > 0, (
            "TC-09 : une phrase sans citation aurait dû être détectée"
        )
        assert "Les agents IA" in uncited[0]
