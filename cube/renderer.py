# cube/renderer.py
from __future__ import annotations
from typing import Optional

import cv2, math, time
import numpy as np


# ══════════════════════════════════════════════════════
#  COULEURS
# ══════════════════════════════════════════════════════

FACE_COLORS = {
    'U': np.array([255,255,255],np.float32),
    'D': np.array([  0,215,215],np.float32),
    'F': np.array([  0,  0,220],np.float32),
    'B': np.array([  0,130,255],np.float32),
    'L': np.array([  0,200,  0],np.float32),
    'R': np.array([220,  0,  0],np.float32),
    '?': np.array([ 35, 35, 35],np.float32),
}

NORMALS = {
    'F': np.array([ 0, 0, 1],float),
    'B': np.array([ 0, 0,-1],float),
    'R': np.array([ 1, 0, 0],float),
    'L': np.array([-1, 0, 0],float),
    'U': np.array([ 0, 1, 0],float),
    'D': np.array([ 0,-1, 0],float),
}

FACE_CFG = {
    'F': (np.array([-1.5, 1.5, 1.5],float),
          np.array([ 1.0, 0.0, 0.0],float),
          np.array([ 0.0,-1.0, 0.0],float)),
    'B': (np.array([ 1.5, 1.5,-1.5],float),
          np.array([-1.0, 0.0, 0.0],float),
          np.array([ 0.0,-1.0, 0.0],float)),
    'R': (np.array([ 1.5, 1.5, 1.5],float),
          np.array([ 0.0, 0.0,-1.0],float),
          np.array([ 0.0,-1.0, 0.0],float)),
    'L': (np.array([-1.5, 1.5,-1.5],float),
          np.array([ 0.0, 0.0, 1.0],float),
          np.array([ 0.0,-1.0, 0.0],float)),
    'U': (np.array([-1.5, 1.5,-1.5],float),
          np.array([ 1.0, 0.0, 0.0],float),
          np.array([ 0.0, 0.0, 1.0],float)),
    'D': (np.array([-1.5,-1.5, 1.5],float),
          np.array([ 1.0, 0.0, 0.0],float),
          np.array([ 0.0, 0.0,-1.0],float)),
}


def _build_quads():
    res = {}
    for face,(o,vc,vr) in FACE_CFG.items():
        q = np.zeros((9,4,3),float)
        i = 0
        for row in range(3):
            for col in range(3):
                q[i,0]=o+col*vc      +row*vr
                q[i,1]=o+(col+1)*vc  +row*vr
                q[i,2]=o+(col+1)*vc  +(row+1)*vr
                q[i,3]=o+col*vc      +(row+1)*vr
                i+=1
        res[face]=q
    return res

QUADS = _build_quads()


# ══════════════════════════════════════════════════════
#  MAPPING DRAG → MOVE
# ══════════════════════════════════════════════════════

def drag_to_move(face:str, row:int, col:int,
                 dx:float, dy:float) -> Optional[str]:
    if abs(dx)<8 and abs(dy)<8:
        return None
    h = abs(dx)>=abs(dy)
    R = dx>0; D = dy>0

    if face=='F':
        if h:
            return ["D'","E'","U"][row] if R else ["D","E","U'"][row]
        else:
            return ["L","M","R'"][col] if D else ["L'","M'","R"][col]
    if face=='B':
        if h:
            return ["D","E","U'"][row] if R else ["D'","E'","U"][row]
        else:
            return ["R","M'","L'"][col] if D else ["R'","M","L"][col]
    if face=='R':
        if h:
            return ["D'","E'","U"][row] if R else ["D","E","U'"][row]
        else:
            return "R'" if D else "R"
    if face=='L':
        if h:
            return ["D","E","U'"][row] if R else ["D'","E'","U"][row]
        else:
            return "L" if D else "L'"
    if face=='U':
        if h:
            return "y" if R else "y'"
        else:
            return ["L","M","R'"][col] if D else ["L'","M'","R"][col]
    if face=='D':
        if h:
            return "y'" if R else "y"
        else:
            return ["L'","M'","R"][col] if D else ["L","M","R'"][col]
    return None


# ══════════════════════════════════════════════════════
#  PARTICULES
# ══════════════════════════════════════════════════════

