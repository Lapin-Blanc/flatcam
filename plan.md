# Plan de remise en état - FlatCAM (fork de modernisation)

> Ce document liste les chantiers issus de l'audit du 2026-05-31, classés par
> priorité. Chaque action explique d'abord **pourquoi** elle est nécessaire (en
> langage accessible), puis **comment** la réaliser et **comment vérifier** que
> c'est fait. Il sert de feuille de route : on coche au fur et à mesure.

## Contexte en deux mots

FlatCAM est un logiciel qui transforme des fichiers de CAO de circuit imprimé
(Gerber, Excellon) en parcours d'usinage (G-code) pour une fraiseuse CNC. Ce
dépôt est un fork qui a porté le vieux code (Python 2 / PyQt4) sur une stack
moderne (Python 3.12 / PySide6 / shapely 2.x). Le portage du code "métier" est
réussi, mais deux choses ont été laissées de côté : les **tests automatiques**
n'ont pas suivi la migration, et il n'existe **aucun garde-fou automatique**
(CI) qui vérifie que l'application fonctionne avant de publier une version. Du
coup, des régressions sont passées inaperçues.

Analogie : la voiture roule, mais le tableau de bord (les voyants d'alerte) a
été débranché pendant la révision. On va d'abord réparer la panne visible, puis
rebrancher les voyants pour ne plus rouler à l'aveugle.

## Légende des priorités

- **P0** - Bug réel qui casse une fonctionnalité aujourd'hui. A faire en premier.
- **P1** - Garde-fous (tests + CI) : sans eux, les bugs reviendront.
- **P2** - Hygiène du projet (dépendances, documentation) : faible effort, bon rapport.
- **P3** - Dette de fond (qualité, architecture) : travail de long terme, par petites touches.

---

## Phase 0 - Corriger la panne visible (P0)

### 0.1 - Réparer la commande `cutout`

**Pourquoi.** La commande de script `cutout` (qui découpe le contour d'une carte)
plante systématiquement. Elle utilise une fonction de la bibliothèque de calcul
géométrique (shapely) qui a été renommée dans la version 2.x : `cascaded_union`
est devenue `unary_union`. Tout le reste du code a été mis à jour, sauf ce
fichier. Resultat : dès qu'un utilisateur lance `cutout`, le programme lève une
erreur (`NameError`) et l'opération échoue. C'est une correction d'une ligne,
mais elle restaure une fonctionnalité aujourd'hui cassee.

**Comment.**
- Dans `tclCommands/TclCommandCutout.py`, ligne 93, remplacer `cascaded_union`
  par `unary_union`.
- Ajouter l'import explicite en haut du fichier : `from shapely.ops import unary_union`
  (ne pas compter sur un import "fourre-tout" implicite, c'est précisément ce qui
  a masqué le bug).

**Vérifier.**
- `python -c "import tclCommands.TclCommandCutout"` ne doit plus rien casser.
- Idéalement, écrire un petit test qui exécute la commande `cutout` sur un
  fichier d'exemple (voir Phase 1).

> Branche suggérée : `fix/cutout-shapely2-unary-union`.

### 0.2 - Réparer la fonction Paint (régression shapely 2.x)

**Pourquoi.** Découvert en remettant les tests en route (Phase 1) : la fonction
**Paint** (remplissage de zones cuivre) plantait à l'exécution. Le code de
`camlib.py` modifiait une géométrie en place via `ligne.coords = [...]`. Dans
shapely 1.x c'était permis ; dans shapely 2.x les géométries sont **immuables**
(plus de "setter" sur `coords`), d'où une erreur `AttributeError`. 13 tests
échouaient tous sur cette unique cause. C'est exactement le type de régression
silencieuse que l'absence de CI de test laissait passer.

**Comment.** Les 13 emplacements (`paint_connect`, `path_connect`, et la
génération G-code dans `generate_from_geometry_2`) ont été convertis du schéma
"muter en place" `geo.coords = ...` vers "reconstruire" `geo = LineString(...)`.

**Vérifier.** Les 13 tests Paint/PathConnect passent désormais (53/53 au total).

---

## Phase 1 - Rebrancher les voyants (P1)

> Statut : terminée. La suite passe à **53/53** en headless (~43 s), aucun blocage.
> Découverte majeure au passage : la régression Paint ci-dessus (0.2), corrigée.
> Détails de réalisation notés sous chaque action.

C'est le coeur du plan. Tant que cette phase n'est pas faite, chaque correction
risque d'en casser une autre sans qu'on s'en aperçoive.

### 1.1 - Migrer les tests de PyQt4 vers PySide6

**Pourquoi.** Plusieurs fichiers de test importent encore `PyQt4`, la vieille
bibliothèque graphique qui n'existe plus dans l'environnement moderne. Ces tests
ne se lancent même pas : ils s'arrêtent immédiatement sur une erreur d'import.
Autrement dit, une bonne partie du filet de sécurité est tombée par terre lors
de la migration et n'a jamais été ramassée.

**Comment.**
- Fichiers concernés : `tests/test_gerber_flow.py`, `tests/test_excellon_flow.py`,
  `tests/test_svg_flow.py`, `tests/test_tcl_shell.py`, `tests/test_polygon_paint.py`,
  `tests/other/destructor_test.py` (et le dossier `sandbox/` si on veut être complet).
- Remplacer `from PyQt4 import QtGui` par les imports PySide6 équivalents
  (`QApplication` est dans `PySide6.QtWidgets`, pas `QtGui` comme à l'époque de Qt4).
- Corriger aussi `cascaded_union` dans `tests/test_pathconnect.py`.

**Vérifier.** Chaque fichier doit au moins être collecté sans erreur d'import.

### 1.2 - Permettre l'exécution sans écran (mode "headless")

**Pourquoi.** Plusieurs tests créent une vraie fenêtre graphique et attendent
parfois 5 secondes avec un `sleep` codé en dur. Sur un serveur d'intégration
continue (CI), il n'y a pas d'écran : ces tests bloquent ou échouent. Il faut
leur dire de tourner "à blanc", sans affichage.

**Comment.**
- Forcer la variable d'environnement `QT_QPA_PLATFORM=offscreen` (le fichier
  `tests/smoke_secondary.py` le fait déjà correctement, on s'en inspire).
- Idéalement, centraliser ce réglage dans un `conftest.py` (pytest) ou un module
  d'amorçage commun, plutôt que de le répéter dans chaque test.
- Remplacer progressivement les `sleep(5)` par une attente sur un événement
  réel (les tests basés sur un temps fixe sont "flaky" : ils échouent au hasard).

**Vérifier.** `QT_QPA_PLATFORM=offscreen python -m unittest discover tests/`
s'exécute jusqu'au bout sur une machine sans écran.

> **Réalisé.** Centralisé dans `conftest.py` (racine) : `QT_QPA_PLATFORM=offscreen`,
> backend matplotlib `Agg`, et `sys.path`. La vraie cause des blocages n'était
> pas les `sleep` mais les **boîtes de dialogue modales** (`QMessageBox.exec()`)
> que rien ne ferme en headless : elles sont neutralisées (no-op) dans le
> conftest. Un garde-fou `--timeout=120` (pytest-timeout) garantit qu'un test
> bloqué échoue au lieu de figer la CI. Le `sleep(5)` de `test_polygon_paint`
> subsiste (raffinement non bloquant). Note : `FlatCAMApp` parse `sys.argv` dans
> le corps de la classe `App` ; neutralisé dans le conftest, vraie correction
> renvoyée en 3.3.

### 1.3 - Réparer ou retirer les tests `tclCommands` orphelins

**Pourquoi.** Le dossier `tests/test_tclCommands/` contient une quinzaine de
fichiers censés tester les commandes de script (mirror, scale, offset, panelize,
etc.). Mais ce sont de simples fonctions sans la structure attendue par le
lanceur de tests : elles ne sont jamais découvertes ni exécutées. C'est du test
"fantôme" : il donne une fausse impression de couverture.

**Comment.**
- Décider au cas par cas : soit on les rattache au framework (les transformer en
  vraies classes de test), soit on supprime ceux qui sont obsolètes.
- Au minimum, couvrir les commandes les plus utilisées, dont `cutout` (cf. 0.1).

**Vérifier.** Le nombre de tests réellement exécutés augmente ; plus aucun
fichier de test "mort" ne traîne.

> **Statut : différé `[~]`.** Ces fonctions étaient conçues pour être injectées
> comme méthodes de la classe `TclShellTest` (elles utilisent `self.fc`,
> `self.geometry_name`...). Les rattacher proprement (ordre, état partagé entre
> tests) est un sous-chantier à part entière, et elles n'ont jamais tourné sous
> le nouveau stack. En attendant, elles sont **exclues** de la collecte
> (`collect_ignore_glob` dans `conftest.py`) pour ne pas planter. Le flux TCL
> reste couvert par `test_tcl_shell.py` (mirror, isolate, exteriors, geocutout...)
> et par `tests/smoke_secondary.py`.

### 1.4 - Choisir et configurer le lanceur de tests

**Pourquoi.** Les tests sont écrits en `unittest` (la bibliothèque standard),
mais il n'y a aucune configuration centrale. Adopter `pytest` (qui sait aussi
lancer les tests `unittest`) donne une découverte automatique, de meilleurs
rapports d'erreur et un point d'entrée unique.

**Comment.**
- Ajouter une section `[tool.pytest.ini_options]` dans `pyproject.toml`
  (dossier de tests, options par défaut).
- Ajouter un groupe de dépendances de développement (`pytest`, `pytest-qt`
  éventuellement) - voir 2.1.

**Vérifier.** `pytest` lancé à la racine collecte et exécute toute la suite.

### 1.5 - Ajouter un workflow CI de test

**Pourquoi.** C'est le voyant principal. Aujourd'hui, le seul automatisme
(`.github/workflows/release.yml`) ne sert qu'à fabriquer les binaires lors d'une
publication : il ne lance aucun test. Résultat : on ne découvre les régressions
qu'une fois la version livrée. On veut au contraire que les tests tournent à
chaque modification proposée.

**Comment.**
- Créer `.github/workflows/test.yml` déclenché sur `push` et `pull_request`.
- Étapes : installer Python 3.12, installer le projet + dépendances de dev,
  lancer `pytest` en mode headless (`QT_QPA_PLATFORM=offscreen`, avec `xvfb` sur
  Linux si nécessaire).
- Ajouter une étape `pip-audit` qui signale les dépendances vulnérables (cf. 2.2).
- Optionnel mais recommandé : un linter (`ruff`) pour l'hygiène de base.

**Vérifier.** Une pull request de test affiche bien le statut vert/rouge des
tests avant fusion.

---

## Phase 2 - Hygiène du projet (P2)

### 2.1 - Épingler les dépendances et déclarer les dépendances de dev

**Pourquoi.** Les versions minimales déclarées sont irréalistes (`numpy>=1.8`,
`matplotlib>=1.3.1` datent de 2013) et il n'y a aucune borne supérieure. Concrètement,
rien n'empêche une future mise à jour de bibliothèque de casser l'application du
jour au lendemain, exactement comme l'a fait shapely 2.x avec `cascaded_union`.
On veut figer des fourchettes de versions testées et connues pour fonctionner.

**Comment.**
- Mettre à jour les bornes dans `pyproject.toml` et `requirements.txt` sur des
  versions modernes cohérentes (ex. `numpy>=2,<3`, `shapely>=2,<3`).
- Ajouter un groupe `[project.optional-dependencies]` `dev` avec `pytest`, `ruff`,
  `pip-audit`.

**Vérifier.** Une installation propre dans un venv neuf fonctionne et lance les tests.

### 2.2 - Vérification automatique des vulnérabilités

**Pourquoi.** Le logiciel ouvre des fichiers fournis par des tiers (Gerber, SVG,
projets). Une faille dans une dépendance pourrait être exploitée via un fichier
piégé. `pip-audit` compare les versions installées à une base de vulnérabilités
connues et alerte automatiquement.

**Comment.** Ajouter `pip-audit` dans la CI (Phase 1.5) ; traiter les alertes.

### 2.3 - Corriger la documentation

**Pourquoi.** Le `README.md` annonce que le fork tourne sous **PyQt5**, alors que
tout le code utilise en réalité **PySide6**. Un contributeur qui se fie au README
installerait la mauvaise bibliothèque. Petite incohérence, mais elle induit en
erreur dès la première lecture.

**Comment.** Remplacer "PyQt5" par "PySide6" dans `README.md` (ligne 12).

**Vérifier.** Le README décrit la stack réellement utilisée.

---

## Phase 3 - Dette de fond (P3, long terme, par petites touches)

> Ces chantiers améliorent la robustesse et la maintenabilité mais ne sont pas
> urgents. A traiter opportunistement, idéalement une fois le filet de tests en
> place (sinon, risque de casser sans s'en rendre compte).

### 3.1 - Remplacer les `eval()` par du parsing sûr

**Pourquoi.** Plusieurs champs de saisie et le parseur de macros Gerber utilisent
`eval()`, qui exécute le texte saisi comme du code Python. Pour un logiciel de
bureau local, le risque de sécurité est limité (l'utilisateur exécute sur sa
propre machine), mais c'est fragile : une saisie malformée fait planter
l'application au lieu d'afficher un message d'erreur propre.

**Où.** `GUIElements.py` (lignes 108, 151, 253), `ToolDblSided.py:137`,
`camlib.py` (lignes 1120, 1142).

**Comment.** Utiliser `ast.literal_eval` pour les valeurs simples, ou un petit
évaluateur d'expressions mathématiques dédié pour les champs de dimension.

### 3.2 - Traiter les `except:` nus

**Pourquoi.** Une vingtaine d'endroits attrapent toutes les erreurs sans les
nommer ni les journaliser (`except:` suivi de `pass`). Ça masque les vrais bugs :
quand quelque chose tourne mal, l'application continue en silence dans un état
incohérent, et on ne sait pas pourquoi.

**Où.** Principalement `camlib.py` et `FlatCAMApp.py`.

**Comment.** Remplacer par des exceptions précises (`except ValueError:`...) et,
a minima, journaliser l'erreur avant de la traiter.

### 3.3 - Décomposer le "god object" `App` (chantier de fond)

**Pourquoi.** La classe `App` (`FlatCAMApp.py`) concentre près de 2800 lignes et
fait tout : interface, fichiers, logique métier, threads, shell de script. C'est
difficile à comprendre, à tester et à modifier sans effet de bord. De plus, elle
forme des dépendances circulaires avec les autres modules (chacun importe l'autre).

**Comment.** Travail incrémental et prudent : extraire des responsabilités une à
une (gestion des fichiers, gestion de la configuration, shell...) vers des modules
dédiés, en s'appuyant sur les tests pour ne rien casser. A n'entreprendre
qu'après la Phase 1.

### 3.4 - Découper les méthodes géantes et remplacer les imports `*`

**Pourquoi.** `Gerber.parse_lines()` fait ~570 lignes : illisible et impossible à
tester par morceaux. Les imports "fourre-tout" (`from camlib import *`) masquent
d'où viennent les fonctions - c'est ce qui a permis au bug `cutout` de passer
inaperçu. Remplacer ces imports par des imports explicites rendrait ce type
d'erreur visible immédiatement (l'éditeur signalerait le nom non défini).

**Comment.** Extraire des sous-fonctions nommées ; remplacer les `import *` par
des imports explicites, module par module.

---

## Suivi

| Phase | Action | Priorité | Statut |
|-------|--------|----------|--------|
| 0.1 | Réparer `cutout` (`unary_union` + `LineString`) | P0 | [x] |
| 0.2 | Réparer Paint (`LineString` immuable, shapely 2.x) | P0 | [x] |
| 1.1 | Migrer tests PyQt4 -> PySide6 | P1 | [x] |
| 1.2 | Mode headless + neutralisation dialogues modaux | P1 | [x] |
| 1.3 | Réparer/retirer tests `tclCommands` orphelins | P1 | [~] |
| 1.4 | Configurer pytest | P1 | [x] |
| 1.5 | Workflow CI de test | P1 | [x] |
| 2.1 | Épingler dépendances + groupe dev | P2 | [x] |
| 2.2 | `pip-audit` en CI (bloquant) | P2 | [x] |
| 2.3 | Corriger README (PySide6) | P2 | [x] |
| 3.1 | Supprimer les `eval()` | P3 | [ ] |
| 3.2 | Traiter les `except:` nus | P3 | [ ] |
| 3.3 | Décomposer `App` | P3 | [ ] |
| 3.4 | Méthodes géantes + imports explicites | P3 | [ ] |
