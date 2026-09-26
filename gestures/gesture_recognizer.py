# gestures/gesture_recognizer.py
"""
Reconnaissance de gestes — pilote l'interaction "mains nues", fidèle à la
démo de référence :

  POING FERMÉ (FIST)        + déplacement de la main → orbite la caméra
  PINCEMENT (pouce + index) + glisser                 → attrape un sticker
                                                          et tourne sa face
  POUCE LEVÉ (THUMB_UP)                                → mélange le cube

Le pincement réutilise tel quel le pipeline "souris" de CubeRenderer
(press / hover / release) : le point de pincement (milieu pouce-index)
fait simplement office de curseur. C'est main.py qui fait le lien entre
les événements ci-dessous et le renderer.
"""
from __future__ import annotations

import math
import time
from collections import deque

from utils.config import (COOLDOWN_S, HOLD_FRAMES, STARTUP_DELAY_S,
                           PINCH_ON, PINCH_OFF)


class GestureRecognizer:

    # Association forme-de-main → étiquette (utilisée pour l'affichage
    # HUD et pour détecter POUCE LEVÉ ; le pincement, lui, ne dépend pas
    # de cette table : il est mesuré en continu via les landmarks).
    MAP = {
        (0,0,0,0,0):"FIST",
        (0,1,0,0,0):"POINT",
        (0,1,1,0,0):"PEACE",
        (0,1,1,1,0):"THREE",
        (1,1,1,1,1):"OPEN",
        (1,0,0,0,0):"THUMB_UP",
    }

    FRIENDLY_FACE = {
        'U':"UP", 'D':"DOWN", 'F':"FRONT",
        'B':"BACK", 'L':"LEFT", 'R':"RIGHT",
    }

    def __init__(self):
        self._reset()

    def _reset(self):
        # Affichage HUD
        self.current_gesture  = "NONE"
        self.current_movement = "NONE"
        self.selected_layer   = "-"     # face actuellement attrapée
        self.rotation_dir     = "-"
        self.state            = "IDLE"

        self._gbuf   = deque(maxlen=HOLD_FRAMES)
        self._stable = "NONE"

        # Pincement (grab & turn)
        self.pinching           = False
        self.pinch_just_started = False
        self.pinch_just_ended   = False
        self.pinch_point        = None   # (x,y) normalisé [0,1], pendant le pincement
        self._last_pinch_point  = None   # dernier point connu (pour le relâcher)

        # Orbite (poing fermé)
        self._orbit_prev = None
        self.orbit_delta = None          # (dx,dy) normalisé, ou None

        self._last_shuffle_t = 0.0
        self._ready = time.time() + STARTUP_DELAY_S

    def reset(self):
        self._reset()

    # ══════════════════════════════════════════════════
    #  MISE À JOUR PAR FRAME
    # ══════════════════════════════════════════════════

    def update(self, finger_states, hand_position, landmarks=None):
        raw = (self.MAP.get(tuple(finger_states), "UNKNOWN")
               if finger_states else "NONE")
        self._gbuf.append(raw)
        if (len(self._gbuf) == HOLD_FRAMES
                and len(set(self._gbuf)) == 1
                and raw not in ("NONE", "UNKNOWN")):
            self._stable = raw
        else:
            self._stable = "NONE"

        self._update_pinch(landmarks)
        self._update_orbit(raw, hand_position)
        self._update_display_fields(raw)
        self._update_state()

    # ── Pincement pouce-index ───────────────────────────

    def _update_pinch(self, landmarks):
        was_pinching = self.pinching
        self.pinch_just_started = False
        self.pinch_just_ended   = False

        if landmarks and len(landmarks) >= 21:
            th, ix     = landmarks[4], landmarks[8]
            wrist, mcp = landmarks[0], landmarks[9]
            # Distance pouce-index normalisée par la taille de la main,
            # pour rester indépendant de la distance à la caméra.
            span = math.hypot(mcp[0]-wrist[0], mcp[1]-wrist[1]) or 1e-6
            dist = math.hypot(th[0]-ix[0], th[1]-ix[1]) / span

            if not was_pinching and dist < PINCH_ON:
                self.pinching = True
            elif was_pinching and dist > PINCH_OFF:
                self.pinching = False

            if self.pinching:
                pt = ((th[0]+ix[0])/2, (th[1]+ix[1])/2)
                self.pinch_point       = pt
                self._last_pinch_point = pt
        else:
            self.pinching = False

        if self.pinching and not was_pinching:
            self.pinch_just_started = True
        elif was_pinching and not self.pinching:
            self.pinch_just_ended = True
            self.pinch_point = None  # le point figé reste dans _last_pinch_point

    # ── Orbite (poing fermé + déplacement) ──────────────

    def _update_orbit(self, raw, hand_position):
        self.orbit_delta = None
        is_fist = (raw == "FIST" or self._stable == "FIST")

        if is_fist and not self.pinching and hand_position:
            if self._orbit_prev is not None:
                dx = hand_position[0] - self._orbit_prev[0]
                dy = hand_position[1] - self._orbit_prev[1]
                if abs(dx) > 0.0008 or abs(dy) > 0.0008:
                    self.orbit_delta = (dx, dy)
            self._orbit_prev = hand_position
        else:
            self._orbit_prev = hand_position if (is_fist and hand_position) else None

    # ── Champs d'affichage HUD ──────────────────────────

    def _update_display_fields(self, raw):
        self.current_gesture = "PINCH" if self.pinching else raw
        if self.pinching:
            self.current_movement = "DRAG"
        elif self.orbit_delta:
            self.current_movement = "ORBIT"
        else:
            self.current_movement = "NONE"
        if not self.pinching:
            self.selected_layer = "-"

    def _update_state(self):
        now = time.time()
        if self.pinch_just_started:
            self.state = "PINCH_DETECTED"
        elif self.pinching:
            self.state = "TRACKING_MOVEMENT"
        elif self.orbit_delta:
            self.state = "ORBITING"
        elif self._last_shuffle_t and now - self._last_shuffle_t < COOLDOWN_S:
            self.state = "COOLDOWN"
        else:
            self.state = "IDLE"

    # ══════════════════════════════════════════════════
    #  API POUR main.py
    # ══════════════════════════════════════════════════

    def set_grabbed_face(self, face) -> None:
        """main.py appelle ceci juste après renderer.press(), pour que le
        HUD affiche la face effectivement attrapée (FRONT/UP/...)."""
        self.selected_layer = self.FRIENDLY_FACE.get(face, "-") if face else "-"

    def last_pinch_pixel(self, W: int, H: int):
        """Position en pixels du dernier point de pincement connu — à
        utiliser au moment du relâcher (pinch_just_ended)."""
        if self._last_pinch_point is None:
            return None
        x, y = self._last_pinch_point
        return (int(x * W), int(y * H))

    def get_move(self):
        """Renvoie 'SHUFFLE' quand le pouce levé est maintenu (avec
        cooldown pour éviter les répétitions accidentelles)."""
        now = time.time()
        if now < self._ready:
            return None
        if self._stable != "THUMB_UP":
            return None
        if now - self._last_shuffle_t < COOLDOWN_S:
            return None
        self._last_shuffle_t = now
        self._gbuf.clear()
        self._stable = "NONE"
        print("[Gesture] THUMB_UP → SHUFFLE")
        return "SHUFFLE"
