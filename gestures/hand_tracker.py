# gestures/hand_tracker.py
"""
Hand Tracking via MediaPipe.
Compatible API classique (0.10.x) et nouvelle API Tasks (1.x).
"""

import cv2
import numpy as np
import mediapipe as mp
import os
import urllib.request
from utils.config import (MAX_HANDS, DETECT_CONF, TRACK_CONF,
                           MODEL_PATH, MODEL_URL)


# Détection de la version d'API disponible
try:
    _ = mp.solutions.hands
    _USE_NEW_API = False
except AttributeError:
    _USE_NEW_API = True


def _ensure_model() -> str | None:
    """Télécharge le modèle si absent."""
    if os.path.exists(MODEL_PATH):
        return MODEL_PATH
    print(f"[Tracker] Téléchargement modèle → {MODEL_PATH}")
    try:
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("[Tracker] Modèle téléchargé ✓")
        return MODEL_PATH
    except Exception as e:
        print(f"[Tracker] Erreur téléchargement : {e}")
        return None


class HandTracker:
    """
    Détecte la main et extrait 21 landmarks.
    Publie :
      - hand_detected  : bool
      - landmarks      : list[(x,y,z)] normalisé [0,1]
      - finger_states  : list[int] × 5 (0=replié, 1=étendu)
      - hand_position  : (x, y) centre de la main
      - index_tip      : (x, y) bout de l'index
      - handedness     : "Left" | "Right" | None
    """

    # Indices landmarks
    TIPS  = [4,  8, 12, 16, 20]
    PIPS  = [3,  6, 10, 14, 18]
    MCPS  = [1,  5,  9, 13, 17]

    # Connexions pour dessin du squelette
    LINKS = [
        (0,1),(1,2),(2,3),(3,4),
        (0,5),(5,6),(6,7),(7,8),
        (0,9),(9,10),(10,11),(11,12),
        (0,13),(13,14),(14,15),(15,16),
        (0,17),(17,18),(18,19),(19,20),
        (5,9),(9,13),(13,17),(0,17),
    ]

    def __init__(self):
        self._reset_state()
        self._use_new = _USE_NEW_API

        if _USE_NEW_API:
            self._init_new_api()
        else:
            self._init_classic_api()

    def _reset_state(self):
        self.hand_detected  = False
        self.landmarks      = None
        self.finger_states  = None
        self.hand_position  = None
        self.index_tip      = None
        self.handedness     = None

    # ── Initialisation API ──────────────────────────────────────

    def _init_classic_api(self):
        self._mp_hands = mp.solutions.hands
        self._draw     = mp.solutions.drawing_utils
        self._style    = mp.solutions.drawing_styles
        self._hs       = self._mp_hands.Hands(
            static_image_mode        = False,
            max_num_hands            = MAX_HANDS,
            min_detection_confidence = DETECT_CONF,
            min_tracking_confidence  = TRACK_CONF,
        )
        print("[Tracker] API classique (mp.solutions.hands) ✓")

    def _init_new_api(self):
        path = _ensure_model()
        if not path:
            print("[Tracker] Fallback → tentative API classique")
            self._use_new = False
            try:
                self._init_classic_api()
            except Exception as e:
                print(f"[Tracker] ERREUR : {e}")
            return

        try:
            from mediapipe.tasks import python as mpt
            from mediapipe.tasks.python import vision as mpv

            opts = mpv.HandLandmarkerOptions(
                base_options=mpt.BaseOptions(
                    model_asset_path=path
                ),
                running_mode=mpv.RunningMode.IMAGE,
                num_hands=MAX_HANDS,
                min_hand_detection_confidence=DETECT_CONF,
                min_hand_presence_confidence =DETECT_CONF,
                min_tracking_confidence      =TRACK_CONF,
            )
            self._lm = mpv.HandLandmarker.create_from_options(opts)
            print("[Tracker] Nouvelle API Tasks (IMAGE mode) ✓")
        except Exception as e:
            print(f"[Tracker] Nouvelle API échouée ({e}), fallback classique")
            self._use_new = False
            self._init_classic_api()

    # ── Interface publique ──────────────────────────────────────

    def process(self, frame: np.ndarray) -> np.ndarray:
        """Traite un frame, dessine le squelette et met à jour l'état."""
        self._reset_state()
        if self._use_new:
            return self._proc_new(frame)
        return self._proc_classic(frame)

    def close(self):
        try:
            if self._use_new and hasattr(self, '_lm') and self._lm:
                self._lm.close()
            elif hasattr(self, '_hs') and self._hs:
                self._hs.close()
        except Exception:
            pass

    # ── Traitement API classique ────────────────────────────────

    def _proc_classic(self, frame: np.ndarray) -> np.ndarray:
        H, W = frame.shape[:2]
        rgb  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res  = self._hs.process(rgb)

        if not res.multi_hand_landmarks:
            return frame

        self.hand_detected = True
        raw = res.multi_hand_landmarks[0]

        # Extraire landmarks normalisés
        self.landmarks = [(l.x, l.y, l.z) for l in raw.landmark]

        # Handedness
        if res.multi_handedness:
            self.handedness = (
                res.multi_handedness[0].classification[0].label
            )

        # Dessiner squelette natif MediaPipe
        self._draw.draw_landmarks(
            frame, raw,
            self._mp_hands.HAND_CONNECTIONS,
            self._style.get_default_hand_landmarks_style(),
            self._style.get_default_hand_connections_style(),
        )

        self._compute(W, H)
        return frame

    # ── Traitement nouvelle API ─────────────────────────────────

    def _proc_new(self, frame: np.ndarray) -> np.ndarray:
        if not hasattr(self, '_lm') or not self._lm:
            return frame

        H, W = frame.shape[:2]

        # MediaPipe Tasks exige une image carrée pour éviter distorsion
        side   = max(W, H)
        square = np.zeros((side, side, 3), dtype=np.uint8)
        y_off  = (side - H) // 2
        x_off  = (side - W) // 2
        square[y_off:y_off+H, x_off:x_off+W] = frame

        rgb = cv2.cvtColor(square, cv2.COLOR_BGR2RGB)
        img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        try:
            res = self._lm.detect(img)
        except Exception as e:
            print(f"[Tracker] detect() erreur : {e}")
            return frame

        if not res.hand_landmarks:
            return frame

        self.hand_detected = True
        raw = res.hand_landmarks[0]

        # Corriger les landmarks : enlever l'offset du padding carré
        corrected = []
        for lm in raw:
            px = lm.x * side - x_off
            py = lm.y * side - y_off
            nx = float(np.clip(px / W, 0.0, 1.0))
            ny = float(np.clip(py / H, 0.0, 1.0))
            corrected.append((nx, ny, lm.z))

        self.landmarks = corrected

        # Handedness
        if res.handedness:
            self.handedness = res.handedness[0][0].display_name

        self._draw_skeleton(frame, corrected, W, H)
        self._compute(W, H)
        return frame

    # ── Dessin squelette ────────────────────────────────────────

    def _draw_skeleton(self, frame: np.ndarray,
                       lms: list, W: int, H: int):
        pts = [(int(x * W), int(y * H)) for x, y, z in lms]

        # Connexions
        for a, b in self.LINKS:
            if a < len(pts) and b < len(pts):
                cv2.line(frame, pts[a], pts[b],
                         (0, 210, 0), 2, cv2.LINE_AA)

        # Points
        for i, pt in enumerate(pts):
            is_tip = (i in self.TIPS)
            r      = 7 if is_tip else 4
            color  = (0, 255, 80) if is_tip else (220, 220, 220)
            cv2.circle(frame, pt, r, color, -1)
            cv2.circle(frame, pt, r, (0, 0, 0), 1)

    # ── Calculs dérivés ─────────────────────────────────────────

    def _compute(self, W: int, H: int):
        """Calcule finger_states, hand_position et index_tip."""
        if not self.landmarks or len(self.landmarks) < 21:
            return

        # Centre de la main (moyenne landmarks 0–8)
        n  = min(9, len(self.landmarks))
        xs = [self.landmarks[i][0] for i in range(n)]
        ys = [self.landmarks[i][1] for i in range(n)]
        self.hand_position = (float(np.mean(xs)), float(np.mean(ys)))

        # Bout de l'index
        t              = self.landmarks[8]
        self.index_tip = (t[0], t[1])

        # États des doigts
        self.finger_states = self._calc_finger_states()

    def _calc_finger_states(self) -> list[int]:
        """
        Retourne [pouce, index, majeur, annulaire, auriculaire]
        1 = étendu, 0 = replié
        """
        lm = self.landmarks
        states = []

        # Pouce : compare X (dépend du handedness)
        if self.handedness == "Right":
            states.append(1 if lm[4][0] < lm[3][0] else 0)
        else:
            states.append(1 if lm[4][0] > lm[3][0] else 0)

        # Autres doigts : compare Y (TIP vs PIP)
        for tip, pip in zip(self.TIPS[1:], self.PIPS[1:]):
            # TIP.y < PIP.y signifie doigt levé (y=0 en haut)
            states.append(1 if lm[tip][1] < lm[pip][1] else 0)

        return states