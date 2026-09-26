# Rubik's Cube AR — Contrôle Gestuel

Application de réalité augmentée : un Rubik's Cube 3×3 flotte devant la
caméra et se manipule à la main (MediaPipe Hands) ou à la souris.

## Lancer le projet

```bash
pip install -r requirements.txt
python main.py
```

Le modèle MediaPipe (`hand_landmarker.task`) est téléchargé automatiquement
au premier lancement si l'ancienne API `mp.solutions.hands` n'est pas
disponible.

## Contrôles

**Main (caméra)** — fidèle à la démo de référence
| Geste                              | Action                                    |
|-------------------------------------|--------------------------------------------|
| Poing fermé + déplacer la main       | oriente/orbite la vue de la caméra          |
| Pincement (pouce + index) sur un sticker, puis glisser | attrape ce sticker et tourne sa face (comme un glisser-souris) |
| Pouce levé (maintenu ~1 s)          | mélange le cube                            |

Le pincement fonctionne exactement comme un clic-glisser de souris : on
« attrape » un sticker du bout des doigts, on tire dans une direction, et
la face tourne dans le sens correspondant en le relâchant — glisser vers
la droite/gauche/haut/bas déclenche des mouvements différents selon la
face et la rangée touchées (`cube/renderer.py::drag_to_move`).

**Souris** (identique, en secours si pas de caméra)
- Glisser sur un sticker → tourne la face
- Glisser dans le vide → orbite la caméra

**Clavier** (voir `utils/config.py`)
- `Q` / `Échap` : quitter
- `S` : mélanger · `R` : réinitialiser · `V` : résoudre automatiquement
- `+` / `-` : zoom
- Flèches ou `W A S D` / `X` : orbiter la vue manuellement
- `Entrée` : passer l'écran de calibration au démarrage

## Le Rubik's Cube — comment jouer

Le cube 3×3 a 6 faces de 9 stickers chacune. Le but est de retrouver
l'état où **chaque face n'affiche qu'une seule couleur**.

**Notation standard (WCA)**, utilisée dans tout le code et le HUD :
chaque lettre désigne une face vue depuis l'extérieur, et signifie
« tourner cette face d'un quart de tour dans le sens horaire » :

| Lettre | Face   | Lettre | Face    |
|--------|--------|--------|---------|
| `U` (Up)     | dessus | `D` (Down)   | dessous |
| `L` (Left)   | gauche | `R` (Right)  | droite  |
| `F` (Front)  | devant | `B` (Back)   | derrière|

- Un `'` après la lettre (ex. `U'`) = sens **anti-horaire**.
- Un `2` après la lettre (ex. `U2`) = **demi-tour** (180°).
- `M`, `E`, `S` désignent les tranches du **milieu** (respectivement
  parallèles à L/R, à U/D, à F/B) ; `x`, `y` (et leurs primes) font
  tourner le **cube entier** sans bouger les mains.

**Mélanger / résoudre dans l'appli** : `S` applique une suite de moves
aléatoires valides (`RubiksCube.shuffle`) ; `V` calcule une solution
(solveur optimal *kociemba* si installé, sinon recherche en largeur
bornée, sinon inversion pure et simple de l'historique des coups) puis
la rejoue automatiquement coup par coup.

**Pour apprendre à résoudre un vrai cube**, la méthode débutant classique
avance couche par couche : 1) croix blanche, 2) coins blancs (première
couche complète), 3) arêtes du milieu (deuxième couche), 4) croix jaune
puis coins jaunes orientés (dessus), 5) permutation finale des coins et
arêtes. Le CFOP (Cross–F2L–OLL–PLL), utilisé en compétition, accélère
cette même logique avec des algorithmes mémorisés pour les deux
dernières étapes.


## Correctifs apportés à ton code

