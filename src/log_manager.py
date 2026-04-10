"""
src/log_manager.py — Wiki LLM

Append une entrée dans wiki/log.md après chaque opération.

Format d'une entrée (SPECS.md Bloc 2) :
    ## [YYYY-MM-DD] type | nom
    description optionnelle sur une ou plusieurs lignes

Types valides :
    ingest, query, contradiction, qualite, insuffisant, nouveau-dossier

Discipline :
- Append-only strict. Le module n'OUVRE jamais le fichier en lecture, ne
  parse jamais le contenu existant. La seule opération autorisée est
  d'écrire en mode 'a' à la fin du fichier.
- La date est obtenue via `date.today()` à chaque appel — jamais fournie
  par l'appelant. La règle « jamais inventer un timestamp » est respectée
  structurellement : il est impossible de passer une date arbitraire à
  ce module, donc impossible d'en falsifier une.
- Un type invalide lève ValueError avec un message lisible. Aucune entrée
  ne doit être écrite silencieusement avec un type incorrect.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

# Permettre l'exécution en script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


DEFAULT_WIKI_ROOT = _PROJECT_ROOT / "wiki"

VALID_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "ingest",
        "query",
        "contradiction",
        "qualite",
        "insuffisant",
        "nouveau-dossier",
    }
)


# --- API publique --------------------------------------------------------


def append_log_entry(
    event_type: str,
    name: str,
    description: str | None = None,
    wiki_root: Path | str = DEFAULT_WIKI_ROOT,
) -> dict:
    """Append une entrée à la fin de wiki/log.md.

    Args:
        event_type: l'un de VALID_EVENT_TYPES.
        name: identifiant court de l'événement (nom de source, sujet de
            requête, nom de concept, etc.).
        description: texte libre optionnel ajouté sous le préfixe.
        wiki_root: racine du wiki. Par défaut ~/Projects/wiki-llm/wiki/.

    Returns:
        dict avec :
            "date"        : str (YYYY-MM-DD)
            "event_type"  : str
            "name"        : str
            "log_path"    : Path absolu du log.md écrit
            "entry"       : str complète de l'entrée appendée
              (sans le saut de ligne d'amorce)

    Raises:
        ValueError: si event_type n'est pas dans VALID_EVENT_TYPES, ou si
            log.md est absent (le bootstrap doit avoir été lancé).
    """
    if event_type not in VALID_EVENT_TYPES:
        raise ValueError(
            f"Type d'événement invalide : {event_type!r}.\n"
            f"Types acceptés : {sorted(VALID_EVENT_TYPES)}."
        )

    today = date.today().isoformat()
    log_path = Path(wiki_root) / "log.md"

    if not log_path.is_file():
        raise ValueError(
            f"log.md introuvable : {log_path}\n"
            f"Lance d'abord le bootstrap (Prompt 1) pour créer la structure."
        )

    header = f"## [{today}] {event_type} | {name}"
    entry = header + "\n"
    if description:
        entry += description.rstrip("\n") + "\n"

    # Append-only strict — ouverture en mode 'a', un saut de ligne d'amorce
    # garantit la séparation visuelle d'avec l'entrée précédente même si le
    # fichier ne se termine pas par une ligne blanche.
    with log_path.open("a", encoding="utf-8") as f:
        f.write("\n" + entry)

    return {
        "date": today,
        "event_type": event_type,
        "name": name,
        "log_path": log_path,
        "entry": entry,
    }


# --- Test manuel ---------------------------------------------------------

if __name__ == "__main__":
    print("=== Append entrée ingest ===")
    r1 = append_log_entry(
        event_type="ingest",
        name="claude-vient-de-prendre-le-controle-de-votre-mac",
        description="Ingestion de la fiche computer-use : 1 page source créée, 3 pages concepts touchées.",
    )
    print(f"  date  : {r1['date']}")
    print(f"  type  : {r1['event_type']}")

    print("\n=== Append entrée contradiction ===")
    r2 = append_log_entry(
        event_type="contradiction",
        name="agents-ia",
        description="Tension d'horizon entre source-deux-philosophies (opportunité) et source-rationnement (collision énergétique).",
    )
    print(f"  date  : {r2['date']}")
    print(f"  type  : {r2['event_type']}")

    print("\n=== Append entrée qualite (sans description) ===")
    r3 = append_log_entry(
        event_type="qualite",
        name="contrôle santé du wiki",
    )
    print(f"  date  : {r3['date']}")
    print(f"  type  : {r3['event_type']}")

    print("\n=== Contenu de wiki/log.md ===")
    print((DEFAULT_WIKI_ROOT / "log.md").read_text(encoding="utf-8"))

    print("=== Test type invalide ===")
    try:
        append_log_entry(
            event_type="bidule",
            name="test",
        )
        print("  ❌ Aucune exception levée — comportement incorrect.")
        sys.exit(1)
    except ValueError as e:
        print(f"  ✅ ValueError levée comme attendu :")
        for line in str(e).splitlines():
            print(f"     {line}")
