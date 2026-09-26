#!/usr/bin/env python3
# main.py
"""
Rubik's Cube AR — Gesture Control
Point d'entrée de l'application.

Pipeline par frame :
  caméra → HandTracker (squelette 21 points)
         → GestureRecognizer (poing → orbite, pincement → grab&turn)
         → RubiksCube (état facelets)
         → CubeRenderer (rendu 3D overlay + effets)
         → HUD (panneaux d'information)

Contrôles main (caméra) :
  - Poing fermé + déplacement     → orbite la caméra autour du cube
  - Pincement (pouce + index)
      sur un sticker, puis glisser → tourne la face correspondante
  - Pouce levé (maintenu)          → mélange le cube

Contrôles souris (identiques, en secours) :
  - Glisser sur un sticker  → tourne la face correspondante
  - Glisser dans le vide    → orbite la caméra autour du cube

Contrôles clavier (voir utils/config.py) :
  Q / Esc   quitter          S   mélanger        R   réinitialiser
  V         résoudre         +/-  zoom            flèches / WASD  orbiter
"""
from __future__ import annotations

import os
import sys
import time
import traceback
import cv2

# ── Rend l'import robuste quel que soit le répertoire d'où le script
#    est lancé (ex: double-clic, autre venv, lancement depuis un autre
#    dossier) : on force le dossier du script en tête de sys.path pour
#    que "cube", "gestures", "ui", "utils" soient toujours trouvés.
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

for _pkg in ("cube", "gestures", "ui", "utils"):
    if not os.path.isdir(os.path.join(_PROJECT_ROOT, _pkg)):
        sys.exit(
            f"[Main] Dossier '{_pkg}/' introuvable a cote de main.py.\n"
            f"       Repertoire attendu : {_PROJECT_ROOT}\n"
            f"       -> Verifie que le zip a bien ete extrait SANS dossier "
            f"imbrique (main.py, cube/, gestures/, ui/, utils/ doivent "
            f"etre directement dans ce dossier)."
        )

from utils.config import (
    CAM_INDEX, CAM_FPS, OUTPUT_W, OUTPUT_H, WINDOW_NAME,
    SHUFFLE_N, STARTUP_DELAY_S,
    AUTO_ROTATE, AUTO_ROTATE_SPEED, ORBIT_SENSITIVITY,
    KEY_QUIT, KEY_SHUFFLE, KEY_RESET, KEY_SOLVE,
    KEY_ZOOM_IN, KEY_ZOOM_OUT,
    KEY_ROT_L, KEY_ROT_R, KEY_ROT_U, KEY_ROT_D,
)
from cube import RubiksCube, CubeRenderer, CubeSolver
from gestures import HandTracker, GestureRecognizer
from ui import HUD

# Durée d'affichage de l'état "ROTATING" après un move (s)
MOVE_FLASH_S = 0.22
# Intervalle entre deux coups joués automatiquement pendant la résolution (s)
SOLVE_STEP_S = 0.35

ENTER_KEYS = (13, 10)


def _key_match(key: int, mapping) -> bool:
    if isinstance(mapping, (list, tuple)):
        return key in mapping
    return key == mapping