### 1. `main.py` manquant
Le fichier n'était pas fourni : rien ne reliait caméra, tracking, gestes,
cube, rendu et HUD. Il a été écrit en entier avec :
- boucle principale (capture → tracking → gestes → rendu → HUD),
- interaction souris ET main (orbite / grab&turn),
- raccourcis clavier complets,
- auto-rotation douce quand la main est inactive,
- écran de **calibration** au démarrage (barre de progression + "SHOW YOUR
  OPEN HAND TO THE CAMERA"), fidèle à la vidéo de référence,
- lecture animée de la solution (un coup toutes les 0.35 s) quand on
  appuie sur `V`.

### 2. Bug mathématique dans le moteur du cube (`cube/rubiks_cube.py`)
En testant rigoureusement le modèle (identités de groupe, commutateurs
classiques `U F U' F'` et `R B R' B'`, 300 mélanges aléatoires suivis de
leur inversion), j'ai trouvé que **`F'`, `B'`, `S'` et la rotation globale
`x'` n'étaient pas les vraies inverses de `F`, `B`, `S`, `x`** — un
sticker sur deux se retrouvait mal orienté après une inversion. Concrètement,
avant le correctif : mélanger puis lancer "résoudre" ne redonnait **pas**
un cube résolu. Les 4 fonctions ont été corrigées et revalidées :
- tout move suivi de son inverse déclaré s'annule exactement,
- les commutateurs d'ordre 6 reviennent bien à l'identité,
- 300 scrambles aléatoires + inversion historique → 0 échec (contre
  ~169/300 avant correctif).

### 3. Interaction gestuelle réécrite pour coller à la vidéo de référence
Après analyse image par image de la vidéo, l'interaction réelle montrée
n'est pas un système de "couche sélectionnée + swipe" mais un système de
**pincement direct** (grab & turn) :
- `gestures/gesture_recognizer.py` réécrit : détecte en continu la
  distance pouce-index (normalisée par la taille de la main, avec
  hystérésis `PINCH_ON` / `PINCH_OFF` pour éviter le scintillement) pour
  déclencher un pincement, et le déplacement de la main en poing fermé
  pour l'orbite. Nouveaux états exposés : `PINCH_DETECTED`,
  `TRACKING_MOVEMENT`, `ORBITING`, `COOLDOWN`, `IDLE` (identiques aux
  libellés vus dans la vidéo).
- Le pincement réutilise **tel quel** le pipeline souris déjà présent
  dans `cube/renderer.py` (`press` / `hover` / `release`) : le point de
  pincement (milieu pouce-index) fait simplement office de curseur — le
  point de contact avec un sticker et le calcul du mouvement résultant
  (`drag_to_move`) sont exactement les mêmes que pour la souris.
- `ui/hud.py` mis à jour : légende de gestes simplifiée (FIST/PINCH/
  THUMB_UP), panneau des faces (FRONT/BACK/UP/DOWN/LEFT/RIGHT) qui
  surligne la face attrapée, message de statut central reprenant les
  libellés de la vidéo ("PINCH DETECTED — FRONT FACE",
  "TRACKING MOVEMENT — DRAG TO TURN A LAYER", "FIST — ORBIT VIEW").
- Nouvelles constantes dans `utils/config.py` : `PINCH_ON`, `PINCH_OFF`,
  `ORBIT_SENSITIVITY`.

### 4. Divers
- `from __future__ import annotations` ajouté à `rubiks_cube.py` et
  `solver.py` pour rester compatible Python 3.9 (les annotations
  `list[str] | None` y plantaient sinon à l'import).
- Nouvelle propriété `CubeRenderer.dragging` et `CubeRenderer.grabbed_face`
  (au lieu d'accéder aux attributs privés `_ds`/`_df` depuis l'extérieur).
- État `SOLVING` ajouté au HUD (bordure violette pulsante + couleur
  dédiée) pendant la lecture animée de la solution.
- `__init__.py` corrects pour les quatre packages (`cube`, `gestures`,
  `ui`, `utils`) — certains étaient corrompus dans l'archive fournie.
- `main.py` détecte maintenant lui-même un dossier manquant (`cube/`,
  `gestures/`, `ui/`, `utils/`) et affiche un message clair au lieu d'un
  `ModuleNotFoundError` cryptique — utile en cas d'extraction incomplète
  du zip sous Windows.
- Nettoyage BOM/CRLF sur l'ensemble des fichiers.

## Structure

```
rubiks-gesture/
├── main.py
├── requirements.txt
├── hand_landmarker.task     ← téléchargé automatiquement
├── cube/
│   ├── __init__.py
│   ├── rubiks_cube.py       (corrigé)
│   ├── renderer.py
│   └── solver.py            (corrigé : compat py3.9)
├── gestures/
│   ├── __init__.py
│   ├── hand_tracker.py
│   └── gesture_recognizer.py
├── ui/
│   ├── __init__.py
│   └── hud.py                (état SOLVING ajouté)
└── utils/
    ├── __init__.py
    └── config.py
```
