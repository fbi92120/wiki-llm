# STATS — wiki-llm

*Mesures générées le 2026-07-26. Commandes à exécuter depuis la racine du dépôt.*

## wiki-llm

- **Date du premier commit** : 2026-04-09
  `git log --reverse --format='%ad' --date=short | head -1`
- **Date du dernier commit** : 2026-04-11
  `git log -1 --format='%ad' --date=short`
- **Nombre total de commits** : 33 (58 avant la réécriture d'historique du 2026-07-27 — voir note ci-dessous)
  `git rev-list --count HEAD`
- **Nombre de jours calendaires distincts avec au moins un commit** : 3
  `git log --format='%ad' --date=short | sort -u | wc -l`
- **Durée calendaire entre premier et dernier commit** : 2 jours
  `git log --format='%at' | sort -n | awk 'NR==1{f=$1} END{printf "%d jours\n", ($1-f)/86400}'`
- **Plus longue interruption entre deux commits** : 0,67 jour
  `git log --format='%at' | sort -n | awk 'NR>1{g=$1-p; if(g>m)m=g} {p=$1} END{printf "%.2f jours\n", m/86400}'`
> **Note — métriques git.** Les valeurs ci-dessus (commits, dates, jours actifs) ont été mesurées le 2026-07-26, **avant** la réécriture d'historique du 2026-07-27 (publication : purge du vault `wiki/`+`wiki-test/` et du chemin personnel via `git filter-repo`). Depuis, `git rev-list --count HEAD` renvoie **33** et la plage de dates s'étend au 2026-07-27 (commits de maintenance/publication). La fenêtre de livraison du MVP reste **2026-04-09 → 2026-04-11 (3 jours)**.

- **Nombre de fichiers de code, et lignes de code par langage** (hors `.venv`, `.git`, `__pycache__`) :
  - `.py` : 13 fichiers, 4172 lignes
  - `.sh` : 1 fichier, 16 lignes
  - `.yml` : 1 fichier, 5 lignes

  `find . -name '*.py' -not -path './.venv/*' -not -path './__pycache__/*' | wc -l`
  `find . -name '*.py' -not -path './.venv/*' -not -path './__pycache__/*' -print0 | xargs -0 cat | wc -l`
- **Nombre de fichiers markdown de documentation, et lignes totales** : 14 fichiers, 2738 lignes (documentation rédigée).
  Correction d'une mesure initiale trop inclusive (« 15 fichiers, 4458 lignes ») : elle comptait 2 articles source tiers (Karpathy) présents à la racine (`2026-04-15-…karpathy….md`, ~1835 lignes), qui ne sont pas de la documentation du projet. Exclus ici (via `-not -name '2026-*'`), en plus du vault généré (`wiki/`, `wiki-test/`).
  Pour mémoire : total tous `.md` confondus (documentation + vault généré + articles tiers) = 136 fichiers, 11736 lignes.
  Documentation rédigée : `find . -name '*.md' -not -path './.git/*' -not -path './.venv/*' -not -path './wiki/*' -not -path './wiki-test/*' -not -path './.pytest_cache/*' -not -name '2026-*' | wc -l`
  Lignes : `find . -name '*.md' -not -path './.git/*' -not -path './.venv/*' -not -path './wiki/*' -not -path './wiki-test/*' -not -path './.pytest_cache/*' -not -name '2026-*' -print0 | xargs -0 cat | wc -l`
- **Nombre de tests, et commande utilisée pour les compter** : 25 fonctions `def test_` dans 2 fichiers `test_*.py`
  `grep -rE '^\s*def test_' --include='*.py' --exclude-dir=.venv . | wc -l`
  Écart de comptage à signaler : `WIKI_LLM_RETOUR_EXPERIENCE.md` documente « 20/20 (12 contrat + 8 smoke) », qui compte des cas de test logiques, pas les fonctions `def test_` — les deux mesures ne portent pas sur le même objet.
- **Part du code réservée aux tests** : 26,6 % (1111 lignes de test sur 4172 lignes `.py` au total ; 3 fichiers)
  Lignes de test : `find . -name '*.py' \( -name 'test_*.py' -o -path '*/tests/*' \) -not -path './.venv/*' -not -path './__pycache__/*' -print0 | xargs -0 cat | wc -l`
  Total `.py` : `find . -name '*.py' -not -path './.venv/*' -not -path './__pycache__/*' -print0 | xargs -0 cat | wc -l`
- **Taille moyenne d'une fonction Python (hors test)** : 31,4 lignes (médiane 20 ; min 3, max 179) sur 62 fonctions dans 10 fichiers.
  Mesuré par script AST : `ast.FunctionDef` + `end_lineno - lineno + 1`, sur les `.py` hors `tests/` et `test_*.py`.
- **Le code est-il commenté / documenté ?** : oui — le mieux documenté des dépôts mesurés.
  - Docstrings : fonctions 59/62 (95 %), classes 1/1 (100 %), modules 9/10 (90 %).
  - Commentaires inline : 173 pour 2330 lignes de code (ratio 0,07).
- **Version courante déclarée, si elle figure quelque part** :
  - `SPECS.md` : Version 1.0 — `grep -m1 -i version SPECS.md`
  - `backlog.wiki-llm.md` : Version 1.0

---

## Publiabilité

Vérification de l'état courant **et** de l'historique git.

- **Secrets / clés d'API** : aucun. `.env` présent dans `.gitignore`, jamais commité dans l'historique, absent du disque. Aucun motif de clé (`sk-…`, `AIza…`, `gsk_…`, `ghp_…`) trouvé ni dans l'arbre courant ni dans aucun commit (`git rev-list --all` + `git grep`).
- **Chemins personnels** : une occurrence dans `DIAGNOSTIC_2026-04-11.md` → **corrigé le 2026-07-27** : chemin remplacé par un placeholder dans le fichier, et `/Users/fbi` scrubé de tout l'historique (`git filter-repo`).
- **Noms de clients / employeurs** : aucun détecté. La seule mention « nom de client » est une règle de `CLAUDE.md` qui en interdit la présence.
- **Contenu sous licence tierce / données personnelles** : le vault produit par l'outil était commité (125 fichiers dérivés de vidéos tierces + notes personnelles) → **corrigé le 2026-07-27** : `wiki/`+`wiki-test/` untrackés (`git rm --cached`, fichiers conservés en local), ajoutés au `.gitignore`, et purgés de tout l'historique. Absence vérifiée sur un clone frais du remote.

**Conclusion (mise à jour 2026-07-27) : publié — corrections effectuées.** Dépôt public (https://github.com/fbi92120/wiki-llm), historique nettoyé (0 fichier vault, 0 chemin personnel, vérifié par clone frais). Reste un point d'hygiène : **LICENSE absent** (à ajouter).

---

## Autres mesures (critères de livraison)

- **Modules source** (.py hors test) : 10
- **Dépendances runtime** : aucune hors bibliothèque standard Python (pas de `requirements.txt` ; confirmé par le README)
- **Ratio documentation / code** : 1,07 : 1 (4458 lignes `.md` de documentation hors vault généré, pour 4172 lignes `.py`)
- **Annotations de type** : présentes (74 occurrences `->` / `from __future__ import annotations`)
- **Packaging installable** : absent
- **Intégration continue** : absente
- **Outillage lint / format / typecheck** : absent
- **LICENSE** : absent

