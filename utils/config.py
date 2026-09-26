# utils/config.py

# ─── Caméra ───────────────────────────────────────────
CAM_INDEX = 0
CAM_FPS   = 30

# ─── Sortie ───────────────────────────────────────────
OUTPUT_W = 1280
OUTPUT_H = 720

# ─── Fenêtre ──────────────────────────────────────────
WINDOW_NAME = "Rubik's Cube AR — Gesture Control"

# ─── Cube ─────────────────────────────────────────────
SHUFFLE_N       = 18
SHUFFLE_N_THUMB = 15

# ─── MediaPipe ────────────────────────────────────────
MAX_HANDS   = 1
DETECT_CONF = 0.70
TRACK_CONF  = 0.60
MODEL_PATH  = "hand_landmarker.task"
MODEL_URL   = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)

# ─── Gestes ───────────────────────────────────────────
SWIPE_THR       = 0.10
COOLDOWN_S      = 1.2
HIST_LEN        = 10
HOLD_FRAMES     = 6
STARTUP_DELAY_S = 4.0   # ← augmenté à 4s pour éviter faux gestes

# ─── Pincement (grab & turn — pouce + index) ──────────
PINCH_ON            = 0.32   # ratio dist(pouce,index)/taille-main sous lequel ça pince
PINCH_OFF           = 0.45   # ratio au-dessus duquel le pincement est relâché (hystérésis)

# ─── Orbite (poing fermé + déplacement de la main) ────
ORBIT_SENSITIVITY   = 3.2    # gain appliqué au déplacement normalisé de la main

# ─── Couleurs faces (BGR) ────────────────────────────
FACE_BGR = {
    'U': (  0,   0, 220),
    'D': (  0, 130, 255),
    'F': (245, 245, 245),
    'B': (  0, 215, 215),
    'L': (  0, 200,   0),
    'R': (210,   0,   0),
    '?': ( 40,  40,  40),
}

# ─── Auto-rotation ────────────────────────────────────
AUTO_ROTATE       = True
AUTO_ROTATE_SPEED = 0.25

# ─── Clavier ──────────────────────────────────────────
KEY_QUIT     = [ord('q'), 27]
KEY_SHUFFLE  = ord('s')
KEY_RESET    = ord('r')
KEY_SOLVE    = ord('v')
KEY_ZOOM_IN  = [ord('+'), ord('=')]
KEY_ZOOM_OUT = ord('-')
KEY_ROT_L    = [81, ord('a')]
KEY_ROT_R    = [83, ord('d')]
KEY_ROT_U    = [82, ord('w')]
KEY_ROT_D    = [84, ord('x')]