class App:

    def __init__(self) -> None:
        self.cap = self._open_camera()
        if not self.cap.isOpened():
            raise RuntimeError(
                f"[Main] Impossible d'ouvrir la caméra (index={CAM_INDEX})"
            )

        self.tracker  = HandTracker()
        self.rec      = GestureRecognizer()
        self.cube     = RubiksCube()
        self.renderer = CubeRenderer(OUTPUT_W, OUTPUT_H)
        self.solver   = CubeSolver()
        self.hud      = HUD()

        self._move_flash_until  = 0.0
        self._solving           = False
        self._solve_next_t      = 0.0
        self._calibrated        = False
        self._calib_progress    = 0.0   # secondes accumulées main détectée
        self._last_frame_t      = None
        self._last_mouse        = (0, 0)
        self._frame_count       = 0      # pour la période de grâce anti-touche-fantôme

        cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(WINDOW_NAME, OUTPUT_W, OUTPUT_H)
        cv2.setMouseCallback(WINDOW_NAME, self._on_mouse)

    @staticmethod
    def _open_camera():
        """Ouvre la caméra en essayant d'abord le backend DirectShow sous
        Windows (beaucoup plus fiable que le défaut MSMF pour la capture
        d'images et les réglages de résolution/FPS), puis se rabat sur le
        backend par défaut si besoin. Réessaie aussi la première lecture
        quelques fois : certains pilotes renvoient une frame invalide le
        temps que la caméra "chauffe"."""
        backends = [cv2.CAP_DSHOW, cv2.CAP_ANY] if os.name == "nt" else [cv2.CAP_ANY]
        cap = None
        for backend in backends:
            c = cv2.VideoCapture(CAM_INDEX, backend)
            if c.isOpened():
                cap = c
                break
            c.release()
        if cap is None:
            cap = cv2.VideoCapture(CAM_INDEX)

        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  OUTPUT_W)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, OUTPUT_H)
        cap.set(cv2.CAP_PROP_FPS, CAM_FPS)

        # Laisse quelques essais à la caméra pour renvoyer sa première
        # frame valide (warm-up), plutôt que d'abandonner immédiatement.
        for attempt in range(20):
            ok, _ = cap.read()
            if ok:
                break
            time.sleep(0.1)
        else:
            print("[Main] Avertissement : aucune frame valide reçue "
                  "pendant l'initialisation de la caméra (on continue "
                  "quand même, ça peut se stabiliser).")
        return cap

    # ══════════════════════════════════════════════════
    #  SOURIS
    # ══════════════════════════════════════════════════

    def _on_mouse(self, event, x, y, flags, param):
        if event == cv2.EVENT_MOUSEMOVE:
            lx, ly = self._last_mouse
            if flags & cv2.EVENT_FLAG_LBUTTON:
                self.renderer.drag_orbit(x - lx, y - ly)
            else:
                self.renderer.hover(x, y)
            self._last_mouse = (x, y)
        elif event == cv2.EVENT_LBUTTONDOWN:
            self.renderer.press(x, y)
            self._last_mouse = (x, y)
        elif event == cv2.EVENT_LBUTTONUP:
            mv = self.renderer.release(x, y)
            if mv:
                self._apply_move(mv)

    # ══════════════════════════════════════════════════
    #  INTERACTION MAIN (pincement = grab&turn, poing = orbite)
    # ══════════════════════════════════════════════════

    def _handle_hand_interaction(self) -> None:
        rec, renderer = self.rec, self.renderer

        # ── Poing fermé + déplacement → orbite la vue ──
        if rec.orbit_delta:
            dx, dy = rec.orbit_delta
            renderer.rotate_view(
                dx=dx * OUTPUT_W * ORBIT_SENSITIVITY,
                dy=dy * OUTPUT_H * ORBIT_SENSITIVITY,
            )

        # ── Pincement → attrape un sticker (comme un clic souris) ──
        if rec.pinch_just_started and rec.pinch_point:
            px = int(rec.pinch_point[0] * OUTPUT_W)
            py = int(rec.pinch_point[1] * OUTPUT_H)
            renderer.press(px, py)
            rec.set_grabbed_face(renderer.grabbed_face)

        elif rec.pinching and rec.pinch_point:
            px = int(rec.pinch_point[0] * OUTPUT_W)
            py = int(rec.pinch_point[1] * OUTPUT_H)
            renderer.hover(px, py)

        elif rec.pinch_just_ended:
            pt = rec.last_pinch_pixel(OUTPUT_W, OUTPUT_H)
            if pt:
                mv = renderer.release(*pt)
                if mv:
                    self._apply_move(mv)
            rec.set_grabbed_face(None)

    # ══════════════════════════════════════════════════
    #  ACTIONS CUBE
    # ══════════════════════════════════════════════════

    def _apply_move(self, mv: str) -> None:
        self.cube.apply_move(mv)
        self.cube.state = "ROTATING"
        self._move_flash_until = time.time() + MOVE_FLASH_S
        self.renderer.trigger_move_flash()

    def _shuffle(self) -> None:
        self.solver.reset()
        self._solving = False
        self.cube.shuffle(SHUFFLE_N)
        self.cube.state = "IDLE"
        self.renderer.trigger_flash(0.8)

    def _reset(self) -> None:
        self.cube.reset()
        self.solver.reset()
        self._solving = False
        self.renderer.trigger_flash(0.5)

    def _start_solve(self) -> None:
        if self.cube.is_solved():
            return
        sol = self.solver.solve(self.cube)
        if sol:
            self._solving       = True
            self._solve_next_t  = time.time()
            self.cube.state     = "SOLVING"

    def _step_solve(self) -> None:
        now = time.time()
        if now < self._solve_next_t:
            return
        mv = self.solver.next_move()
        if mv is None:
            self._solving   = False
            self.cube.state = "IDLE"
            self.renderer.trigger_flash(1.0)
            return
        self._apply_move(mv)
        self.cube.state    = "SOLVING"   # reste en mode résolution
        self._solve_next_t = now + SOLVE_STEP_S

    # ══════════════════════════════════════════════════
    #  CLAVIER
    # ══════════════════════════════════════════════════

    def _handle_key(self, key: int) -> bool:
        """Retourne False pour quitter."""
        if key == -1:
            return True
        if _key_match(key, KEY_QUIT):
            return False
        if _key_match(key, KEY_SHUFFLE):
            self._shuffle()
        elif _key_match(key, KEY_RESET):
            self._reset()
        elif _key_match(key, KEY_SOLVE):
            self._start_solve()
        elif _key_match(key, KEY_ZOOM_IN):
            self.renderer.zoom(6)
        elif _key_match(key, KEY_ZOOM_OUT):
            self.renderer.zoom(-6)
        elif _key_match(key, KEY_ROT_L):
            self.renderer.rotate_view(dx=-4)
        elif _key_match(key, KEY_ROT_R):
            self.renderer.rotate_view(dx=4)
        elif _key_match(key, KEY_ROT_U):
            self.renderer.rotate_view(dy=-4)
        elif _key_match(key, KEY_ROT_D):
            self.renderer.rotate_view(dy=4)
        return True

    # ══════════════════════════════════════════════════
    #  ÉCRAN DE CALIBRATION (démarrage)
    # ══════════════════════════════════════════════════
    #  Deux étapes, comme dans la vidéo de référence :
    #    1) main non détectée   → "SHOW YOUR OPEN HAND TO THE CAMERA"
    #       (barre à 0, en attente)
    #    2) main détectée       → "HOLD STILL - CALIBRATING"
    #       (barre verte qui ne progresse QUE si la main reste visible ;
    #        elle se met en pause, sans se réinitialiser, si la main
    #        disparaît un instant)

    def _draw_calibration(self, frame, ratio: float, active: bool) -> None:
        H, W = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (W, H), (10, 10, 14), -1)
        cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)

        bar_col = (0, 215, 0) if active else (0, 215, 215)

        bw, bh = 520, 140
        bx, by = W // 2 - bw // 2, H // 2 - bh // 2
        cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (200, 200, 0), 1)

        title = "CALIBRATION"
        (tw, _), _ = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
        cv2.putText(frame, title, (W // 2 - tw // 2, by + 38),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (200, 200, 0), 2, cv2.LINE_AA)

        sub = "HOLD STILL - CALIBRATING" if active else "SHOW YOUR OPEN HAND TO THE CAMERA"
        (sw, _), _ = cv2.getTextSize(sub, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.putText(frame, sub, (W // 2 - sw // 2, by + 66),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (230, 230, 230), 1, cv2.LINE_AA)

        pbx, pby, pbw, pbh = bx + 40, by + 90, bw - 80, 14
        cv2.rectangle(frame, (pbx, pby), (pbx + pbw, pby + pbh), (40, 40, 40), -1)
        fw = int(pbw * max(0.0, min(1.0, ratio)))
        if fw > 0:
            cv2.rectangle(frame, (pbx, pby), (pbx + fw, pby + pbh), bar_col, -1)
        cv2.rectangle(frame, (pbx, pby), (pbx + pbw, pby + pbh), (90, 90, 90), 1)

        hint = "Place your open hand inside the blue frame  |  ENTER = skip"
        (hw, _), _ = cv2.getTextSize(hint, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
        cv2.putText(frame, hint, (W // 2 - hw // 2, by + bh - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1, cv2.LINE_AA)

    # ══════════════════════════════════════════════════
    #  BOUCLE PRINCIPALE
    # ══════════════════════════════════════════════════

    def run(self) -> None:
        try:
            while True:
                ok, frame = self.cap.read()
                if not ok:
                    print(f"[Main] Flux caméra interrompu "
                          f"(frame #{self._frame_count}).")
                    break
                self._frame_count += 1

                frame = cv2.flip(frame, 1)
                if (frame.shape[1], frame.shape[0]) != (OUTPUT_W, OUTPUT_H):
                    frame = cv2.resize(frame, (OUTPUT_W, OUTPUT_H))

                frame = self.tracker.process(frame)
                self.rec.update(self.tracker.finger_states,
                                 self.tracker.hand_position,
                                 self.tracker.landmarks)

                now = time.time()
                raw_dt = 0.0 if self._last_frame_t is None else now - self._last_frame_t
                # Plafonné : la toute première inférence MediaPipe peut
                # prendre 1 à 3s (chargement du modèle) ; sans ce plafond,
                # ce délai serait compté d'un coup dans la calibration.
                dt = max(0.0, min(raw_dt, 0.1))
                self._last_frame_t = now

                # Période de grâce : ignore une éventuelle touche
                # "fantôme" capturée juste à la création de la fenêtre
                # (rare, mais évite une fermeture instantanée surprenante).
                in_grace_period = self._frame_count <= 15

                # ── Écran de calibration au démarrage ──
                #    la barre ne progresse que si une main est détectée
                #    (elle se met en pause, sans se réinitialiser, sinon)
                if not self._calibrated:
                    if self.tracker.hand_detected:
                        self._calib_progress += dt
                    if self._calib_progress >= STARTUP_DELAY_S:
                        self._calibrated = True
                        print("[Main] Calibration terminée, démarrage du jeu.")
                    else:
                        ratio = self._calib_progress / STARTUP_DELAY_S
                        self._draw_calibration(frame, ratio, self.tracker.hand_detected)
                        cv2.imshow(WINDOW_NAME, frame)
                        key = cv2.waitKey(1) & 0xFF
                        if key in ENTER_KEYS:
                            self._calibrated = True
                            print("[Main] Calibration passée (Entrée).")
                        elif _key_match(key, KEY_QUIT) and not in_grace_period:
                            print(f"[Main] Touche quitter pendant la "
                                  f"calibration (code={key}).")
                            break
                        continue

                # ── Rotation automatique douce si inactif ──
                hand_orbiting = bool(self.rec.orbit_delta)
                if AUTO_ROTATE and not self.renderer.dragging and not hand_orbiting:
                    self.renderer.auto_rotate(AUTO_ROTATE_SPEED)

                # ── Interaction main : orbite (FIST) / grab&turn (PINCH) ──
                if not self._solving:
                    self._handle_hand_interaction()

                # ── Résolution automatique OU geste de mélange ──
                if self._solving:
                    self._step_solve()
                else:
                    mv = self.rec.get_move()
                    if mv == "SHUFFLE":
                        self._shuffle()

                # ── Fin de l'effet "ROTATING" ──
                if self.cube.state == "ROTATING" and now > self._move_flash_until:
                    self.cube.state = "IDLE"

                # ── Rendu ──
                frame = self.renderer.render(frame, self.cube)
                frame = self.hud.draw(frame, self.tracker, self.rec, self.cube)

                cv2.imshow(WINDOW_NAME, frame)
                key = cv2.waitKey(1) & 0xFF
                if _key_match(key, KEY_QUIT) and in_grace_period:
                    key = -1  # ignore une éventuelle touche fantôme au tout démarrage
                if not self._handle_key(key):
                    print(f"[Main] Touche quitter (code={key}).")
                    break
        except Exception:
            print("[Main] Erreur inattendue :")
            traceback.print_exc()
        finally:
            self.cleanup()

    def cleanup(self) -> None:
        self.tracker.close()
        self.cap.release()
        cv2.destroyAllWindows()
        print("[Main] Arrêt propre.")


def main() -> None:
    try:
        App().run()
    except Exception:
        print("[Main] Erreur fatale au démarrage :")
        traceback.print_exc()
        input("Appuyez sur Entrée pour fermer...")


if __name__ == "__main__":
    main()
