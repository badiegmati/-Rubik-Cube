# cube/solver.py
"""
Solveur Rubik's Cube.
Priorité : kociemba (optimal) → BFS → inversion historique.
"""
from __future__ import annotations

import copy
from collections import deque


class CubeSolver:

    # Moves pour BFS (sans couches médianes pour simplifier)
    MOVES_BFS = [
        "U", "U'", "U2",
        "D", "D'", "D2",
        "R", "R'", "R2",
        "L", "L'", "L2",
        "F", "F'", "F2",
        "B", "B'", "B2",
    ]

    MAX_BFS = 5

    def __init__(self):
        self.solution: list[str] = []
        self._idx:     int       = 0
        self.solved:   bool      = False

    def solve(self, cube) -> list[str]:
        if cube.is_solved():
            self.solution = []
            self._idx     = 0
            self.solved   = True
            return []

        self.solved = False
        self._idx   = 0

        # 1. Kociemba (optimal)
        sol = try_kociemba(cube)

        # 2. BFS borné
        if not sol:
            print("[Solver] Kociemba indisponible → BFS")
            sol = self._bfs(cube)

        # 3. Inversion historique
        if not sol:
            print("[Solver] BFS échoué → inversion historique")
            sol = self._inverse(cube)

        self.solution = sol or []
        return self.solution

    def next_move(self) -> str | None:
        if self._idx < len(self.solution):
            mv = self.solution[self._idx]
            self._idx += 1
            return mv
        self.solved = True
        return None

    def has_moves(self) -> bool:
        return self._idx < len(self.solution)

    def reset(self):
        self.solution = []
        self._idx     = 0
        self.solved   = False

    def _bfs(self, cube) -> list[str] | None:
        key  = lambda c: str(c.faces)
        init = cube.copy()
        q    = deque([(init, [])])
        vis  = {key(init)}

        while q:
            cur, moves = q.popleft()
            if len(moves) >= self.MAX_BFS:
                continue
            for mv in self.MOVES_BFS:
                nc = cur.copy()
                nc.apply_move(mv)
                k  = key(nc)
                if k in vis:
                    continue
                vis.add(k)
                nm = moves + [mv]
                if nc.is_solved():
                    print(f"[Solver] BFS trouvé : {nm}")
                    return nm
                q.append((nc, nm))
        return None

    @staticmethod
    def _inverse(cube) -> list[str]:
        INV = {
            "U": "U'", "U'": "U",  "U2": "U2",
            "D": "D'", "D'": "D",  "D2": "D2",
            "R": "R'", "R'": "R",  "R2": "R2",
            "L": "L'", "L'": "L",  "L2": "L2",
            "F": "F'", "F'": "F",  "F2": "F2",
            "B": "B'", "B'": "B",  "B2": "B2",
            "M": "M'", "M'": "M",  "M2": "M2",
            "E": "E'", "E'": "E",  "E2": "E2",
            "S": "S'", "S'": "S",
            "x": "x'", "x'": "x",
            "y": "y'", "y'": "y",
            "z": "z'", "z'": "z",
        }
        sol = [INV.get(m, m)
               for m in reversed(cube.moves_history)]
        print(f"[Solver] Inversion : {len(sol)} moves")
        return sol


def try_kociemba(cube) -> list[str] | None:
    """
    Résout avec kociemba si disponible.
    Ordre faces kociemba : U R F D L B
    Chaque face : 9 stickers de haut-gauche à bas-droite.
    """
    try:
        import kociemba

        # Ordre WCA pour kociemba
        face_order = ['U', 'R', 'F', 'D', 'L', 'B']

        # Mapping : lettre de face → lettre kociemba
        # Le centre de chaque face donne son identité
        center_to_k = {}
        for f in face_order:
            center = cube.faces[f][1][1]
            center_to_k[center] = f

        # Construire la chaîne de 54 caractères
        s = ""
        for f in face_order:
            for r in range(3):
                for c in range(3):
                    cell = cube.faces[f][r][c]
                    k    = center_to_k.get(cell, '?')
                    s   += k

        if '?' in s:
            print(f"[Kociemba] État invalide : {s}")
            return None

        # Résoudre
        result = kociemba.solve(s).strip()
        if not result:
            return []

        # Parser le résultat
        # kociemba retourne : "R U R' U' ..." avec notation standard
        raw_moves = result.split()
        moves     = []
        for m in raw_moves:
            # Convertir "R2" "U'" etc. directement
            moves.append(m)

        print(f"[Kociemba] Solution : {moves}")
        return moves

    except ImportError:
        return None
    except Exception as e:
        print(f"[Kociemba] Erreur : {e}")
        return None