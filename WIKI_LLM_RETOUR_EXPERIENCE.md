# Retour d'experience — Wiki LLM
## Document de capitalisation projet

**Auteur** : Francois Biller
**Date** : 2026-04-10
**Repo** : https://github.com/fbi92120/wiki-llm
**Statut** : MVP valide en conditions reelles — 20/20 tests, 19 sources ingerees, vue graphe Obsidian conforme
**Concept source** : [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)

---

## 1. Ce que l'appli fait

Outil LLM pilote (pas un agent autonome) qui maintient une base de
connaissances persistante en fichiers Markdown a partir de fiches
YouTube produites par YT Knowledge Extractor.

```
python3 ingestwiki.py <fiche-reduit.md>
```

Une commande declenche le Workflow A complet :

1. Lecture de la fiche source (format `-reduit.md` ou natif YT Extractor)
2. Mise a jour de `index.md` en premier (regle 4)
3. Creation de la page `wiki/sources/[slug].md`
4. Creation ou mise a jour des pages `wiki/concepts/[slug].md`
5. Append dans `wiki/log.md`
6. Enregistrement des contradictions si signalees
7. Generation du compte-rendu (tensions + question transversale)
8. Validation post-ingestion (9 regles verifiees)
9. Commit git automatique

Le wiki se lit dans Obsidian (vault = `wiki/`). La vue graphe montre
les liens entre sources, concepts et contradictions sans configuration.

**Production reelle** : 19 pages source, 69 pages concept, 88 entrees
d'index, 24 entrees de log — a partir de 19 fiches YT Extractor.

---

## 2. Architecture retenue

### Principe directeur

Orchestrateur passif + modules a responsabilite unique. Zero logique
metier dans le point d'entree CLI. Tout est dans `src/`.

```
Fiche -reduit.md
 |
 +-- src/reader.py           -> lit la fiche, extrait les champs structures
 +-- src/index_manager.py    -> met a jour wiki/index.md
 +-- src/source_writer.py    -> genere wiki/sources/[slug].md
 +-- src/concept_writer.py   -> cree/met a jour wiki/concepts/[slug].md
 +-- src/log_manager.py      -> append dans wiki/log.md
 +-- src/contradiction_manager.py -> enregistre dans contradictions.md + page concept
 +-- src/validator.py         -> verifie les 9 regles post-ingestion
 |
 +-- ingestwiki.py           -> orchestration pure, zero logique metier
```

### Decisions cles

| Decision | Choix | Raison |
|---|---|---|
| Index vs RAG vectoriel | `index.md` simple | Suffisant jusqu'a ~500 pages (Karpathy). RAG reporte en V2-4 |
| Architecture agentique | Reportee en V2-9 | Chaque operation pilotee par l'humain. Pas de boucle autonome |
| Vault Obsidian | `wiki/` dans le projet git | Git et Obsidian cohabitent sans friction. Pas de sync iCloud |
| Orchestrateur passif | Zero logique dans `ingestwiki.py` | Prepare une V2 avec interface differente sans toucher `src/` |
| Tests avant validateur | TC-01 a TC-09 ecrits avant `validator.py` | Les tests definissent le contrat, le code s'y conforme |
| Contradiction manager | Enregistrement seulement, pas de detection | La detection semantique appartient au LLM pilote, pas au code |
| Question transversale | Template formulaique, surchargeable par `--question` | Pas de LLM dans l'orchestrateur — le pilote fournit la synthese |

### Slugification

`slugify()` dans `source_writer.py` : normalisation Unicode NFKD, retrait
des accents, minuscules, tirets. Reutilise par tous les modules.
Un bug de timestamps dans les noms de concepts (herite des fiches YT
Extractor) a necessite un nettoyage defensif dans `concept_writer.py`
(`_clean_concept_name()`) — voir section 7.

---

## 3. Decisions prises pendant l'implementation

### Divergences avec les specs initiales

| Spec | Implementation reelle | Raison |
|---|---|---|
| `trois_idees: list[str]` dans reader.py | Champ retire | Section absente des fiches -reduit.md. La synthese appartient au generateur, pas au reader |
| Chemin du vault : iCloud | `~/Projects/wiki-llm/wiki/` local | Decision prise apres test — git et Obsidian cohabitent sans friction, pas de sync iCloud |
| Detection automatique des contradictions | Enregistrement manuel seulement | Le MVP est pilote — la detection semantique est le travail du LLM, pas du code |
| Fiche de reference smoke test : "La chute d'Anthropic" | Fallback sur premiere fiche disponible | Fiche absente de wiki-test/. Test ecrit avec recherche automatique + fallback |

