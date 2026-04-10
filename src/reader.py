"""
src/reader.py — Wiki LLM

Lecteur de fiches produites par YT Knowledge Extractor.
Supporte deux formats :
    - fiches -reduit.md (résumé sans transcript)
    - fiches natives (format complet avec transcript horodaté en fin de fichier)

Le module lit le fichier source et en extrait la matière brute structurée.
Il ne modifie jamais le fichier source (règle 6 de la constitution).

Gestion du transcript :
    Le contenu à partir du marqueur de transcript est ignoré. Deux formes
    reconnues :
    - Section ## Transcript horodaté (ou toute variante ## Transcript…)
    - Commentaire HTML <!-- TRANSCRIPT HORODATÉ … --> (format natif actuel)
    Tout le texte après le premier marqueur trouvé est tronqué avant le
    parsing des sections.

Note de spec — champ `trois_idees` retiré du contrat
-----------------------------------------------------
Le contrat initial du Prompt 2 demandait un champ `trois_idees: list[str]`.
Ce champ a été retiré après vérification de la structure réelle des fiches :
aucune section "Trois idées principales" n'existe dans les fiches -reduit.md.
La synthèse en trois idées appartient au générateur de page source, pas au
reader. Le reader extrait uniquement la matière brute présente dans la fiche.
Décision actée le 2026-04-09.

Sections présentes dans une fiche :
    ## Thèse centrale
    ## Chapitrage inféré        (non extrait — non utilisé par le wiki)
    ## Carte des idées
    ## Concepts clés            (sous-blocs #### nom + définition + exemple)
    ## Formulations notables
    ## Questions ouvertes
    ## Mes notes
    ## Sources & références     (non extrait — non utilisé par le wiki)
    ## Transcript horodaté      (ignoré — tronqué avant parsing)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SourceFiche:
    """Champs extraits d'une fiche -reduit.md, prêts à être consommés
    par le générateur de page source."""

    titre: str = ""
    url: str = ""
    chaine: str = ""
    duree: str = ""
    these_centrale: str = ""
    carte_des_idees: str = ""
    concepts_cles: list[dict] = field(default_factory=list)
    formulations_notables: list[str] = field(default_factory=list)
    questions_ouvertes: list[str] = field(default_factory=list)
    mes_notes: str = ""


# --- Regex ---------------------------------------------------------------

# Ligne de métadonnées :
# **URL** : <url> · **Channel** : <chaine> · **Processed** : <date> · **Duration** : <duree>
_META_RE = re.compile(
    r"\*\*URL\*\*\s*:\s*(?P<url>\S+)"
    r".*?\*\*Channel\*\*\s*:\s*(?P<chaine>.+?)\s*·"
    r".*?\*\*Duration\*\*\s*:\s*(?P<duree>\S+)"
)

# En-tête d'un concept : #### Nom du concept [▶ 00:00:45](https://...)
# Formes reconnues :
#   [▶ HH:MM:SS](url)   — format natif complet
#   [▶ HH:MM:SS]        — sans URL
#   ▶ HH:MM:SS          — timestamp nu
_CONCEPT_HEADER_RE = re.compile(
    r"^####\s+(.+?)"
    r"(?:\s*\[▶[^\]]*\](?:\([^)]*\))?|\s*▶\s*\d{2}:\d{2}:\d{2})?"
    r"\s*$"
)

# Item d'une question ouverte numérotée : "1. ...", "2.  ..."
_QUESTION_ITEM_RE = re.compile(r"^\s*\d+\.\s+(.*)")

# Marqueurs de début de transcript — tout le texte à partir de là est ignoré.
# Forme 1 : section ## Transcript… (## Transcript horodaté, ## Transcript, etc.)
# Forme 2 : commentaire HTML <!-- TRANSCRIPT … -->
_TRANSCRIPT_RE = re.compile(
    r"(?:^## Transcript[^\n]*$|^<!--\s*TRANSCRIPT[^\n]*-->)",
    re.MULTILINE | re.IGNORECASE,
)


# --- API publique --------------------------------------------------------


def read_fiche(path: str | Path) -> SourceFiche:
    """Lit une fiche -reduit.md et retourne ses champs structurés.

    Args:
        path: chemin vers le fichier -reduit.md.

    Returns:
        Un SourceFiche dont les champs absents valent "" ou [], jamais None.

    Raises:
        FileNotFoundError: si le chemin ne pointe pas vers un fichier existant.
            Le message indique le chemin attendu.
    """
    p = Path(path).expanduser()
    if not p.is_file():
        raise FileNotFoundError(
            f"Fiche source introuvable : {p}\n"
            f"Vérifie le chemin et que la fiche -reduit.md existe."
        )

    text = p.read_text(encoding="utf-8")
    text = _strip_transcript(text)
    fiche = SourceFiche()

    fiche.titre = _extract_title(text)
    fiche.url, fiche.chaine, fiche.duree = _extract_metadata(text)

    sections = _split_sections(text)
    fiche.these_centrale = sections.get("Thèse centrale", "").strip()
    fiche.carte_des_idees = sections.get("Carte des idées", "").strip()
    fiche.concepts_cles = _parse_concepts(sections.get("Concepts clés", ""))
    fiche.formulations_notables = _parse_formulations(
        sections.get("Formulations notables", "")
    )
    fiche.questions_ouvertes = _parse_questions(sections.get("Questions ouvertes", ""))
    fiche.mes_notes = sections.get("Mes notes", "").strip()

    return fiche


# --- Helpers internes ----------------------------------------------------


def _strip_transcript(text: str) -> str:
    """Tronque le texte avant le marqueur de transcript.

    Si aucun marqueur n'est trouvé (fiches -reduit.md), retourne le texte
    tel quel — rien ne change pour les fixtures existantes.
    """
    m = _TRANSCRIPT_RE.search(text)
    if m:
        return text[: m.start()].rstrip()
    return text


def _extract_title(text: str) -> str:
    """Première ligne `# titre` du document."""
    for line in text.splitlines():
        if line.startswith("# ") and not line.startswith("## "):
            return line[2:].strip()
    return ""


def _extract_metadata(text: str) -> tuple[str, str, str]:
    """Extrait (url, chaine, duree) depuis la ligne de métadonnées.
    Retourne ("", "", "") si la ligne n'est pas trouvée."""
    m = _META_RE.search(text)
    if not m:
        return "", "", ""
    return m.group("url").strip(), m.group("chaine").strip(), m.group("duree").strip()


