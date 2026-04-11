# Wiki LLM

Un modèle pour construire des bases de connaissances personnelles avec des LLMs.

Ce fichier est une idée à copier-coller dans votre propre agent LLM (par exemple OpenAI Codex, Claude Code, OpenCode / Pi, etc.). Son but est de transmettre l’idée générale, mais c’est votre agent qui en construira les détails en collaboration avec vous.

## L’idée centrale

La plupart des gens utilisent les LLMs avec des documents selon le schéma du RAG : on téléverse un ensemble de fichiers, le LLM récupère les passages pertinents au moment de la requête, puis génère une réponse. Cela fonctionne, mais le LLM redécouvre le savoir depuis zéro à chaque question. Il n’y a aucune accumulation. Si vous posez une question subtile qui demande de synthétiser cinq documents, le LLM doit retrouver puis assembler les bons fragments à chaque fois. Rien ne se construit dans la durée. NotebookLM, les téléversements de fichiers dans ChatGPT, et la plupart des systèmes RAG fonctionnent ainsi.

L’idée ici est différente. Au lieu de se contenter de récupérer des informations depuis des documents bruts au moment de la requête, le LLM construit et maintient progressivement un wiki persistant — une collection structurée de fichiers markdown reliés entre eux, située entre vous et les sources brutes. Quand vous ajoutez une nouvelle source, le LLM ne se contente pas de l’indexer pour plus tard. Il la lit, en extrait les informations clés, et l’intègre au wiki existant — en mettant à jour les pages d’entités, en révisant les résumés de sujets, en notant les contradictions entre nouvelles et anciennes informations, en renforçant ou en remettant en question la synthèse en cours. Le savoir est compilé une fois, puis maintenu à jour, au lieu d’être reconstruit à chaque question.

C’est la différence essentielle : le wiki est un artefact persistant qui s’enrichit par accumulation. Les renvois entre pages sont déjà en place. Les contradictions ont déjà été signalées. La synthèse reflète déjà tout ce que vous avez lu. Le wiki devient plus riche à chaque nouvelle source et à chaque question posée.

Vous n’écrivez presque jamais le wiki vous-même — le LLM le rédige et l’entretient. Votre rôle consiste à fournir les sources, explorer, et poser les bonnes questions. Le LLM fait le travail ingrat — résumé, liens croisés, classement, maintenance — qui rend une base de connaissances réellement utile dans le temps. En pratique, Karpathy dit avoir l’agent LLM ouvert d’un côté et Obsidian de l’autre. Le LLM fait les modifications à partir de la conversation, et il consulte les résultats en temps réel — en suivant les liens, en regardant la vue graphe, en lisant les pages mises à jour. Obsidian est l’IDE ; le LLM est le programmeur ; le wiki est le codebase.

Cette approche peut servir dans de nombreux contextes :

- **Personnel** : suivre ses objectifs, sa santé, sa psychologie, son développement personnel — classer journaux, articles, notes de podcasts, et construire peu à peu une vision structurée de soi-même.
- **Recherche** : approfondir un sujet pendant des semaines ou des mois — lire des articles, papiers, rapports, et bâtir progressivement un wiki complet avec une thèse évolutive.
- **Lecture d’un livre** : classer chaque chapitre au fil de l’eau, créer des pages pour les personnages, thèmes, intrigues et leurs liens. À la fin, on obtient un wiki-compagnon riche.
- **Entreprise/équipe** : un wiki interne maintenu par des LLMs, alimenté par les discussions Slack, les comptes rendus de réunion, les documents de projet, les appels clients. Avec éventuellement des humains pour valider les mises à jour.
- **Analyse concurrentielle, due diligence, préparation de voyage, notes de cours, passions approfondies** — tout ce qui consiste à accumuler des connaissances dans le temps et à vouloir les organiser plutôt que les disperser.

## Architecture

Il y a trois couches :

**Sources brutes** — votre collection de documents sources sélectionnés. Articles, papiers, images, fichiers de données. Elles sont immuables : le LLM les lit mais ne les modifie jamais. C’est la source de vérité.

