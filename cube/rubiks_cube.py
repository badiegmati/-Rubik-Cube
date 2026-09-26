# cube/rubiks_cube.py
"""
Rubik's Cube 3×3 — Représentation facelets WCA.
Tous les moves validés mathématiquement.
"""
from __future__ import annotations
import random, copy
from collections import Counter


class RubiksCube:

    FACES = ('U','D','F','B','L','R')

    # Couleurs BGR pour affichage
    COLORS_BGR = {
        'U': (255, 255, 255),  # Blanc
        'D': (  0, 215, 215),  # Jaune
        'F': (  0,   0, 220),  # Rouge
        'B': (  0, 130, 255),  # Orange
        'L': (  0, 200,   0),  # Vert
        'R': (220,   0,   0),  # Bleu
    }

    def __init__(self):
        self.moves_history: list[str] = []
        self.state = "IDLE"
        self.reset()

    # ══════════════════════════════════
    #  ÉTAT
    # ══════════════════════════════════

    def reset(self):
        self.faces = {f: [[f]*3 for _ in range(3)]
                      for f in self.FACES}
        self.moves_history.clear()
        self.state = "IDLE"

    def is_solved(self) -> bool:
        for f, g in self.faces.items():
            c = g[1][1]
            for r in range(3):
                for k in range(3):
                    if g[r][k] != c:
                        return False
        return True

    def copy(self) -> 'RubiksCube':
        n = RubiksCube.__new__(RubiksCube)
        n.faces = {f: [r[:] for r in g]
                   for f, g in self.faces.items()}
        n.moves_history = self.moves_history[:]
        n.state = self.state
        return n

    def validate(self) -> bool:
        all_c = [c for g in self.faces.values()
                 for r in g for c in r]
        cnt = Counter(all_c)
        for f in self.FACES:
            if cnt.get(f, 0) != 9:
                print(f"[Validate] {f}={cnt.get(f,0)}/9")
                return False
            if self.faces[f][1][1] != f:
                print(f"[Validate] centre {f} "
                      f"= {self.faces[f][1][1]}")
                return False
        return True

    # ══════════════════════════════════
    #  UTILITAIRES
    # ══════════════════════════════════

    def _r(self, f, i):      return self.faces[f][i][:]
    def _c(self, f, i):      return [self.faces[f][r][i]
                                     for r in range(3)]
    def _sr(self, f, i, v):  self.faces[f][i] = v[:]
    def _sc(self, f, i, v):
        for r in range(3): self.faces[f][r][i] = v[r]

    def _cw(self, f):
        g = self.faces[f]
        self.faces[f] = [
            [g[2][0],g[1][0],g[0][0]],
            [g[2][1],g[1][1],g[0][1]],
            [g[2][2],g[1][2],g[0][2]],
        ]

    def _ccw(self, f):
        self._cw(f); self._cw(f); self._cw(f)

    # ══════════════════════════════════
    #  MOVES VALIDÉS WCA
    # ══════════════════════════════════

    def move_U(self):
        self._cw('U')
        f,r,b,l = (self._r('F',0), self._r('R',0),
                   self._r('B',0), self._r('L',0))
        self._sr('R',0,f); self._sr('B',0,r)
        self._sr('L',0,b); self._sr('F',0,l)
        self.moves_history.append("U")

    def move_Ui(self):
        self._ccw('U')
        f,r,b,l = (self._r('F',0), self._r('R',0),
                   self._r('B',0), self._r('L',0))
        self._sr('L',0,f); self._sr('B',0,l)
        self._sr('R',0,b); self._sr('F',0,r)
        self.moves_history.append("U'")

    def move_U2(self):
        self.move_U(); self.move_U()
        self.moves_history[-2:] = ["U2"]

    def move_D(self):
        self._cw('D')
        f,r,b,l = (self._r('F',2), self._r('R',2),
                   self._r('B',2), self._r('L',2))
        self._sr('L',2,f); self._sr('B',2,l)
        self._sr('R',2,b); self._sr('F',2,r)
        self.moves_history.append("D")

    def move_Di(self):
        self._ccw('D')
        f,r,b,l = (self._r('F',2), self._r('R',2),
                   self._r('B',2), self._r('L',2))
        self._sr('R',2,f); self._sr('B',2,r)
        self._sr('L',2,b); self._sr('F',2,l)
        self.moves_history.append("D'")

    def move_D2(self):
        self.move_D(); self.move_D()
        self.moves_history[-2:] = ["D2"]

    def move_R(self):
        self._cw('R')
        u,f,d,b = (self._c('U',2), self._c('F',2),
                   self._c('D',2), self._c('B',0))
        self._sc('U',2,f); self._sc('F',2,d)
        self._sc('D',2,b[::-1]); self._sc('B',0,u[::-1])
        self.moves_history.append("R")

    def move_Ri(self):
        self._ccw('R')
        u,f,d,b = (self._c('U',2), self._c('F',2),
                   self._c('D',2), self._c('B',0))
        self._sc('F',2,u); self._sc('D',2,f)
        self._sc('B',0,d[::-1]); self._sc('U',2,b[::-1])
        self.moves_history.append("R'")

    def move_R2(self):
        self.move_R(); self.move_R()
        self.moves_history[-2:] = ["R2"]

    def move_L(self):
        self._cw('L')
        u,f,d,b = (self._c('U',0), self._c('F',0),
                   self._c('D',0), self._c('B',2))
        self._sc('U',0,b[::-1]); self._sc('B',2,d[::-1])
        self._sc('D',0,f);       self._sc('F',0,u)
        self.moves_history.append("L")

    def move_Li(self):
        self._ccw('L')
        u,f,d,b = (self._c('U',0), self._c('F',0),
                   self._c('D',0), self._c('B',2))
        self._sc('F',0,d); self._sc('D',0,b[::-1])
        self._sc('B',2,u[::-1]); self._sc('U',0,f)
        self.moves_history.append("L'")

    def move_L2(self):
        self.move_L(); self.move_L()
        self.moves_history[-2:] = ["L2"]

    def move_F(self):
        self._cw('F')
        u,r,d,l = (self._r('U',2), self._c('R',0),
                   self._r('D',0), self._c('L',2))
        self._sc('R',0,u); self._sr('D',0,r)
        self._sc('L',2,d[::-1]); self._sr('U',2,l[::-1])
        self.moves_history.append("F")

    def move_Fi(self):
        self._ccw('F')
        u,r,d,l = (self._r('U',2), self._c('R',0),
                   self._r('D',0), self._c('L',2))
        self._sr('U',2,r); self._sc('R',0,d)
        self._sr('D',0,l[::-1]); self._sc('L',2,u[::-1])
        self.moves_history.append("F'")

    def move_F2(self):
        self.move_F(); self.move_F()
        self.moves_history[-2:] = ["F2"]

    def move_B(self):
        self._cw('B')
        u,r,d,l = (self._r('U',0), self._c('R',2),
                   self._r('D',2), self._c('L',0))
        self._sc('L',0,u[::-1]); self._sr('D',2,l)
        self._sc('R',2,d[::-1]); self._sr('U',0,r)
        self.moves_history.append("B")

    def move_Bi(self):
        self._ccw('B')
        u,r,d,l = (self._r('U',0), self._c('R',2),
                   self._r('D',2), self._c('L',0))
        self._sr('U',0,l[::-1]); self._sc('L',0,d)
        self._sr('D',2,r[::-1]); self._sc('R',2,u)
        self.moves_history.append("B'")

    def move_B2(self):
        self.move_B(); self.move_B()
        self.moves_history[-2:] = ["B2"]

    def move_M(self):
        u,f,d,b = (self._c('U',1), self._c('F',1),
                   self._c('D',1), self._c('B',1))
        self._sc('U',1,b[::-1]); self._sc('B',1,d[::-1])
        self._sc('D',1,f);       self._sc('F',1,u)
        self.moves_history.append("M")

    def move_Mi(self):
        u,f,d,b = (self._c('U',1), self._c('F',1),
                   self._c('D',1), self._c('B',1))
        self._sc('F',1,d); self._sc('D',1,b[::-1])
        self._sc('B',1,u[::-1]); self._sc('U',1,f)
        self.moves_history.append("M'")

    def move_M2(self):
        self.move_M(); self.move_M()
        self.moves_history[-2:] = ["M2"]

    def move_E(self):
        f,r,b,l = (self._r('F',1), self._r('R',1),
                   self._r('B',1), self._r('L',1))
        self._sr('L',1,f); self._sr('B',1,l)
        self._sr('R',1,b); self._sr('F',1,r)
        self.moves_history.append("E")

    def move_Ei(self):
        f,r,b,l = (self._r('F',1), self._r('R',1),
                   self._r('B',1), self._r('L',1))
        self._sr('R',1,f); self._sr('B',1,r)
        self._sr('L',1,b); self._sr('F',1,l)
        self.moves_history.append("E'")

    def move_S(self):
        u,r,d,l = (self._r('U',1), self._c('R',1),
                   self._r('D',1), self._c('L',1))
        self._sc('R',1,u); self._sr('D',1,r)
        self._sc('L',1,d[::-1]); self._sr('U',1,l[::-1])
        self.moves_history.append("S")

    def move_Si(self):
        u,r,d,l = (self._r('U',1), self._c('R',1),
                   self._r('D',1), self._c('L',1))
        self._sr('U',1,r); self._sc('R',1,d)
        self._sr('D',1,l[::-1]); self._sc('L',1,u[::-1])
        self.moves_history.append("S'")

    # ══════════════════════════════════
    #  ROTATIONS GLOBALES (vue seulement)
    # ══════════════════════════════════

    def rotate_y(self):
        """Tout le cube tourne comme U."""
        u = copy.deepcopy(self.faces['U'])
        d = copy.deepcopy(self.faces['D'])
        f = copy.deepcopy(self.faces['F'])
        r = copy.deepcopy(self.faces['R'])
        b = copy.deepcopy(self.faces['B'])
        l = copy.deepcopy(self.faces['L'])
        self.faces['F'] = l; self.faces['R'] = f
        self.faces['B'] = r; self.faces['L'] = b
        # U tourne CW
        self.faces['U'] = [
            [u[2][0],u[1][0],u[0][0]],
            [u[2][1],u[1][1],u[0][1]],
            [u[2][2],u[1][2],u[0][2]],
        ]
        # D tourne CCW
        self.faces['D'] = [
            [d[0][2],d[1][2],d[2][2]],
            [d[0][1],d[1][1],d[2][1]],
            [d[0][0],d[1][0],d[2][0]],
        ]
        self.moves_history.append("y")

    def rotate_yi(self):
        """Tout le cube tourne comme U'."""
        u = copy.deepcopy(self.faces['U'])
        d = copy.deepcopy(self.faces['D'])
        f = copy.deepcopy(self.faces['F'])
        r = copy.deepcopy(self.faces['R'])
        b = copy.deepcopy(self.faces['B'])
        l = copy.deepcopy(self.faces['L'])
        self.faces['F'] = r; self.faces['L'] = f
        self.faces['B'] = l; self.faces['R'] = b
        # U tourne CCW
        self.faces['U'] = [
            [u[0][2],u[1][2],u[2][2]],
            [u[0][1],u[1][1],u[2][1]],
            [u[0][0],u[1][0],u[2][0]],
        ]
        # D tourne CW
        self.faces['D'] = [
            [d[2][0],d[1][0],d[0][0]],
            [d[2][1],d[1][1],d[0][1]],
            [d[2][2],d[1][2],d[0][2]],
        ]
        self.moves_history.append("y'")

    def rotate_x(self):
        """Tout le cube tourne comme R."""
        u = copy.deepcopy(self.faces['U'])
        f = copy.deepcopy(self.faces['F'])
        d = copy.deepcopy(self.faces['D'])
        b = copy.deepcopy(self.faces['B'])
        r = copy.deepcopy(self.faces['R'])
        l = copy.deepcopy(self.faces['L'])
        self.faces['U'] = f
        self.faces['F'] = d
        self.faces['D'] = [row[::-1] for row in reversed(b)]
        self.faces['B'] = [row[::-1] for row in reversed(u)]
        self.faces['R'] = [
            [r[2][0],r[1][0],r[0][0]],
            [r[2][1],r[1][1],r[0][1]],
            [r[2][2],r[1][2],r[0][2]],
        ]
        self.faces['L'] = [
            [l[0][2],l[1][2],l[2][2]],
            [l[0][1],l[1][1],l[2][1]],
            [l[0][0],l[1][0],l[2][0]],
        ]
        self.moves_history.append("x")

    def rotate_xi(self):
        """Tout le cube tourne comme R'."""
        u = copy.deepcopy(self.faces['U'])
        f = copy.deepcopy(self.faces['F'])
        d = copy.deepcopy(self.faces['D'])
        b = copy.deepcopy(self.faces['B'])
        r = copy.deepcopy(self.faces['R'])
        l = copy.deepcopy(self.faces['L'])
        self.faces['U'] = [row[::-1] for row in reversed(b)]
        self.faces['F'] = u
        self.faces['D'] = f
        self.faces['B'] = [row[::-1] for row in reversed(d)]
        self.faces['R'] = [
            [r[0][2],r[1][2],r[2][2]],
            [r[0][1],r[1][1],r[2][1]],
            [r[0][0],r[1][0],r[2][0]],
        ]
        self.faces['L'] = [
            [l[2][0],l[1][0],l[0][0]],
            [l[2][1],l[1][1],l[0][1]],
            [l[2][2],l[1][2],l[0][2]],
        ]
        self.moves_history.append("x'")

    # ══════════════════════════════════
    #  SHUFFLE — moves externes SEULEMENT
    # ══════════════════════════════════

    def shuffle(self, n: int = 20):
        """
        Mélange avec uniquement des moves de couche externe.
        N'utilise JAMAIS rotate_y/rotate_x pour éviter
        d'invalider les centres.
        """
        pool = [
            ("U",self.move_U),("U'",self.move_Ui),("U2",self.move_U2),
            ("D",self.move_D),("D'",self.move_Di),("D2",self.move_D2),
            ("R",self.move_R),("R'",self.move_Ri),("R2",self.move_R2),
            ("L",self.move_L),("L'",self.move_Li),("L2",self.move_L2),
            ("F",self.move_F),("F'",self.move_Fi),("F2",self.move_F2),
            ("B",self.move_B),("B'",self.move_Bi),("B2",self.move_B2),
        ]
        last_face = None
        count     = 0
        while count < n:
            nm, fn = random.choice(pool)
            face   = nm[0]
            if face == last_face:
                continue
            fn()
            last_face = face
            count    += 1
        self.state = "IDLE"

    # ══════════════════════════════════
    #  DISPATCH
    # ══════════════════════════════════

    def apply_move(self, mv: str):
        TABLE = {
            "U":  self.move_U,   "U'": self.move_Ui,  "U2": self.move_U2,
            "D":  self.move_D,   "D'": self.move_Di,  "D2": self.move_D2,
            "R":  self.move_R,   "R'": self.move_Ri,  "R2": self.move_R2,
            "L":  self.move_L,   "L'": self.move_Li,  "L2": self.move_L2,
            "F":  self.move_F,   "F'": self.move_Fi,  "F2": self.move_F2,
            "B":  self.move_B,   "B'": self.move_Bi,  "B2": self.move_B2,
            "M":  self.move_M,   "M'": self.move_Mi,  "M2": self.move_M2,
            "E":  self.move_E,   "E'": self.move_Ei,
            "S":  self.move_S,   "S'": self.move_Si,
            "y":  self.rotate_y, "y'": self.rotate_yi,
            "x":  self.rotate_x, "x'": self.rotate_xi,
            "Y":  self.rotate_y, "Y'": self.rotate_yi,
            "X":  self.rotate_x, "X'": self.rotate_xi,
        }
        fn = TABLE.get(mv)
        if fn: fn()
        else: print(f"[Cube] Move inconnu: '{mv}'")