def _split_sections(text: str) -> dict[str, str]:
    """Découpe le texte en sections de niveau 2 (## Titre).

    Retourne un dict {titre_section: contenu_brut} où le contenu inclut
    toutes les lignes jusqu'à la prochaine section ## (ou fin de fichier).
    """
    sections: dict[str, str] = {}
    current_title: str | None = None
    current_lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("## ") and not line.startswith("### "):
            if current_title is not None:
                sections[current_title] = "\n".join(current_lines)
            current_title = line[3:].strip()
            current_lines = []
        else:
            if current_title is not None:
                current_lines.append(line)
    if current_title is not None:
        sections[current_title] = "\n".join(current_lines)
    return sections


def _parse_concepts(block: str) -> list[dict]:
    """Découpe le bloc 'Concepts clés' en liste de dicts.

    Chaque concept = {'nom': str, 'definition': str, 'exemple': str}.
    Définition et exemple peuvent être multi-lignes ; elles sont reconcaténées
    en un seul espace.
    """
    if not block.strip():
        return []
    concepts: list[dict] = []
    current: dict | None = None
    pending_field: str | None = None

    for line in block.splitlines():
        header = _CONCEPT_HEADER_RE.match(line)
        if header:
            if current is not None:
                concepts.append(current)
            current = {"nom": header.group(1).strip(), "definition": "", "exemple": ""}
            pending_field = None
            continue

        if current is None:
            continue

        stripped = line.strip()
        if stripped.startswith("**Définition selon l'auteur**"):
            _, _, content = stripped.partition(":")
            current["definition"] = content.strip()
            pending_field = "definition"
        elif stripped.startswith("**Exemple utilisé**"):
            _, _, content = stripped.partition(":")
            current["exemple"] = content.strip()
            pending_field = "exemple"
        elif stripped and pending_field:
            # Continuation d'une définition ou d'un exemple sur plusieurs lignes
            current[pending_field] = (current[pending_field] + " " + stripped).strip()

    if current is not None:
        concepts.append(current)
    return concepts


def _parse_formulations(block: str) -> list[str]:
    """Extrait les citations verbatim du bloc 'Formulations notables'.

    Chaque citation est un bloc de lignes consécutives commençant par '>',
    incluant la ligne du timestamp `> [▶ ...]` quand elle est présente.
    """
    if not block.strip():
        return []
    quotes: list[str] = []
    current: list[str] = []
    for line in block.splitlines():
        if line.startswith(">"):
            current.append(line)
        else:
            if current:
                quotes.append("\n".join(current).strip())
                current = []
    if current:
        quotes.append("\n".join(current).strip())
    return quotes


def _parse_questions(block: str) -> list[str]:
    """Extrait les questions du bloc 'Questions ouvertes'.

    Chaque entrée est une question préfixée par 'N.' dans la fiche source.
    Le numéro est retiré, mais le contenu (y compris les marques Obsidian
    `==…==`) est reproduit verbatim.
    """
    if not block.strip():
        return []
    questions: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            questions.append(" ".join(s.strip() for s in current if s.strip()))
            current.clear()

    for line in block.splitlines():
        m = _QUESTION_ITEM_RE.match(line)
        if m:
            flush()
            current.append(m.group(1))
        elif line.strip() and current:
            current.append(line.strip())
        elif not line.strip():
            flush()
    flush()
    return questions


# --- Test manuel ---------------------------------------------------------

if __name__ == "__main__":
    import sys

    default_test = (
        Path.home()
        / "Projects"
        / "wiki-llm"
        / "wiki-test"
        / "2026-01-26-deux-philosophies-deux-trajectoires-et-un-basculement-vers-l-economie-des-agents-reduit.md"
    )
    test_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_test

    fiche = read_fiche(test_path)
    print(f"Fichier      : {test_path.name}")
    print(f"Titre        : {fiche.titre}")
    print(f"URL          : {fiche.url}")
    print(f"Chaine       : {fiche.chaine}")
    print(f"Duree        : {fiche.duree}")
    print(f"Thèse        : {fiche.these_centrale[:120]}{'…' if len(fiche.these_centrale) > 120 else ''}")
    print(f"Carte idées  : {len(fiche.carte_des_idees)} caractères")
    print(f"Concepts     : {len(fiche.concepts_cles)} concept(s)")
    for c in fiche.concepts_cles:
        print(f"  - {c['nom']}")
        print(f"      def    : {c['definition'][:80]}…")
        print(f"      ex     : {c['exemple'][:80]}…")
    print(f"Formulations : {len(fiche.formulations_notables)} citation(s)")
    print(f"Questions    : {len(fiche.questions_ouvertes)} question(s)")
    print(f"Mes notes    : {len(fiche.mes_notes)} caractères")
    print(f"  contenu    : {fiche.mes_notes!r}")