### Confirmations des specs

- L'index.md comme substitut au RAG fonctionne parfaitement a 88 entrees
- L'ordre d'appel du Workflow A (index en premier) est structurellement garanti par l'orchestrateur
- La separation source/concept/synthese tient dans la duree
- Le journal des mises a jour dans chaque page concept trace correctement les evolutions
- Le format de `contradictions.md` est pret mais inutilise au MVP (aucune contradiction enregistree)

---

## 4. Constitution — les 15 regles non negociables

Definies dans CLAUDE.md avant le premier module. 9 sont testables
automatiquement (TC-01 a TC-09). Les 6 autres sont des garde-fous
comportementaux verifies par revue humaine.

**Fidelite aux sources :**
1. Ne jamais reecrire une page si une mise a jour partielle suffit
2. Signaler explicitement toute contradiction entre sources
3. "Mes notes" reproduites verbatim sous "Note personnelle :"
4. `index.md` mis a jour a chaque ingestion sans exception
5. Ne jamais inventer un lien non etabli par les sources
6. Sources brutes immuables — lire uniquement, jamais modifier

**Integrite du wiki dans le temps :**
7. Jamais supprimer, renommer ou deplacer une page sans instruction humaine
8. Nouvelle source qui contredit : ajouter un angle, jamais ecraser
9. Page orpheline : signaler immediatement
10. Source insuffisante : deplacer dans `a-traiter/`, log label `insuffisant`

**Discipline d'execution :**
11. Perimetre d'ecriture : `sources/`, `concepts/`, `syntheses/`, `a-traiter/` uniquement
12. Fin d'ingestion : compte-rendu avec tensions + question transversale
13. Template page source : fixe pour Workflow A
14. Reponse a une requete : depuis le wiki uniquement
15. `wiki/` versionne avec git — commit apres chaque ingestion

**Lecon** : la constitution de YT Extractor avait 8 regles. Celle-ci en a 15
parce que le systeme est stateful — les regles d'integrite dans le temps
(7-10) n'existaient pas dans un projet stateless.

---

## 5. Sequence d'implementation suivie

```
Phase 0 — Corrections de terminologie
  Prompt 0-A  CLAUDE.md : "outil LLM pilote" au lieu de "agent"
  Prompt 0-B  decisions.md : V2-9 architecture agentique
  Prompt 0-C  explication-methode.md : note terminologique

Phase 1 — Implementation (12 prompts dans l'ordre SPECS.md Bloc 5)
  Prompt 1   Bootstrap : structure wiki/ + fichiers initiaux + git init
  Prompt 2   src/reader.py : lecteur de fiches -reduit.md
  Prompt 3   src/source_writer.py : generateur pages sources/
  Prompt 4   src/concept_writer.py : generateur/metteur a jour concepts/
  Prompt 5   src/index_manager.py : gestionnaire index.md
  Prompt 6   src/log_manager.py : gestionnaire log.md
  Prompt 7   src/contradiction_manager.py : gestionnaire contradictions.md
  Prompt 8   tests/test_contract.py : 9 tests de contrat (AVANT validateur)
  Prompt 9   src/validator.py : verificateur post-ingestion
  Prompt 10  ingestwiki.py : orchestrateur Workflow A
  Prompt 11  tests/test_smoke.py : test bout en bout
  Prompt 12  README.md + README.fr.md
```

**Regle validee** : les tests de contrat (Prompt 8) sont ecrits AVANT le
validateur (Prompt 9) et l'orchestrateur (Prompt 10). Le validateur se
conforme aux tests, pas l'inverse.

**Regle validee** : 1 prompt = 1 module = verification avant de passer
au suivant. Chaque module a ete teste isolement avant integration.

---

## 6. Ce qui a bien fonctionne

**Les specs co-construites en amont** : 1 286 lignes de specs
(SPECS.md + CLAUDE.md + decisions.md + explication-methode.md +
PROMPTS_CLAUDE_CODE.md) pour 3 533 lignes de Python. Ratio 1:2.7.
Les specs ont elimine les ambiguites avant que le code les rencontre.

**Constitution avant code** : les 15 regles definies dans CLAUDE.md
ont rendu les decisions d'implementation mecaniques. Quand un cas
limite apparaissait, la regle existait deja.

**Tests de contrat avant validateur** : les 9 tests TC-01 a TC-09
ont ete ecrits avant `validator.py`. Le validateur a ete ecrit pour
que les tests passent — pas l'inverse. Un seul ajustement de regex
(TC-08 : `_REPORT_FIELD_RE` traversait les lignes via `\s*`) corrige
dans le test, pas dans le module.

