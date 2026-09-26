# ui/hud.py
"""
HUD professionnel — optimisé (vignette et graphiques cachés).
"""

import cv2
import time
import math
import numpy as np
from collections import deque


class FPSCounter:
    def __init__(self, n: int = 30):
        self._t = deque(maxlen=n)

    def tick(self) -> float:
        self._t.append(time.perf_counter())
        if len(self._t) < 2:
            return 0.0
        return (len(self._t)-1) / (self._t[-1]-self._t[0])


class HUD:

    FONT  = cv2.FONT_HERSHEY_SIMPLEX
    FONTB = cv2.FONT_HERSHEY_DUPLEX

    # Palette BGR
    C_TEAL   = (180, 200,   0)
    C_WHITE  = (225, 225, 225)
    C_GRAY   = (105, 105, 105)
    C_GREEN  = (  0, 210,   0)
    C_ORANGE = (  0, 140, 255)
    C_YELLOW = (  0, 195, 195)
    C_RED    = ( 30,  30, 200)
    C_BLUE   = (200,   0,   0)
    C_PURPLE = (180,   0, 180)
    C_DARK   = ( 10,  10,  14)

    def __init__(self):
        self._fps      = FPSCounter(30)
        self._fps_hist = deque(maxlen=60)

    # ──────────────────────────────────────────────────────────────

    def draw(self, frame: np.ndarray,
             tracker, rec, cube) -> np.ndarray:
        fps  = self._fps.tick()
        self._fps_hist.append(fps)
        H, W = frame.shape[:2]
        t    = time.time()

        self._panel(frame, tracker, rec, cube, fps, t)
        self._layer_bar(frame, rec, W, H, t)
        self._moves_bar(frame, cube, W, H)
        self._status(frame, tracker, rec, W, H, t)
        self._top_right(frame, cube, fps, W)
        self._fps_graph(frame, W, H)
        self._gesture_help(frame, rec, W, H, t)
        self._border(frame, W, H, t, cube)

        if cube.is_solved():
            self._solved_banner(frame, W, t)

        return frame

    # ──────────────────────────────────────────────────────────────
    #  UTILITAIRES
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _bg(frame, x, y, w, h, alpha=0.72, color=(10,10,14)):
        """Rectangle semi-transparent."""
        H_f, W_f = frame.shape[:2]
        x2, y2   = min(x+w, W_f), min(y+h, H_f)
        if x2 <= x or y2 <= y:
            return
        roi = frame[y:y2, x:x2]
        bg  = np.full_like(roi, color, dtype=np.uint8)
        cv2.addWeighted(bg, alpha, roi, 1-alpha, 0, roi)
        frame[y:y2, x:x2] = roi

    @staticmethod
    def _border_rect(frame, x, y, w, h, color, thick=1):
        cv2.rectangle(frame, (x,y), (x+w,y+h), color, thick)

    @staticmethod
    def _glow(frame, text, pos, font, scale, color,
              thick=1, radius=2):
        """Texte avec halo."""
        gc = tuple(max(0, int(v*0.35)) for v in color)
        for dx_ in range(-radius, radius+1, 1):
            for dy_ in range(-radius, radius+1, 1):
                if dx_*dx_ + dy_*dy_ <= radius*radius:
                    cv2.putText(
                        frame, text,
                        (pos[0]+dx_, pos[1]+dy_),
                        font, scale, gc, thick+1,
                        cv2.LINE_AA
                    )
        cv2.putText(frame, text, pos, font, scale,
                    color, thick, cv2.LINE_AA)

    @staticmethod
    def _shadow_text(frame, text, pos, font, scale,
                     color, thick=1):
        cv2.putText(frame, text,
                    (pos[0]+1, pos[1]+1),
                    font, scale, (0,0,0), thick+1,
                    cv2.LINE_AA)
        cv2.putText(frame, text, pos, font, scale,
                    color, thick, cv2.LINE_AA)

    @staticmethod
    def _progress(frame, x, y, w, h, ratio,
                  col_fg=(0,215,215), col_bg=(25,25,35)):
        cv2.rectangle(frame, (x,y), (x+w,y+h), col_bg, -1)
        fw = max(0, int(w * min(1.0, max(0.0, ratio))))
        if fw > 0:
            cv2.rectangle(frame, (x,y), (x+fw,y+h), col_fg, -1)
        cv2.rectangle(frame, (x,y), (x+w,y+h), (50,50,65), 1)

    def _dot(self, frame, cx, cy, r, color, blink=False):
        if blink:
            a = (math.sin(time.time()*3)+1)/2
            c = tuple(int(v*a) for v in color)
        else:
            c = color
        cv2.circle(frame, (cx,cy), r, (0,0,0), -1)
        cv2.circle(frame, (cx,cy), r-1, c, -1, cv2.LINE_AA)

    # ──────────────────────────────────────────────────────────────
    #  PANNEAU PRINCIPAL
    # ──────────────────────────────────────────────────────────────

    def _panel(self, frame, tracker, rec, cube, fps, t):
        px, py, pw, ph = 12, 12, 290, 270

        self._bg(frame, px, py, pw, ph, alpha=0.80)

        # Titre bar
        cv2.rectangle(frame, (px,py), (px+pw,py+30),
                      (18,20,28), -1)

        # Bordure pulsante
        pulse = (math.sin(t*2.2)+1)/2
        bc    = tuple(int(v*(0.55+0.45*pulse))
                      for v in self.C_TEAL)
        cv2.rectangle(frame, (px,py), (px+pw,py+ph), bc, 1)
        cv2.rectangle(frame, (px,py), (px+pw,py+30), bc, 1)

        # Titre
        self._glow(frame, "GESTURE CONTROL",
                   (px+12, py+21),
                   self.FONT, 0.52, self.C_TEAL,
                   thick=1, radius=2)

        # Pastille tracking
        self._dot(frame,
                  px+pw-16, py+16, 6,
                  self.C_GREEN if tracker.hand_detected
                  else self.C_ORANGE,
                  blink=not tracker.hand_detected)

        # Données
        rows = [
            ("TRACKING",
             "ACTIVE" if tracker.hand_detected else "SEARCHING",
             self.C_GREEN if tracker.hand_detected
             else self.C_ORANGE),
            ("GESTURE",   rec.current_gesture,
             self._gest_col(rec.current_gesture)),
            ("MOVEMENT",  rec.current_movement,
             self._move_col(rec.current_movement)),
            ("LAYER",     rec.selected_layer,   self.C_YELLOW),
            ("DIRECTION", rec.rotation_dir,      self.C_WHITE),
            ("STATE",     cube.state,
             self._state_col(cube.state)),
            ("FPS",       f"{fps:.0f}",
             self.C_GREEN if fps >= 24
             else self.C_ORANGE if fps >= 14
             else self.C_RED),
        ]

        for i, (lbl, val, col) in enumerate(rows):
            yy = py + 50 + i*30

            # Séparateur léger
            if i:
                cv2.line(frame,
                         (px+8, yy-10),
                         (px+pw-8, yy-10),
                         (28, 28, 38), 1)

            # Barre colorée gauche
            cv2.rectangle(frame,
                          (px, yy-16), (px+3, yy+2),
                          col, -1)

            cv2.putText(frame, lbl,
                        (px+12, yy), self.FONT,
                        0.37, self.C_GRAY, 1)
            self._shadow_text(frame, str(val),
                              (px+155, yy), self.FONT,
                              0.43, col, thick=1)

        # Barre FPS
        self._progress(frame,
                       px+10, py+ph-16,
                       pw-20, 5,
                       min(1.0, fps/60.0),
                       col_fg=self.C_GREEN if fps>=24
                              else self.C_ORANGE)

    # ──────────────────────────────────────────────────────────────
    #  SÉLECTEUR COUCHES
    # ──────────────────────────────────────────────────────────────

    def _layer_bar(self, frame, rec, W, H, t):
        layers = ["FRONT", "BACK", "UP", "DOWN", "LEFT", "RIGHT"]
        lh, lw = 36, 108
        lx     = W - lw - 12
        start  = H//2 - (len(layers)*lh)//2

        total_h = len(layers)*lh + 20
        self._bg(frame, lx-8, start-10,
                 lw+18, total_h,
                 alpha=0.78)
        cv2.rectangle(frame,
                      (lx-8, start-10),
                      (lx+lw+10, start+total_h-10),
                      (42,42,55), 1)

        cv2.putText(frame, "LAYER",
                    (lx, start-16),
                    self.FONT, 0.34, self.C_GRAY, 1)

        for i, layer in enumerate(layers):
            ly     = start + i*lh
            is_sel = (rec.selected_layer == layer)

            if is_sel:
                pulse = (math.sin(t*3.2)+1)/2
                sc    = tuple(
                    int(v*(0.25+0.18*pulse))
                    for v in self.C_TEAL
                )
                cv2.rectangle(frame,
                              (lx-4, ly),
                              (lx+lw+4, ly+lh-4),
                              sc, -1)
                cv2.rectangle(frame,
                              (lx-4, ly),
                              (lx+lw+4, ly+lh-4),
                              self.C_TEAL, 1)
                self._glow(frame, layer,
                           (lx+8, ly+24),
                           self.FONT, 0.44,
                           self.C_TEAL,
                           thick=1, radius=2)
                # Flèche
                ax = lx - 13
                ay = ly + lh//2
                tri = np.array([
                    [ax,   ay],
                    [ax-7, ay-5],
                    [ax-7, ay+5],
                ], dtype=np.int32)
                cv2.fillPoly(frame, [tri], self.C_TEAL)
            else:
                cv2.putText(frame, layer,
                            (lx+8, ly+24),
                            self.FONT, 0.38,
                            self.C_GRAY, 1)

            if i < len(layers)-1:
                cv2.line(frame,
                         (lx, ly+lh-2),
                         (lx+lw, ly+lh-2),
                         (32,32,44), 1)

    # ──────────────────────────────────────────────────────────────
    #  BARRE MOVES
    # ──────────────────────────────────────────────────────────────

    def _moves_bar(self, frame, cube, W, H):
        bx, by = 12, H-74
        bw, bh = W//2 - 20, 60

        self._bg(frame, bx, by, bw, bh, alpha=0.78)
        cv2.rectangle(frame, (bx,by), (bx+bw,by+bh),
                      (42,42,55), 1)

        n = len(cube.moves_history)
        cv2.putText(frame, f"MOVES [{n}]",
                    (bx+10, by+18), self.FONT,
                    0.38, self.C_GRAY, 1)

        moves = cube.moves_history[-18:]
        txt   = "  ".join(moves) if moves else "—"

        max_w = bw - 20
        while True:
            (tw, _), _ = cv2.getTextSize(
                txt, self.FONT, 0.48, 1
            )
            if tw <= max_w:
                break
            parts = txt.split("  ", 1)
            if len(parts) < 2:
                break
            txt = "…  " + parts[1]

        # Dernier move mis en valeur
        parts = txt.rsplit("  ", 1)
        if len(parts) == 2 and moves:
            pre, last = parts
            cv2.putText(frame, pre+"  ",
                        (bx+10, by+50),
                        self.FONT, 0.47,
                        self.C_GRAY, 1)
            (pw_, _), _ = cv2.getTextSize(
                pre+"  ", self.FONT, 0.47, 1
            )
            self._shadow_text(frame, last,
                              (bx+10+pw_, by+50),
                              self.FONT, 0.52,
                              self.C_TEAL, thick=1)
        else:
            cv2.putText(frame, txt,
                        (bx+10, by+50),
                        self.FONT, 0.47,
                        self.C_WHITE, 1)

    # ──────────────────────────────────────────────────────────────
    #  STATUT BAS CENTRE
    # ──────────────────────────────────────────────────────────────

    def _status(self, frame, tracker, rec, W, H, t):
        if not tracker.hand_detected:
            msg = "  ◇  WAITING FOR GESTURE  "
            col = self.C_ORANGE
        elif rec.state == "PINCH_DETECTED":
            face = rec.selected_layer if rec.selected_layer != "-" else "?"
            msg  = f"  ◆  PINCH DETECTED — {face} FACE  "
            col  = self.C_TEAL
        elif rec.state == "TRACKING_MOVEMENT":
            msg = "  ◆  TRACKING MOVEMENT — DRAG TO TURN A LAYER  "
            col = self.C_GREEN
        elif rec.state == "ORBITING":
            msg = "  ◆  FIST — ORBIT VIEW  "
            col = self.C_YELLOW
        elif rec.state == "COOLDOWN":
            msg = "  ◆  COOLDOWN  "
            col = self.C_PURPLE
        else:
            g   = rec.current_gesture
            m   = rec.current_movement
            msg = f"  ◆  {g}  ·  {m}  "
            col = self.C_GREEN

        (tw, th), _ = cv2.getTextSize(
            msg, self.FONT, 0.56, 1
        )
        tx = (W - tw)//2
        ty = H - 18

        bx1, by1 = tx-18, ty-th-12
        bx2, by2 = tx+tw+18, ty+10

        self._bg(frame, bx1, by1,
                 bx2-bx1, by2-by1, alpha=0.82)

        pulse = (math.sin(t*3)+1)/2
        bc    = tuple(int(v*(0.5+0.5*pulse)) for v in col)
        cv2.rectangle(frame, (bx1,by1), (bx2,by2), bc, 2)

        self._dot(frame,
                  tx-6, ty-th//2, 5, col,
                  blink=not tracker.hand_detected)

        self._shadow_text(frame, msg, (tx,ty),
                          self.FONT, 0.56, col)

    # ──────────────────────────────────────────────────────────────
    #  TOP RIGHT
    # ──────────────────────────────────────────────────────────────

    def _top_right(self, frame, cube, fps, W):
        lines = [
            (f"{W}×720  ·  {fps:.0f} FPS",       self.C_GRAY),
            ("MediaPipe  ·  NumPy  ·  OpenCV",    self.C_GRAY),
            (f"MOVES: {len(cube.moves_history)}"
             f"  ·  {'✓ SOLVED' if cube.is_solved() else 'PLAYING'}",
             self.C_GREEN if cube.is_solved() else self.C_GRAY),
        ]
        for i, (ln, col) in enumerate(lines):
            (tw,_),_ = cv2.getTextSize(ln, self.FONT, 0.36, 1)
            cv2.putText(frame, ln,
                        (W-tw-10, 15+i*16),
                        self.FONT, 0.36, col, 1,
                        cv2.LINE_AA)

    # ──────────────────────────────────────────────────────────────
    #  GRAPHIQUE FPS
    # ──────────────────────────────────────────────────────────────

    def _fps_graph(self, frame, W, H):
        if len(self._fps_hist) < 4:
            return
        gx, gy, gw, gh = 12, 295, 140, 42

        self._bg(frame, gx, gy, gw, gh, alpha=0.75)
        cv2.rectangle(frame, (gx,gy), (gx+gw,gy+gh),
                      (35,35,48), 1)
        cv2.putText(frame, "FPS",
                    (gx+4, gy+12), self.FONT, 0.30,
                    self.C_GRAY, 1)

        # Ligne 30 FPS
        ref = gy+gh - int(30/62.0*(gh-15)) - 2
        cv2.line(frame, (gx+2,ref), (gx+gw-2,ref),
                 (40,40,52), 1)

        hist = list(self._fps_hist)
        n    = len(hist)
        pts  = []
        for i, v in enumerate(hist):
            px_ = gx + 2 + int(i*(gw-4)/max(1,n-1))
            py_ = gy+gh-2 - int(min(v,62)/62.0*(gh-15))
            pts.append((px_, py_))

        if len(pts) > 1:
            # Fill
            fill = np.array(
                pts
                + [(pts[-1][0], gy+gh-2),
                   (pts[0][0],  gy+gh-2)],
                dtype=np.int32
            )
            ov = frame.copy()
            cv2.fillPoly(ov, [fill], (0,40,40))
            cv2.addWeighted(ov, 0.28, frame, 0.72, 0, frame)

            # Courbe
            for i in range(len(pts)-1):
                v   = hist[i]
                col = (self.C_GREEN  if v >= 24
                       else self.C_ORANGE if v >= 14
                       else self.C_RED)
                cv2.line(frame, pts[i], pts[i+1],
                         col, 1, cv2.LINE_AA)

    # ──────────────────────────────────────────────────────────────
    #  GUIDE GESTES
    # ──────────────────────────────────────────────────────────────

    def _gesture_help(self, frame, rec, W, H, t):
        gx  = W//2 + 25
        gy  = H - 74
        gw  = W - gx - 140
        gh  = 60

        self._bg(frame, gx, gy, gw, gh, alpha=0.78)
        cv2.rectangle(frame, (gx,gy), (gx+gw,gy+gh),
                      (42,42,55), 1)
        cv2.putText(frame, "GESTURES",
                    (gx+8, gy+15), self.FONT,
                    0.34, self.C_GRAY, 1)

        guides = [
            ("FIST",     "ORBIT",   self.C_YELLOW),
            ("PINCH",    "GRAB",    self.C_TEAL),
            ("THUMB_UP", "SHUFFLE", self.C_PURPLE),
        ]

        cw    = max(1, (gw-16)//3)
        cur_g = rec.current_gesture

        for i, (sym, act, col) in enumerate(guides):
            ci  = i % 3
            ri  = i // 3
            gx_ = gx + 8 + ci*cw
            gy_ = gy + 30 + ri*18
            txt = f"{sym}:{act}"
            active = (cur_g == sym)

            if active:
                p = (math.sin(t*4)+1)/2
                c = tuple(min(255,int(v*(0.7+0.3*p)))
                          for v in col)
                self._glow(frame, txt, (gx_,gy_),
                           self.FONT, 0.29, c,
                           thick=1, radius=1)
            else:
                cv2.putText(frame, txt, (gx_,gy_),
                            self.FONT, 0.29,
                            self.C_GRAY, 1)

    # ──────────────────────────────────────────────────────────────
    #  BORDURE ANIMÉE
    # ──────────────────────────────────────────────────────────────

    def _border(self, frame, W, H, t, cube):
        if cube.is_solved():
            hue = (t*60) % 360
            r   = int(127+127*math.sin(math.radians(hue)))
            g   = int(127+127*math.sin(math.radians(hue+120)))
            b   = int(127+127*math.sin(math.radians(hue+240)))
            col = (b, g, r)
            th  = 3
        elif cube.state == "ROTATING":
            p   = (math.sin(t*8)+1)/2
            col = (int(80*p), int(120*p), int(240*p))
            th  = 2
        elif cube.state == "SOLVING":
            p   = (math.sin(t*6)+1)/2
            col = (int(180*p), int(20*p), int(180*p))
            th  = 2
        else:
            i   = 0.28 + 0.10*math.sin(t*0.6)
            col = tuple(int(v*i) for v in self.C_TEAL)
            th  = 1

        cv2.rectangle(frame, (2,2), (W-2,H-2), col, th)

    # ──────────────────────────────────────────────────────────────
    #  BANNER SOLVED
    # ──────────────────────────────────────────────────────────────

    def _solved_banner(self, frame, W, t):
        msg = "  \u2605  CUBE SOLVED  \u2605  "
        hue = (t*50) % 360
        r   = int(127+127*math.sin(math.radians(hue)))
        g   = int(127+127*math.sin(math.radians(hue+120)))
        b   = int(127+127*math.sin(math.radians(hue+240)))
        col = (b, g, r)

        (tw, th_), _ = cv2.getTextSize(
            msg, self.FONTB, 1.0, 2
        )
        tx = (W-tw)//2

        self._bg(frame, tx-22, 54, tw+44, 54,
                 alpha=0.88)
        cv2.rectangle(frame, (tx-22,54),
                      (tx+tw+22,108), col, 2)
        self._glow(frame, msg, (tx,96),
                   self.FONTB, 1.0, col,
                   thick=2, radius=3)

    # ──────────────────────────────────────────────────────────────
    #  COULEURS CONTEXTUELLES
    # ──────────────────────────────────────────────────────────────

    def _gest_col(self, g):
        return {
            "FIST":     self.C_YELLOW,
            "OPEN":     self.C_GREEN,
            "PEACE":    self.C_TEAL,
            "THREE":    self.C_ORANGE,
            "POINT":    self.C_WHITE,
            "THUMB_UP": self.C_PURPLE,
        }.get(g, self.C_GRAY)

    def _move_col(self, m):
        return (self.C_TEAL
                if m in ("RIGHT","LEFT")
                else self.C_WHITE
                if m in ("UP","DOWN")
                else self.C_GRAY)

    def _state_col(self, s):
        return {
            "IDLE":     self.C_YELLOW,
            "ROTATING": self.C_ORANGE,
            "SOLVING":  self.C_PURPLE,
            "SOLVED":   self.C_GREEN,
        }.get(s, self.C_WHITE)