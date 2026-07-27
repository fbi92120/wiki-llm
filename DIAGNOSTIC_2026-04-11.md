# Diagnostic — Wiki LLM vs YT Extractor
**Date** : 2026-04-11
**Objet** : etat reel des deux projets par rapport aux specs Wiki LLM

---

## 1. Structure wiki-llm

Conforme aux specs. `wiki/` contient 84 concepts, 24 sources, index, log, contradictions.
`config.yml` pointe vers le vault Obsidian iCloud. `ingest.log` present (ignore par git).

Warning R11 detecte a la derniere ingestion : `ingest.log` est dans `wiki/`
donc le validateur le signale comme "hors perimetre". Bug mineur — le
validateur devrait l'exclure.

---

## 2. Structure yt-knowledge-extractor

- Ecrit dans le vault Obsidian configuré (`<vault>/YT-Knowledge/`) en mode obsidian.
- Organise par sous-dossier = slug de la chaine YouTube.
- Produit des **fiches completes** (pas de `-reduit`). Le format `-reduit` n'est pas genere automatiquement — il a ete cree manuellement pour les fixtures.

---

## 3. Format des fiches reelles

Sections presentes dans une fiche YT Extractor recente (2026-04-10) :

```
## These centrale
## Chapitrage infere
## Carte des idees
## Concepts cles
## Formulations notables
## Questions ouvertes
## Mes notes
## Sources & references
```

Pas de section `## Transcript horodate` dans les fiches recentes — le
transcript est absent (commentaire HTML `<!-- TRANSCRIPT -->` uniquement
dans les fixtures plus anciennes de wiki-test/).

---

## 4. reader.py — champs extraits

| Champ | Section lue |
|---|---|
| `titre` | `# titre` (ligne 1) |
| `url`, `chaine`, `duree` | Ligne metadonnees `**URL**` |
| `these_centrale` | `## These centrale` |
| `carte_des_idees` | `## Carte des idees` |
| `concepts_cles` | `## Concepts cles` (sous-blocs `####`) |
| `formulations_notables` | `## Formulations notables` |
| `questions_ouvertes` | `## Questions ouvertes` |
| `mes_notes` | `## Mes notes` |

Sections ignorees par reader.py (par design) : `## Chapitrage infere`,
`## Sources & references`.

---

## 5. Fixtures vs fiches reelles

Les sections sont identiques. La fixture `-reduit.md` et la fiche native
ont exactement les memes 8 sections `##`. La seule difference historique :

- Les fiches natives de wiki-test/ (anciennes) avaient un
  `<!-- TRANSCRIPT HORODATE -->` + transcript brut a la fin — gere par
  `_strip_transcript()`.
- Les fiches recentes de YT Extractor n'ont plus ce transcript.

---

## 6. Resume des ecarts

| Ecart | Impact |
|---|---|
| **Aucun ecart de format** | reader.py lit correctement les fiches natives et les -reduit. Les sections sont les memes. |
| **Warning R11 sur ingest.log** | Le validateur signale `ingest.log` comme fichier hors perimetre. Il devrait l'exclure (c'est un log technique, pas du contenu wiki). |
| **Pas de fiches `-reduit`** | YT Extractor ne genere pas de `-reduit.md`. Les fixtures dans wiki-test/ sont des copies manuelles. reader.py gere les deux formats — pas de probleme fonctionnel. |
| **"Mes notes" souvent vide** | La fiche recente a `*(espace libre)*` dans "Mes notes". reader.py retourne `"*(espace libre)*"` comme contenu — techniquement non vide. Pas un bug, mais la page source affichera ce placeholder sous "Note personnelle". |

---

## Actions identifiees

1. **Bug R11** : exclure `ingest.log` du check R11 dans `validator.py`
2. **Mes notes placeholder** : decider si `*(espace libre)*` doit etre traite comme vide par reader.py
3. **Fixtures wiki-test/** : les `-reduit.md` sont des copies manuelles — documenter ou automatiser

---

*Diagnostic produit par Claude Code — aucune modification appliquee.*