**L'orchestrateur passif** : `ingestwiki.py` ne contient aucune
logique metier (408 lignes d'orchestration pure). Changer l'ordre
des operations ou ajouter un module ne casse rien.

**Le format natif YT Extractor** : ajouter le support des fiches
natives (avec transcript horodate) a necessite une seule fonction
(`_strip_transcript()`, 8 lignes) sans modifier aucune autre partie
du code. Le reader tronque avant le marqueur de transcript, les
modules en aval ne voient pas la difference.

**Obsidian comme vault direct** : ouvrir `wiki/` comme vault
Obsidian fonctionne sans aucune configuration. La vue graphe montre
immediatement les liens entre pages. Git et Obsidian cohabitent.

---

## 7. Ce qui aurait du etre fait differemment

**Le chemin du vault** : les specs initiales prevoyaient d'ecrire
directement dans le vault Obsidian sur iCloud. Cette decision a ete
reversee pendant l'implementation — `wiki/` est maintenant dans le
projet git, ouvert comme vault Obsidian. La decision aurait du etre
tranchee dans les specs, pas decouverte pendant le code.

**Les timestamps dans les noms de concepts** : les fiches YT Extractor
contiennent des timestamps (`[00:01:29]`) dans les headers de concepts.
Le reader les retirait via regex, mais certaines formes (`[00:01:29]`
sans URL, `00:01:29` nu) passaient entre les mailles. Resultat : 13
pages concept avec des slugs pollues (`securite-des-modeles-00-00-48.md`).
Corrige par un nettoyage defensif dans `concept_writer.py` +
renommage de masse des pages + mise a jour de toutes les references.
**Lecon** : tester le slugify sur des donnees reelles des les specs,
pas en production.

**La fiche de reference du smoke test** : les specs designaient
"La chute d'Anthropic" comme fiche de reference. Elle n'existait pas
dans wiki-test/. Le test a ete ecrit avec un fallback automatique.
**Lecon** : verifier la disponibilite des fixtures avant de les
designer dans les specs.

**Python 3.9 sur Mac systeme** : meme probleme que YT Extractor.
La syntaxe `str | None` (Python 3.10+) impose `from __future__ import annotations`
en tete de chaque fichier. Accepte comme pattern recurrent en attendant
la migration Python 3.12.

---

## 8. Tests — resultats reels

### 9 tests de contrat

| # | Regle | Contrat | Resultat |
|---|---|---|---|
| TC-01 | R1 | Sections non concernees inchangees octet par octet | PASS |
| TC-02 | R2 | Contradiction dans contradictions.md avec sources, nature, statut | PASS |
| TC-03 | R3 | Mes notes reproduites verbatim (diff = 0) | PASS |
| TC-04 | R4 | index.md mtime <= toutes les autres pages | PASS |
| TC-05 | R5 | Tous les wikilinks et liens markdown resolvent | PASS |
| TC-06 | R6 | Hash SHA256 des sources brutes inchange | PASS |
| TC-07 | R11 | Seuls sources/, concepts/, syntheses/, a-traiter/ touches | PASS |
| TC-08 | R12 | Compte-rendu avec question transversale non vide | PASS (*) |
| TC-09 | R14 | Chaque phrase de reponse cite un [[page]] | PASS |

(*) TC-08 : la regex `_REPORT_FIELD_RE` a necessite un ajustement —
`\s*` apres le deux-points traversait les sauts de ligne sur macOS.
Corrige en `[ ]*` (espaces seulement). Ajustement du test, pas du module.

### Test smoke (8 assertions)

| # | Assertion | Resultat |
|---|---|---|
| 1 | index.md contient l'entree source | PASS |
| 2 | Page source avec les 5 sections du template | PASS |
| 3 | Note personnelle presente et non vide | PASS |
| 4 | Au moins une page concepts/ creee | PASS |
| 5 | log.md contient l'entree ingest | PASS |
| 6 | git log montre le commit ingest: | PASS |
| 7 | Compte-rendu avec question transversale | PASS |
| 8 | Aucun fichier hors wiki/ dans git diff | PASS |

**Bilan** : 20/20 tests (12 contrat + 8 smoke). Aucun test modifie
pour s'adapter au code — un seul ajustement de regex dans le test
TC-08, qui etait un bug du test lui-meme (pas du module).

---

## 9. Patterns reutilisables pour la Phase 2

### Pattern : module synthesizer.py

Le futur `src/synthesizer.py` suivra le meme schema que les modules
existants :
- Input : objet structure (SourceFiche ou pages concept lues)
- Output : texte Markdown formate
- Zero effet de bord — l'ecriture est faite par l'appelant
- Le module ne lit jamais le wiki directement — tout passe en parametre

```
def synthesize_concept(concept_pages: list[str], fiche: SourceFiche) -> str:
    """Genere la section 'Definition synthetique' d'une page concept.
    Ne modifie rien — retourne le texte a inserer."""
```

### Pattern : validateur extensible

`validator.py` accepte deja des arguments optionnels pour les checks
comparatifs (snapshots avant/apres). Pour la Phase 2, ajouter un
check = ajouter une fonction `_check_rXX()` + un argument optionnel
dans `validate_post_ingestion()`. Aucune modification des checks existants.

### Pattern : contradiction comme signal, pas comme blocage

`contradiction_manager.py` enregistre les contradictions mais ne
bloque pas l'ingestion. C'est un signal pour l'humain. En Phase 2,
le LLM pourra detecter les tensions automatiquement et appeler
`record_contradiction()` — le module est pret.

### Pattern : mesure du temps de vibe coding

Hooks `UserPromptSubmit` + `Stop` dans `~/.claude/settings.json`.
Comptent le temps actif (intervalles < 10 min entre prompts consecutifs).
Resistant aux sessions laissees ouvertes pendant la nuit.

---

## 10. Differences structurelles avec YT Extractor

| Dimension | YT Extractor | Wiki LLM |
|---|---|---|
| **Etat** | Stateless — chaque execution independante | Stateful — chaque ingestion modifie un etat persistant |
| **Output** | Un fichier par execution | Plusieurs fichiers modifies par ingestion (index, source, concepts, log) |
| **Conflits** | Impossibles (fichier nouveau a chaque fois) | Centraux (doublon de source, concept existant, contradiction) |
| **Tests** | Tests unitaires classiques | Tests de contrat sur l'etat du wiki apres operation |
| **Validation** | Structure d'une fiche | Coherence d'un wiki entier (liens, perimetre, immutabilite) |
| **Constitution** | 8 regles | 15 regles (7 supplementaires pour l'integrite dans le temps) |
| **LLM** | Appele a chaque execution (generation) | Jamais appele par le code (pilotage humain uniquement) |
| **Git** | Non versionne | Commit automatique apres chaque ingestion |
| **Provider LLM** | Couche abstraite (Groq, Gemini, etc.) | Aucune couche LLM — le LLM est l'humain qui pilote |
| **Idempotence** | Oui (meme URL = meme fiche) | Non (meme fiche = mise a jour des pages existantes) |

**Lecon structurelle** : la gestion de l'etat est la difference
fondamentale. YT Extractor produit un fichier et oublie. Wiki LLM
modifie un systeme de fichiers interconnectes ou chaque ecriture
doit preserver la coherence de l'ensemble. C'est pour ca que la
constitution a 15 regles au lieu de 8, que les tests verifient
des invariants (octet par octet, hash SHA256), et que le validateur
accepte des snapshots avant/apres pour les checks comparatifs.

---

## Bilan chiffre

| Categorie | Total |
|---|---|
| Lignes Python | 3 533 (2 205 src/ + 920 tests/ + 408 orchestrateur) |
| Fonctions Python | 77 |
| Lignes de specs | 1 286 |
| Ratio specs/code | 1:2.7 |
| Tests | 20/20 (12 contrat + 8 smoke) |
| Pages wiki produites | 88 (19 sources + 69 concepts) |
| Entrees de log | 24 |
| Contradictions enregistrees | 0 (module pret, pas de tensions detectees au MVP) |

---

## 11. Temps de projet

| Phase | Duree | Outil |
|---|---|---|
| Co-construction des specs | ~6h30 | Claude.ai (sessions conversationnelles) |
| Vibe coding (implementation) | ~3h50 | Claude Code (Opus) |
| **Total** | **~10h20** | |

Le ratio specs/code en temps est **1.7:1** — plus de temps a definir
qu'a implementer. C'est le resultat attendu de la methode : les specs
eliminent les ambiguites, le code devient mecanique.

Le temps de vibe coding est estime depuis les timestamps git
(voir section 6 de `explication-methode.md` pour la methode de mesure).
Les prochaines sessions seront mesurees automatiquement par les hooks
`UserPromptSubmit` + `Stop`.

---

*Ce document est destine a etre attache au projet Claude.ai comme
reference de methode et capitalisation issue du MVP Wiki LLM.*