class Particle:
    __slots__=['x','y','vx','vy','life','ml','col','sz','g']
    def __init__(self,x,y,col):
        a=np.random.uniform(0,2*math.pi)
        s=np.random.uniform(1.5,4.5)
        self.x,self.y=float(x),float(y)
        self.vx,self.vy=math.cos(a)*s,math.sin(a)*s
        self.life=1.0; self.ml=np.random.uniform(0.6,1.4)
        self.col=col; self.sz=np.random.randint(2,5)
        self.g=np.random.uniform(0.05,0.12)
    def update(self,dt):
        self.x+=self.vx*dt*60; self.y+=self.vy*dt*60
        self.vy+=self.g; self.life-=dt/self.ml
        return self.life>0
    def draw(self,frame):
        if self.life<=0: return
        a=max(0.,self.life)
        c=tuple(int(v*a) for v in self.col)
        cv2.circle(frame,(int(self.x),int(self.y)),
                   max(1,int(self.sz*a)),c,-1,cv2.LINE_AA)

class Particles:
    def __init__(self):
        self._p=[]; self._t=time.perf_counter()
    def burst(self,x,y,col,n=14):
        for _ in range(n):
            c=tuple(min(255,max(0,int(v+np.random.randint(-20,20))))
                    for v in col)
            self._p.append(Particle(x,y,c))
    def ring(self,cx,cy,r,col,n=24):
        for i in range(n):
            a=2*math.pi*i/n
            self.burst(cx+int(math.cos(a)*r),
                       cy+int(math.sin(a)*r),col,2)
    def draw(self,frame):
        now=time.perf_counter()
        dt=min(now-self._t,0.05); self._t=now
        self._p=[p for p in self._p if p.update(dt)]
        for p in self._p: p.draw(frame)


# ══════════════════════════════════════════════════════
#  RENDERER
# ══════════════════════════════════════════════════════