**Le wiki** — un dossier de fichiers markdown générés par le LLM. Résumés, pages d’entités, pages de concepts, comparaisons, vue d’ensemble, synthèse. Le LLM possède entièrement cette couche. Il crée des pages, les met à jour quand de nouvelles sources arrivent, maintient les liens croisés, et garde l’ensemble cohérent. Vous le lisez ; le LLM l’écrit.

**Le schéma** — un document (par exemple CLAUDE.md pour Claude Code ou AGENTS.md pour Codex) qui explique au LLM comment le wiki est structuré, quelles conventions utiliser, et quels workflows suivre pour ingérer des sources, répondre aux questions, ou entretenir le wiki. C’est le fichier de configuration clé : il transforme le LLM en mainteneur discipliné de wiki plutôt qu’en simple chatbot. Vous et le LLM l’améliorez au fil du temps selon ce qui fonctionne le mieux dans votre domaine.

## Fonctionnement

**Ingestion.** Vous ajoutez une nouvelle source dans la collection brute et vous demandez au LLM de la traiter. Exemple de flux : le LLM lit la source, discute avec vous des points essentiels, écrit une page de résumé dans le wiki, met à jour l’index, met à jour les pages d’entités et de concepts concernées, puis ajoute une entrée dans le journal. Une seule source peut toucher 10 à 15 pages. Karpathy dit préférer ingérer les sources une par une en restant impliqué : il lit les résumés, vérifie les mises à jour, et guide le LLM sur ce qu’il faut mettre en avant. Mais on peut aussi ingérer en lot avec moins de supervision. C’est à vous de définir le workflow qui vous convient et de le documenter dans le schéma pour les sessions futures.

**Requête.** Vous posez des questions au wiki. Le LLM cherche les pages pertinentes, les lit, puis synthétise une réponse avec citations. Les réponses peuvent prendre différentes formes selon la question : une page markdown, un tableau comparatif, un diaporama Marp, un graphique matplotlib, une canvas. L’idée importante : les bonnes réponses peuvent elles aussi être enregistrées dans le wiki comme de nouvelles pages. Une comparaison demandée, une analyse, un lien découvert — tout cela a de la valeur et ne devrait pas disparaître dans l’historique du chat. Ainsi, vos explorations s’accumulent dans la base de connaissances, tout comme les sources ingérées.

**Contrôle qualité.** Périodiquement, demandez au LLM d’évaluer la santé du wiki. Cherchez : les contradictions entre pages, les affirmations devenues obsolètes parce que de nouvelles sources les ont remplacées, les pages orphelines sans liens entrants, les concepts importants mentionnés mais sans page dédiée, les renvois manquants, les lacunes de données qu’une recherche web pourrait combler. Le LLM est bon pour suggérer de nouvelles questions à explorer et de nouvelles sources à rechercher. Cela maintient le wiki en bon état à mesure qu’il grandit.

## Indexation et journalisation

Deux fichiers spéciaux aident le LLM et vous à naviguer dans le wiki à mesure qu’il s’étoffe. Ils ont des rôles différents :

**index.md** est orienté contenu. C’est un catalogue de tout le wiki — chaque page y figure avec un lien, un résumé en une ligne, et éventuellement des métadonnées comme la date ou le nombre de sources. Il est organisé par catégorie (entités, concepts, sources, etc.). Le LLM le met à jour à chaque ingestion. Lorsqu’il répond à une requête, il lit d’abord l’index pour trouver les pages pertinentes, puis approfondit. Cela fonctionne étonnamment bien à échelle modérée (~100 sources, ~des centaines de pages) et évite une infrastructure de RAG par embeddings.

**log.md** est chronologique. C’est un journal append-only de ce qui s’est passé et quand — ingestions, requêtes, contrôles qualité. Astuce utile : si chaque entrée commence par un préfixe constant (par exemple `## [2026-04-02] ingest | Article Title`), le journal devient facilement exploitable avec des outils Unix simples. Le journal donne une chronologie de l’évolution du wiki et aide le LLM à comprendre ce qui a été fait récemment.

## Outils CLI optionnels