class CubeRenderer:

    LIGHT = np.array([0.5,0.8,1.0],float)
    LIGHT /= np.linalg.norm(LIGHT)

    def __init__(self,W=1280,H=720):
        self.W=W; self.H=H
        self.ax=25.0; self.ay=45.0
        self.cell=max(30,min(W,H)//9)
        self.cx=int(W*0.62); self.cy=int(H*0.46)
        self._tx=self.ax; self._ty=self.ay
        self._pts:dict[str,np.ndarray]={}
        self._hover:Optional[tuple]=None
        self._flash=0.0
        self._pulse=0.0; self._was_solved=False
        self._fx=0.0    # flash à chaque move souris
        self._particles=Particles()
        self._vign=self._make_vign(W,H)
        self._M=self._mat()

        # État drag
        self._dp=False   # drag pending
        self._ds=False   # drag on sticker
        self._df:Optional[str]=None
        self._dr=0; self._dc=0
        self._dsx=0; self._dsy=0

        print(f"[Renderer] {W}×{H} "
              f"cx={self.cx} cy={self.cy} "
              f"cell={self.cell}px")

    # ── Vignette ────────────────────────────────────

    @staticmethod
    def _make_vign(W,H):
        cx,cy=W/2,H/2
        Y,X=np.ogrid[:H,:W]
        d=np.sqrt(((X-cx)/W)**2+((Y-cy)/H)**2)
        v=np.clip((d-0.28)/0.52,0,1)*0.58
        return v[:,:,np.newaxis].astype(np.float32)

    def _vign_apply(self,frame):
        f=frame.astype(np.float32)*(1-self._vign)
        return np.clip(f,0,255).astype(np.uint8)

    # ── Matrices ────────────────────────────────────

    def _mat(self):
        ry=math.radians(self.ay); rx=math.radians(self.ax)
        cy_,sy_=math.cos(ry),math.sin(ry)
        cx_,sx_=math.cos(rx),math.sin(rx)
        Ry=np.array([[cy_,0,sy_],[0,1,0],[-sy_,0,cy_]])
        Rx=np.array([[1,0,0],[0,cx_,-sx_],[0,sx_,cx_]])
        return Rx@Ry

    def _proj(self,pts):
        r=pts@self._M.T
        px=( r[...,0]*self.cell+self.cx).astype(np.int32)
        py=(-r[...,1]*self.cell+self.cy).astype(np.int32)
        return np.stack([px,py],axis=-1)

    # ── Visibilité ──────────────────────────────────

    def _visible(self):
        res=[]
        for f,n in NORMALS.items():
            nc=self._M@n; dot=float(nc[2])
            if dot<=0.01: continue
            diff=max(0.,float(np.dot(n,self.LIGHT)))
            lgt=min(1.,0.30+0.60*diff)
            res.append((f,dot,lgt))
        res.sort(key=lambda x:x[1])
        return res

    # ── Hit test ────────────────────────────────────

    def hit_test(self,mx,my)->Optional[tuple]:
        for f,_,_ in reversed(self._visible()):
            if f not in self._pts: continue
            pts_f=self._pts[f]
            for i in range(9):
                c=pts_f[i].mean(0)
                inn=(pts_f[i]-c)*0.86+c
                if self._in_quad(mx,my,inn.astype(float)):
                    return (f,i//3,i%3)
        return None

    @staticmethod
    def _in_quad(px,py,q)->bool:
        n=len(q)
        for i in range(n):
            ax,ay=q[i]; bx,by=q[(i+1)%n]
            if (bx-ax)*(py-ay)-(by-ay)*(px-ax)<0:
                return False
        return True

    # ── Dessin face ─────────────────────────────────

    def _draw_face(self,frame,face,data,lgt):
        q2=self._proj(QUADS[face])
        self._pts[face]=q2
        t=time.time()
        for i in range(9):
            row=i//3; col=i%3
            pts=q2[i]
            cv2.fillConvexPoly(frame,pts,(8,8,8))
            key=data[row][col]
            base=FACE_COLORS.get(key,FACE_COLORS['?'])
            c_arr=np.clip(base*lgt,0,255).astype(np.uint8)
            c=(int(c_arr[0]),int(c_arr[1]),int(c_arr[2]))
            ctr=pts.mean(0)
            inn=((pts-ctr)*0.86+ctr).astype(np.int32)
            is_hov=(self._hover==(face,row,col))
            if is_hov:
                br=np.clip(base*min(1.,lgt*1.4),0,255
                           ).astype(np.uint8)
                bc=(int(br[0]),int(br[1]),int(br[2]))
                cv2.fillConvexPoly(frame,inn,bc)
                cv2.polylines(frame,[inn],True,
                              (255,255,255),2,cv2.LINE_AA)
            else:
                cv2.fillConvexPoly(frame,inn,c)
            # Reflet
            sh=((pts-ctr)*0.34+ctr+np.array([-2.,-2.])
                ).astype(np.int32)
            sa=min(0.22,lgt*0.28)
            if sa>0.04 and key!='?':
                sc=tuple(int(255*sa) for _ in range(3))
                cv2.fillConvexPoly(frame,sh,sc)

    # ── Ombre ───────────────────────────────────────

    def _draw_shadow(self,frame):
        sx=self.cx+int(self.cell*0.32)
        sy=self.cy+int(self.cell*2.30)
        aw=max(1,int(self.cell*2.4))
        ah=max(1,int(self.cell*0.45))
        if (sx-aw<0 or sx+aw>=self.W or
                sy-ah<0 or sy+ah>=self.H): return
        ov=frame.copy()
        cv2.ellipse(ov,(sx,sy),(aw,ah),0,0,360,(0,0,0),-1)
        cv2.addWeighted(ov,0.25,frame,0.75,0,frame)

    # ── Contour ─────────────────────────────────────

    def _draw_outline(self,frame):
        c3=np.array([
            [-1.5,-1.5,-1.5],[1.5,-1.5,-1.5],
            [ 1.5, 1.5,-1.5],[-1.5,1.5,-1.5],
            [-1.5,-1.5, 1.5],[1.5,-1.5, 1.5],
            [ 1.5, 1.5, 1.5],[-1.5,1.5, 1.5],
        ],float)
        edges=[(0,1),(1,2),(2,3),(3,0),
               (4,5),(5,6),(6,7),(7,4),
               (0,4),(1,5),(2,6),(3,7)]
        p=self._proj(c3)
        for a,b in edges:
            cv2.line(frame,tuple(p[a]),tuple(p[b]),
                     (50,50,50),1,cv2.LINE_AA)

    # ── Effets ──────────────────────────────────────

    def trigger_flash(self,intensity=1.0):
        self._flash=intensity

    def trigger_move_flash(self):
        self._fx=0.5

    def _apply_flash(self,frame):
        if self._flash>0:
            w=np.ones_like(frame,np.uint8)*255
            cv2.addWeighted(w,self._flash*0.40,
                            frame,1-self._flash*0.40,0,frame)
            self._flash=max(0.,self._flash-0.07)
        if self._fx>0:
            w=np.ones_like(frame,np.uint8)*255
            cv2.addWeighted(w,self._fx*0.25,
                            frame,1-self._fx*0.25,0,frame)
            self._fx=max(0.,self._fx-0.10)

    def _update_solved(self,frame,cube):
        s=cube.is_solved()
        if s and not self._was_solved:
            self._pulse=1.0
            cols=[(0,0,220),(0,130,255),(240,240,240),
                  (0,215,215),(0,200,0),(220,0,0)]
            r=int(self.cell*1.5)
            for c in cols:
                self._particles.ring(self.cx,self.cy,r,c,8)
        self._was_solved=s
        if s and self._pulse>0.005:
            self._pulse=max(0.,self._pulse-0.015)
            pr=int(self.cell*2.8+self._pulse*self.cell*0.7)
            gv=int(150*self._pulse*(0.7+0.3*math.sin(time.time()*8)))
            ov=frame.copy()
            cv2.circle(ov,(self.cx,self.cy),pr,(0,gv,0),
                       max(1,int(4*self._pulse)),cv2.LINE_AA)
            cv2.addWeighted(ov,self._pulse*0.40,
                            frame,1-self._pulse*0.40,0,frame)

    # ── RENDU PRINCIPAL ─────────────────────────────

    def render(self,frame,cube):
        L=0.14
        self.ax+=(self._tx-self.ax)*L
        self.ay+=(self._ty-self.ay)*L
        self._M=self._mat()

        frame=self._vign_apply(frame)
        self._draw_shadow(frame)
        for f,_,lgt in self._visible():
            self._draw_face(frame,f,cube.faces[f],lgt)
        self._draw_outline(frame)
        self._update_solved(frame,cube)
        self._particles.draw(frame)
        self._apply_flash(frame)
        return frame

    # ── API SOURIS ───────────────────────────────────

    def hover(self,mx,my):
        self._hover=self.hit_test(mx,my)

    def press(self,mx,my)->bool:
        self._dsx,self._dsy=mx,my
        self._dp=True
        hit=self.hit_test(mx,my)
        if hit:
            self._ds=True
            self._df,self._dr,self._dc=hit
            return True
        self._ds=False; self._df=None
        return False

    def release(self,mx,my)->Optional[str]:
        if not self._dp: return None
        self._dp=False
        dx=mx-self._dsx; dy=my-self._dsy
        if self._ds and self._df:
            self._ds=False
            mv=drag_to_move(self._df,self._dr,self._dc,dx,dy)
            f_=self._df; self._df=None
            if mv:
                print(f"[Mouse] {f_}[{self._dr},"
                      f"{self._dc}] ({dx:+d},{dy:+d}) → {mv}")
                self.trigger_move_flash()
            return mv
        return None

    def drag_orbit(self,dx,dy):
        if not self._ds:
            self._ty=(self._ty+dx*0.35)%360
            self._tx=max(-85,min(85,self._tx-dy*0.35))

    # ── Contrôles ────────────────────────────────────

    def rotate_view(self,dx=0,dy=0):
        self._ty=(self._ty+dx)%360
        self._tx=max(-85,min(85,self._tx+dy))

    def auto_rotate(self,speed=0.25):
        self._ty=(self._ty+speed)%360

    def zoom(self,d):
        self.cell=max(30,min(200,self.cell+d))
        print(f"[Renderer] zoom={self.cell}px")

    # ── État (lecture externe) ───────────────────────

    @property
    def dragging(self) -> bool:
        """True tant qu'un drag est en cours sur un sticker (rotation de face)."""
        return self._ds

    @property
    def grabbed_face(self):
        """Face ('U','D','F','B','L','R') actuellement attrapée, ou None."""
        return self._df