À un moment, vous voudrez peut-être créer de petits outils pour aider le LLM à exploiter le wiki plus efficacement. Un moteur de recherche sur les pages du wiki est l’option la plus évidente : à petite échelle, le fichier index suffit, mais quand le wiki grandit, il faut une vraie recherche. qmd est une bonne option : c’est un moteur de recherche local pour fichiers markdown, avec recherche hybride BM25/vectorielle et re-classement par LLM, le tout en local. Il dispose d’une CLI et d’un serveur MCP, ce qui permet au LLM de l’utiliser comme outil natif. Vous pouvez aussi faire quelque chose de plus simple vous-même — le LLM peut vous aider à coder rapidement un script de recherche naïf quand le besoin apparaît.

## Astuces

- **Obsidian Web Clipper** est une extension navigateur qui convertit des articles web en markdown. Très utile pour intégrer rapidement des sources dans votre collection brute.
- **Téléchargez les images localement.** Dans Obsidian, dans Settings → Files and links, définissez le dossier des pièces jointes vers un répertoire fixe, par exemple `raw/assets/`. Puis dans Settings → Hotkeys, cherchez “Download” pour trouver “Download attachments for current file” et associez-lui un raccourci, par exemple Ctrl+Shift+D. Après avoir capturé un article, lancez le raccourci et toutes les images seront téléchargées sur le disque local. C’est optionnel mais utile : cela permet au LLM de voir et citer les images directement plutôt que de dépendre d’URL susceptibles de casser.
- **La vue graphe d’Obsidian** est la meilleure manière de voir la structure du wiki — ce qui est relié à quoi, quelles pages sont des hubs, quelles pages sont orphelines.
- **Marp** est un format de diaporama basé sur markdown. Obsidian a un plugin pour cela. C’est pratique pour générer des présentations directement à partir du contenu du wiki.
- **Dataview** est un plugin Obsidian qui exécute des requêtes sur les métadonnées YAML des pages. Si le LLM ajoute du frontmatter YAML aux pages du wiki (tags, dates, nombre de sources), Dataview peut générer des tableaux et listes dynamiques.
- Le wiki n’est qu’un dépôt git de fichiers markdown. Vous obtenez gratuitement l’historique de versions, les branches et la collaboration.

## Pourquoi ça marche

La partie fastidieuse de l’entretien d’une base de connaissances n’est pas la lecture ni la réflexion, mais la gestion pratique : mise à jour des liens croisés, maintien des résumés, signalement des nouvelles informations qui contredisent les anciennes, cohérence entre des dizaines de pages. Les humains abandonnent les wikis parce que le coût de maintenance croît plus vite que la valeur. Les LLMs ne s’ennuient pas, n’oublient pas de mettre à jour un lien croisé, et peuvent toucher 15 fichiers en une seule passe. Le wiki reste maintenu parce que le coût de maintenance devient presque nul.

Le rôle de l’humain est de sélectionner les sources, orienter l’analyse, poser de bonnes questions et réfléchir à ce que tout cela signifie. Le rôle du LLM est tout le reste.

L’idée est proche, dans l’esprit, du Memex de Vannevar Bush (1945) — un espace de connaissance personnel et curé, avec des chemins associatifs entre documents. La vision de Bush se rapproche davantage de cela que du web tel qu’il est devenu : privé, activement maintenu, où les liens entre documents comptent autant que les documents eux-mêmes. La partie qu’il n’avait pas résolue était : qui fait la maintenance ? Le LLM s’en charge.

## Note

Ce document est volontairement abstrait. Il décrit l’idée, pas une implémentation spécifique. La structure exacte des dossiers, les conventions du schéma, les formats de pages, les outils — tout cela dépendra de votre domaine, de vos préférences et du LLM choisi. Tout ce qui est mentionné ci-dessus est optionnel et modulaire : prenez ce qui vous est utile, ignorez le reste. Par exemple, vos sources peuvent être uniquement textuelles, donc vous n’avez peut-être pas besoin de gestion d’images. Votre wiki peut être assez petit pour que le fichier index suffise, sans moteur de recherche. Vous pouvez ne pas vouloir de diaporamas et préférer seulement des pages markdown. Vous pouvez vouloir un autre format de sortie. La bonne manière d’utiliser cela est de le partager avec votre agent LLM et de co-construire une version adaptée à vos besoins. Le seul rôle du document est de communiquer le schéma général. Votre LLM peut s’occuper du reste.
