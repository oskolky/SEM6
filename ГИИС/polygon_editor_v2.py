"""
Polygon Graphics Editor v3
==========================
Лаб. 1 : Линии (Брезенхем)
Лаб. 2 : Полигоны — выпуклость, нормали, оболочки Грэхема/Джарвиса,
          пересечения, принадлежность точки
Лаб. 3 : Алгоритмы заполнения (ET, AEL, простая затравка, построчная затравка)
          + режим отладки с пошаговым выводом
Лаб. 4 : Триангуляция Делоне (Bowyer–Watson) и диаграмма Вороного
"""

import tkinter as tk
from tkinter import messagebox
import math
from collections import defaultdict


# ═══════════════════════════════════════════════════════════════════
#  GEOMETRY HELPERS
# ═══════════════════════════════════════════════════════════════════

def cross2d(o, a, b):
    return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])

def dist(a, b):
    return math.hypot(b[0]-a[0], b[1]-a[1])

def normalize(v):
    n = math.hypot(v[0], v[1])
    return (0,0) if n < 1e-9 else (v[0]/n, v[1]/n)

def segment_intersect(p1, p2, p3, p4):
    d1 = (p2[0]-p1[0], p2[1]-p1[1])
    d2 = (p4[0]-p3[0], p4[1]-p3[1])
    cross = d1[0]*d2[1] - d1[1]*d2[0]
    if abs(cross) < 1e-9:
        return None
    t = ((p3[0]-p1[0])*d2[1] - (p3[1]-p1[1])*d2[0]) / cross
    u = ((p3[0]-p1[0])*d1[1] - (p3[1]-p1[1])*d1[0]) / cross
    if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
        return (p1[0]+t*d1[0], p1[1]+t*d1[1])
    return None

def point_in_polygon(point, polygon):
    if len(polygon) < 3:
        return False
    x, y = point
    inside = False
    px, py = polygon[-1]
    for cx, cy in polygon:
        if ((cy > y) != (py > y)) and (x < (px-cx)*(y-cy)/(py-cy+1e-12)+cx):
            inside = not inside
        px, py = cx, cy
    return inside

def is_convex(polygon):
    n = len(polygon)
    if n < 3:
        return False
    sign = None
    for i in range(n):
        c = cross2d(polygon[i], polygon[(i+1)%n], polygon[(i+2)%n])
        if abs(c) < 1e-9:
            continue
        s = 1 if c > 0 else -1
        if sign is None:
            sign = s
        elif sign != s:
            return False
    return True

def inward_normals(polygon):
    n = len(polygon)
    area = sum(cross2d(polygon[0], polygon[i], polygon[(i+1)%n]) for i in range(1,n-1))
    normals = []
    for i in range(n):
        a, b = polygon[i], polygon[(i+1)%n]
        dx, dy = b[0]-a[0], b[1]-a[1]
        nx, ny = (dy,-dx) if area > 0 else (-dy, dx)
        normals.append(normalize((nx, ny)))
    return normals


# ═══════════════════════════════════════════════════════════════════
#  CONVEX HULL
# ═══════════════════════════════════════════════════════════════════

def graham_scan(points):
    pts = list(set(points))
    if len(pts) < 3:
        return pts
    pivot = min(pts, key=lambda p: (p[1], p[0]))
    pts.sort(key=lambda p: (math.atan2(p[1]-pivot[1], p[0]-pivot[0]), dist(pivot,p)))
    hull = []
    for p in pts:
        while len(hull) >= 2 and cross2d(hull[-2], hull[-1], p) <= 0:
            hull.pop()
        hull.append(p)
    return hull

def jarvis_march(points):
    pts = list(set(points))
    if len(pts) < 3:
        return pts
    current = min(pts, key=lambda p: (p[0], p[1]))
    hull = []
    while True:
        hull.append(current)
        nxt = pts[0]
        for p in pts[1:]:
            c = cross2d(current, nxt, p)
            if c < 0 or (abs(c) < 1e-9 and dist(current,p) > dist(current,nxt)):
                nxt = p
        current = nxt
        if current == hull[0]:
            break
    return hull


# ═══════════════════════════════════════════════════════════════════
#  BRESENHAM
# ═══════════════════════════════════════════════════════════════════

def bresenham(x0, y0, x1, y1):
    pts = []
    dx, dy = abs(x1-x0), abs(y1-y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2*err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy
    return pts


# ═══════════════════════════════════════════════════════════════════
#  FILL ALGORITHMS
# ═══════════════════════════════════════════════════════════════════

def _poly_bounds(polygon):
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    return int(min(xs)), int(max(xs)), int(min(ys)), int(max(ys))

def fill_scanline_et(polygon, fill_color, debug=False):
    if len(polygon) < 3:
        return
    _, _, ymin, ymax = _poly_bounds(polygon)
    n = len(polygon)
    ET = defaultdict(list)
    for i in range(n):
        x0, y0 = polygon[i]
        x1, y1 = polygon[(i+1)%n]
        if y0 == y1:
            continue
        if y0 > y1:
            x0, y0, x1, y1 = x1, y1, x0, y0
        ET[int(y0)].append([float(x0), (x1-x0)/(y1-y0), int(y1)])
    AEL = []
    spans_all = []
    for y in range(ymin, ymax+1):
        AEL += ET.get(y, [])
        AEL = [e for e in AEL if e[2] > y]
        AEL.sort(key=lambda e: e[0])
        spans_y = []
        for k in range(0, len(AEL)-1, 2):
            xl = int(math.ceil(AEL[k][0]))
            xr = int(math.floor(AEL[k+1][0]))
            if xl <= xr:
                spans_y.append((xl, xr, y))
        spans_all.extend(spans_y)
        if debug:
            info = "  ".join(f"x={e[0]:.1f} ymax={e[2]}" for e in AEL)
            yield spans_y, y, f"y={y}  AEL=[{info}]"
        for e in AEL:
            e[0] += e[1]
    if not debug:
        yield spans_all, -1, ""

def fill_scanline_ael(polygon, fill_color, debug=False):
    yield from fill_scanline_et(polygon, fill_color, debug)

def fill_flood_simple(polygon, seed, cw, ch, debug=False):
    if not point_in_polygon(seed, polygon):
        yield set(), -1, "Затравка вне полигона!"
        return
    visited = set()
    stack = [seed]
    batch = []
    step = 0
    while stack:
        x, y = stack.pop()
        if (x,y) in visited:
            continue
        if not (0<=x<cw and 0<=y<ch):
            continue
        if not point_in_polygon((x,y), polygon):
            continue
        visited.add((x,y))
        batch.append((x,y))
        for nx, ny in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
            if (nx,ny) not in visited:
                stack.append((nx,ny))
        if debug and len(batch) >= 40:
            step += 1
            yield set(batch), step, f"Шаг {step}: {len(visited)} пикс."
            batch = []
    if batch:
        step += 1
        yield set(batch), step, f"Шаг {step}: итого {len(visited)} пикс."
    if not debug:
        yield visited, -1, ""

def fill_flood_scanline(polygon, seed, cw, ch, debug=False):
    if not point_in_polygon(seed, polygon):
        yield set(), -1, "Затравка вне полигона!"
        return
    visited = set()
    stack = [seed]
    step = 0
    while stack:
        sx, sy = stack.pop()
        if (sx,sy) in visited or not point_in_polygon((sx,sy), polygon):
            continue
        xl = sx
        while xl-1>=0 and (xl-1,sy) not in visited and point_in_polygon((xl-1,sy), polygon):
            xl -= 1
        xr = sx
        while xr+1<cw and (xr+1,sy) not in visited and point_in_polygon((xr+1,sy), polygon):
            xr += 1
        span = set()
        for x in range(xl, xr+1):
            if (x,sy) not in visited:
                visited.add((x,sy))
                span.add((x,sy))
        for ry in (sy-1, sy+1):
            if 0 <= ry < ch:
                in_s = False
                for x in range(xl, xr+1):
                    inside = point_in_polygon((x,ry),polygon) and (x,ry) not in visited
                    if inside and not in_s:
                        stack.append((x,ry))
                        in_s = True
                    elif not inside:
                        in_s = False
        if debug and span:
            step += 1
            yield span, step, f"Строка y={sy}  x=[{xl}..{xr}]  итого {len(visited)} пикс."
    if not debug:
        yield visited, -1, ""


# ═══════════════════════════════════════════════════════════════════
#  DELAUNAY TRIANGULATION  (Bowyer–Watson)
# ═══════════════════════════════════════════════════════════════════

def _circumcircle(a, b, c):
    """Circumscribed circle of triangle abc → (cx, cy, r²) or None."""
    ax, ay = a
    bx, by = b
    cx, cy = c
    D = 2*(ax*(by-cy) + bx*(cy-ay) + cx*(ay-by))
    if abs(D) < 1e-10:
        return None
    ux = ((ax*ax+ay*ay)*(by-cy) + (bx*bx+by*by)*(cy-ay) + (cx*cx+cy*cy)*(ay-by)) / D
    uy = ((ax*ax+ay*ay)*(cx-bx) + (bx*bx+by*by)*(ax-cx) + (cx*cx+cy*cy)*(bx-ax)) / D
    r2 = (ax-ux)**2 + (ay-uy)**2
    return ux, uy, r2

def _in_circumcircle(tri_pts, p):
    cc = _circumcircle(*tri_pts)
    if cc is None:
        return False
    ux, uy, r2 = cc
    return (p[0]-ux)**2 + (p[1]-uy)**2 < r2 - 1e-10

def delaunay(points):
    """
    Bowyer–Watson incremental Delaunay triangulation.
    Returns (triangles, circumcenters).
    triangles  = list of (i,j,k) index tuples into `points`.
    circumcenters = list of (cx,cy) for each triangle (or None).
    """
    pts = list(points)
    n = len(pts)
    if n < 3:
        return [], []

    # Super-triangle enclosing all points
    minx = min(p[0] for p in pts); maxx = max(p[0] for p in pts)
    miny = min(p[1] for p in pts); maxy = max(p[1] for p in pts)
    dmax = max(maxx-minx, maxy-miny) * 4
    mx = (minx+maxx)/2;  my = (miny+maxy)/2
    sp = [(mx, my-2*dmax), (mx-2*dmax, my+dmax), (mx+2*dmax, my+dmax)]
    all_pts = pts + sp
    super_idx = {n, n+1, n+2}

    triangles = [frozenset([n, n+1, n+2])]

    for i, p in enumerate(pts):
        bad = [tri for tri in triangles
               if _in_circumcircle([all_pts[j] for j in tri], p)]

        edge_count = defaultdict(int)
        for tri in bad:
            t = list(tri)
            for a, b in [(t[0],t[1]), (t[1],t[2]), (t[0],t[2])]:
                edge_count[frozenset([a,b])] += 1
        boundary = [e for e, cnt in edge_count.items() if cnt == 1]

        for tri in bad:
            triangles.remove(tri)
        for edge in boundary:
            e = list(edge)
            triangles.append(frozenset([e[0], e[1], i]))

    result = [tuple(tri) for tri in triangles if not (tri & super_idx)]

    circumcenters = []
    for tri in result:
        cc = _circumcircle(*[all_pts[j] for j in tri])
        circumcenters.append((cc[0], cc[1]) if cc else None)

    return result, circumcenters


# ═══════════════════════════════════════════════════════════════════
#  VORONOI  (dual graph of Delaunay)
# ═══════════════════════════════════════════════════════════════════

def voronoi_edges(triangles, circumcenters, points, canvas_w, canvas_h):
    """
    Build Voronoi diagram edges as list of (x0,y0,x1,y1).
    Interior edges: connect circumcenters of adjacent triangles.
    Boundary edges: extend circumcenter ray outward to canvas edge.
    """
    edges = []
    edge_to_tri = defaultdict(list)
    for i, tri in enumerate(triangles):
        t = list(tri)
        for a, b in [(t[0],t[1]), (t[1],t[2]), (t[0],t[2])]:
            edge_to_tri[frozenset([a,b])].append(i)

    visited = set()
    for key, tris in edge_to_tri.items():
        fk = frozenset(key)
        if fk in visited:
            continue
        visited.add(fk)

        if len(tris) == 2:
            i, j = tris
            c1, c2 = circumcenters[i], circumcenters[j]
            if c1 and c2:
                edges.append((c1[0], c1[1], c2[0], c2[1]))
        elif len(tris) == 1:
            i = tris[0]
            c = circumcenters[i]
            if c is None:
                continue
            e = list(key)
            p0, p1 = points[e[0]], points[e[1]]
            # midpoint of boundary edge
            mx, my = (p0[0]+p1[0])/2, (p0[1]+p1[1])/2
            # direction from circumcenter toward midpoint (outward)
            dx, dy = mx-c[0], my-c[1]
            n2 = math.hypot(dx, dy)
            if n2 < 1e-9:
                continue
            t_max = max(canvas_w, canvas_h) * 3
            x2 = c[0] - dx/n2 * t_max
            y2 = c[1] - dy/n2 * t_max
            edges.append((c[0], c[1], x2, y2))

    return edges


# ═══════════════════════════════════════════════════════════════════
#  DEBUG PANEL
# ═══════════════════════════════════════════════════════════════════

class DebugPanel(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Отладка алгоритма")
        self.configure(bg="#111111")
        self.geometry("540x480+900+80")
        self.resizable(True, True)

        tk.Label(self, text="⚙ ПОШАГОВАЯ ОТЛАДКА",
                 bg="#111111", fg="#00ff99",
                 font=("Courier", 11, "bold")).pack(pady=(10,4))

        self.step_var = tk.StringVar(value="Шаг: —")
        tk.Label(self, textvariable=self.step_var,
                 bg="#111111", fg="#aaaaaa",
                 font=("Courier", 9)).pack()

        frm = tk.Frame(self, bg="#111111")
        frm.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
        self.log = tk.Text(frm, bg="#0a0a0a", fg="#00ff99",
                           font=("Courier", 9), relief="flat", wrap=tk.WORD)
        sb = tk.Scrollbar(frm, command=self.log.yview, bg="#222222")
        self.log.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.log.pack(fill=tk.BOTH, expand=True)

        ctrl = tk.Frame(self, bg="#111111")
        ctrl.pack(pady=8)
        self.btn_next = tk.Button(ctrl, text="▶ Шаг",
                                  bg="#1a3a1a", fg="#00ff99",
                                  font=("Courier", 9, "bold"),
                                  relief="flat", padx=12, pady=5,
                                  command=self._next_step)
        self.btn_next.pack(side=tk.LEFT, padx=6)
        self.btn_run = tk.Button(ctrl, text="⏩ Всё",
                                 bg="#1a1a3a", fg="#aaaaff",
                                 font=("Courier", 9),
                                 relief="flat", padx=12, pady=5,
                                 command=self._run_all)
        self.btn_run.pack(side=tk.LEFT, padx=6)
        tk.Button(ctrl, text="✕ Закрыть",
                  bg="#3a1a1a", fg="#ff6666",
                  font=("Courier", 9),
                  relief="flat", padx=10, pady=5,
                  command=self.destroy).pack(side=tk.LEFT, padx=6)

        self._gen = None
        self._cb = None
        self._done = False
        self._n = 0

    def attach(self, generator, callback):
        self._gen = generator
        self._cb = callback
        self._done = False
        self._n = 0
        self.log.delete("1.0", tk.END)
        self.step_var.set("Шаг: готов")
        self.btn_next.configure(state=tk.NORMAL)
        self.btn_run.configure(state=tk.NORMAL)
        self.log_msg("Готов. Нажмите ▶ Шаг.\n")

    def log_msg(self, t):
        self.log.insert(tk.END, t+"\n")
        self.log.see(tk.END)

    def _next_step(self):
        if self._done or self._gen is None:
            return
        try:
            pixels, y, msg = next(self._gen)
            self._n += 1
            self.step_var.set(f"Шаг: {self._n}")
            self.log_msg(f"[{self._n:>4}] {msg}")
            if self._cb:
                self._cb(pixels, y, msg)
        except StopIteration:
            self._done = True
            self.btn_next.configure(state=tk.DISABLED)
            self.log_msg("✔ Завершено.")
            self.step_var.set(f"Готово — {self._n} шагов")

    def _run_all(self):
        while not self._done:
            self._next_step()
            self.update_idletasks()


# ═══════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════

class PolygonEditor:
    FILL_ALGOS = [
        ("ET",    "Развертка ET"),
        ("AEL",   "Развертка AEL"),
        ("Flood", "Затравка (стек)"),
        ("Scan",  "Затравка (строч.)"),
    ]

    C = {
        "bg":        "#000000",
        "canvas":    "#000000",
        "grid":      "#1e1e1e",
        "polygon":   "#ffffff",
        "hull_g":    "#dddddd",
        "hull_j":    "#999999",
        "normal":    "#666666",
        "line":      "#ffffff",
        "intersect": "#ff2222",
        "pt_in":     "#00ff99",
        "pt_out":    "#ff3333",
        "vertex":    "#ffffff",
        "preview":   "#555555",
        "tb":        "#0f0f0f",
        "tb2":       "#0a0a16",
        "tb3":       "#060f06",
        "btn_act":   "#2a2a2a",
        "accent":    "#ffffff",
        "txt":       "#cccccc",
        # fill colors
        "f_et":      "#3366ff",
        "f_ael":     "#33ffcc",
        "f_flood":   "#ff9933",
        "f_scan":    "#ff33aa",
        "dbg_step":  "#ffff00",
        # delaunay/voronoi
        "delaunay":  "#2255aa",
        "voronoi":   "#aa2255",
        "circum":    "#1a4422",
        "site":      "#ffdd00",
        "tri_fill":  "#050d1a",
    }

    def __init__(self, root):
        self.root = root
        self.root.title("Polygon Editor v3  |  Делоне & Вороной")
        self.root.configure(bg=self.C["bg"])
        self.root.geometry("1440x900")

        self.current_tool   = tk.StringVar(value="Polygon")
        self.fill_algo      = tk.StringVar(value="ET")
        self.debug_mode     = tk.BooleanVar(value=False)
        self.show_normals   = tk.BooleanVar(value=False)
        self.show_grid      = tk.BooleanVar(value=True)
        self.snap_to_grid   = tk.BooleanVar(value=False)
        self.show_delaunay  = tk.BooleanVar(value=True)
        self.show_voronoi   = tk.BooleanVar(value=True)
        self.show_circum    = tk.BooleanVar(value=False)
        self.show_sites     = tk.BooleanVar(value=True)
        self.grid_size      = 20

        self.polygon_points = []
        self.polygons       = []
        self.line_points    = []
        self.lines          = []
        self.hull_polygon   = None
        self.hull_method    = None
        self.check_point    = None
        self.intersections  = []
        self.preview_pos    = None
        self.seed_point     = None

        self.dv_points       = []
        self.dv_triangles    = []
        self.dv_circumcenters = []
        self.dv_voronoi_edges = []

        self._debug_panel   = None
        self._fill_pixels   = {}

        self._build_ui()
        self._draw_grid()

    # ─────────────────────────────────────────────────────────────
    #  UI
    # ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_menu()
        self._build_toolbar()
        self._build_fill_toolbar()
        self._build_dv_toolbar()
        self._build_canvas()
        self._build_statusbar()

    def _mk_menu(self, parent):
        return tk.Menu(parent, tearoff=0,
                       bg=self.C["tb"], fg=self.C["txt"],
                       activebackground=self.C["btn_act"],
                       activeforeground=self.C["accent"])

    def _build_menu(self):
        bar = tk.Menu(self.root, bg=self.C["tb"], fg=self.C["txt"],
                      activebackground=self.C["btn_act"],
                      activeforeground=self.C["accent"],
                      relief="flat", bd=0)
        self.root.config(menu=bar)

        fm = self._mk_menu(bar)
        bar.add_cascade(label="Файл", menu=fm)
        fm.add_command(label="Очистить всё",            command=self._clear_all)
        fm.add_command(label="Очистить Делоне/Вороной", command=self._clear_dv)
        fm.add_separator()
        fm.add_command(label="Выход", command=self.root.quit)

        pm = self._mk_menu(bar)
        bar.add_cascade(label="Построение полигонов", menu=pm)
        pm.add_command(label="Новый полигон",    command=lambda: self._sel_tool("Polygon"))
        pm.add_command(label="Закрыть полигон",  command=self._close_polygon)
        pm.add_separator()
        pm.add_command(label="Оболочка Грэхем",  command=lambda: self._run_hull("Graham"))
        pm.add_command(label="Оболочка Джарвис", command=lambda: self._run_hull("Jarvis"))
        pm.add_separator()
        pm.add_command(label="Проверить выпуклость", command=self._check_convexity)
        pm.add_checkbutton(label="Нормали", variable=self.show_normals,
                           command=self._redraw_all)

        alm = self._mk_menu(bar)
        bar.add_cascade(label="Алгоритмы заполнения полигонов", menu=alm)
        for key, lbl in self.FILL_ALGOS:
            alm.add_radiobutton(label=lbl, variable=self.fill_algo, value=key)
        alm.add_separator()
        alm.add_command(label="Залить",             command=self._fill_selected)
        alm.add_separator()
        alm.add_checkbutton(label="Режим отладки",  variable=self.debug_mode)
        alm.add_command(label="Панель отладки",     command=self._open_debug_panel)

        dvm = self._mk_menu(bar)
        bar.add_cascade(label="Делоне & Вороной", menu=dvm)
        dvm.add_command(label="Инструмент: добавить точки",   command=lambda: self._sel_tool("DVPoint"))
        dvm.add_separator()
        dvm.add_command(label="Построить триангуляцию Делоне",command=self._run_delaunay)
        dvm.add_command(label="Построить диаграмму Вороного", command=self._run_voronoi)
        dvm.add_command(label="Построить оба",                command=self._run_both)
        dvm.add_separator()
        dvm.add_checkbutton(label="Показать триангуляцию",       variable=self.show_delaunay, command=self._redraw_dv)
        dvm.add_checkbutton(label="Показать диаграмму Вороного", variable=self.show_voronoi,  command=self._redraw_dv)
        dvm.add_checkbutton(label="Описанные окружности",        variable=self.show_circum,   command=self._redraw_dv)
        dvm.add_checkbutton(label="Точки (сайты)",               variable=self.show_sites,    command=self._redraw_dv)
        dvm.add_separator()
        dvm.add_command(label="Очистить Делоне/Вороной", command=self._clear_dv)

        am = self._mk_menu(bar)
        bar.add_cascade(label="Анализ", menu=am)
        am.add_command(label="Рисовать линию",          command=lambda: self._sel_tool("Line"))
        am.add_command(label="Пересечения с полигоном", command=lambda: self._sel_tool("Check Intersection"))
        am.add_command(label="Принадлежность точки",    command=lambda: self._sel_tool("Select Point"))

        vm = self._mk_menu(bar)
        bar.add_cascade(label="Вид", menu=vm)
        vm.add_checkbutton(label="Сетка",            variable=self.show_grid,    command=self._redraw_all)
        vm.add_checkbutton(label="Привязка к сетке", variable=self.snap_to_grid)

    def _build_toolbar(self):
        tb = tk.Frame(self.root, bg=self.C["tb"], pady=5, padx=8)
        tb.pack(side=tk.TOP, fill=tk.X)

        tk.Label(tb, text="POLYGON EDITOR v3",
                 bg=self.C["tb"], fg=self.C["accent"],
                 font=("Courier", 12, "bold")).pack(side=tk.LEFT, padx=(0,14))

        self._tool_btns = {}
        tool_defs = [
            ("Polygon",            "✏ Полигон",      "Polygon"),
            ("Line",               "╱ Линия",         "Line"),
            ("Select Point",       "✦ Точка",         "Select Point"),
            ("Check Intersection", "✕ Пересечение",   "Check Intersection"),
            ("Hull: Graham",       "⬡ Грэхем",        "Hull: Graham"),
            ("Hull: Jarvis",       "⬡ Джарвис",       "Hull: Jarvis"),
            ("DVPoint",            "• Точка ДВ",      "DVPoint"),
        ]
        for key, lbl, tool in tool_defs:
            btn = tk.Button(tb, text=lbl,
                            bg=self.C["tb"], fg=self.C["txt"],
                            activebackground=self.C["btn_act"],
                            relief="flat", bd=0, padx=9, pady=3,
                            cursor="hand2", font=("Courier", 9),
                            command=lambda t=tool: self._sel_tool(t))
            btn.pack(side=tk.LEFT, padx=2)
            self._tool_btns[key] = btn

        tk.Frame(tb, bg="#333333", width=1, height=24).pack(side=tk.LEFT, padx=8)
        tk.Button(tb, text="↺ Очистить",
                  bg=self.C["tb"], fg="#ff5555",
                  relief="flat", bd=0, padx=9, pady=3,
                  font=("Courier", 9), cursor="hand2",
                  command=self._clear_all).pack(side=tk.LEFT, padx=2)
        tk.Button(tb, text="✔ Закрыть полигон",
                  bg=self.C["tb"], fg="#88ff88",
                  relief="flat", bd=0, padx=9, pady=3,
                  font=("Courier", 9), cursor="hand2",
                  command=self._close_polygon).pack(side=tk.LEFT, padx=2)
        self._update_tool_btns()

    def _build_fill_toolbar(self):
        tb2 = tk.Frame(self.root, bg=self.C["tb2"], pady=4, padx=8)
        tb2.pack(side=tk.TOP, fill=tk.X)

        tk.Label(tb2, text="ЗАПОЛНЕНИЕ:",
                 bg=self.C["tb2"], fg="#444466",
                 font=("Courier", 9)).pack(side=tk.LEFT, padx=(0,8))

        fc = {"ET": self.C["f_et"], "AEL": self.C["f_ael"],
              "Flood": self.C["f_flood"], "Scan": self.C["f_scan"]}
        self._fill_btns = {}
        for key, lbl in self.FILL_ALGOS:
            btn = tk.Button(tb2, text=lbl,
                            bg=self.C["tb2"], fg=fc[key],
                            activebackground="#111122",
                            relief="flat", bd=0, padx=9, pady=2,
                            font=("Courier", 9), cursor="hand2",
                            command=lambda k=key: self._sel_fill(k))
            btn.pack(side=tk.LEFT, padx=2)
            self._fill_btns[key] = btn

        tk.Frame(tb2, bg="#222233", width=1, height=20).pack(side=tk.LEFT, padx=8)
        tk.Button(tb2, text="▶ ЗАЛИТЬ",
                  bg="#060f06", fg="#00ff99",
                  activebackground="#0a1a0a",
                  relief="flat", bd=0, padx=11, pady=2,
                  font=("Courier", 9, "bold"), cursor="hand2",
                  command=self._fill_selected).pack(side=tk.LEFT, padx=4)
        tk.Frame(tb2, bg="#222233", width=1, height=20).pack(side=tk.LEFT, padx=8)

        self._debug_btn = tk.Button(tb2, text="⚙ Отладка ВЫКЛ",
                                    bg=self.C["tb2"], fg="#444455",
                                    relief="flat", bd=0, padx=9, pady=2,
                                    font=("Courier", 9), cursor="hand2",
                                    command=self._toggle_debug)
        self._debug_btn.pack(side=tk.LEFT, padx=2)
        tk.Button(tb2, text="✖ Сброс заливки",
                  bg=self.C["tb2"], fg="#aa4422",
                  relief="flat", bd=0, padx=9, pady=2,
                  font=("Courier", 9), cursor="hand2",
                  command=self._clear_fills).pack(side=tk.LEFT, padx=2)
        self._update_fill_btns()

    def _build_dv_toolbar(self):
        tb3 = tk.Frame(self.root, bg=self.C["tb3"], pady=4, padx=8)
        tb3.pack(side=tk.TOP, fill=tk.X)

        tk.Label(tb3, text="ДЕЛОНЕ / ВОРОНОЙ:",
                 bg=self.C["tb3"], fg="#224422",
                 font=("Courier", 9)).pack(side=tk.LEFT, padx=(0,8))

        tk.Button(tb3, text="• Добавить точки",
                  bg=self.C["tb3"], fg=self.C["site"],
                  relief="flat", bd=0, padx=9, pady=2,
                  font=("Courier", 9), cursor="hand2",
                  command=lambda: self._sel_tool("DVPoint")).pack(side=tk.LEFT, padx=2)

        tk.Frame(tb3, bg="#224422", width=1, height=20).pack(side=tk.LEFT, padx=6)

        tk.Button(tb3, text="△ Делоне",
                  bg="#050d0a", fg=self.C["delaunay"],
                  activebackground="#0a1a14",
                  relief="flat", bd=0, padx=11, pady=2,
                  font=("Courier", 9, "bold"), cursor="hand2",
                  command=self._run_delaunay).pack(side=tk.LEFT, padx=3)

        tk.Button(tb3, text="⬡ Вороной",
                  bg="#0d050a", fg=self.C["voronoi"],
                  activebackground="#1a0a14",
                  relief="flat", bd=0, padx=11, pady=2,
                  font=("Courier", 9, "bold"), cursor="hand2",
                  command=self._run_voronoi).pack(side=tk.LEFT, padx=3)

        tk.Button(tb3, text="⬡△ Оба",
                  bg="#0a0a0a", fg="#888888",
                  relief="flat", bd=0, padx=11, pady=2,
                  font=("Courier", 9, "bold"), cursor="hand2",
                  command=self._run_both).pack(side=tk.LEFT, padx=3)

        tk.Frame(tb3, bg="#224422", width=1, height=20).pack(side=tk.LEFT, padx=6)

        for lbl, var, fg in [
            ("Делоне",     self.show_delaunay, self.C["delaunay"]),
            ("Вороной",    self.show_voronoi,  self.C["voronoi"]),
            ("Окружности", self.show_circum,   "#336644"),
            ("Точки",      self.show_sites,    self.C["site"]),
        ]:
            tk.Checkbutton(tb3, text=lbl, variable=var,
                           bg=self.C["tb3"], fg=fg,
                           selectcolor=self.C["tb3"],
                           activebackground=self.C["tb3"],
                           activeforeground=fg,
                           font=("Courier", 9), cursor="hand2",
                           command=self._redraw_dv).pack(side=tk.LEFT, padx=4)

        tk.Frame(tb3, bg="#224422", width=1, height=20).pack(side=tk.LEFT, padx=6)
        self._dv_count_var = tk.StringVar(value="Точек: 0")
        tk.Label(tb3, textvariable=self._dv_count_var,
                 bg=self.C["tb3"], fg="#666666",
                 font=("Courier", 9)).pack(side=tk.LEFT, padx=6)

        tk.Button(tb3, text="✖ Сброс ДВ",
                  bg=self.C["tb3"], fg="#aa4422",
                  relief="flat", bd=0, padx=9, pady=2,
                  font=("Courier", 9), cursor="hand2",
                  command=self._clear_dv).pack(side=tk.RIGHT, padx=4)

    def _build_canvas(self):
        frm = tk.Frame(self.root, bg=self.C["bg"])
        frm.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)
        self.canvas = tk.Canvas(frm, bg=self.C["canvas"],
                                cursor="crosshair", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>",        self._on_left_click)
        self.canvas.bind("<Button-3>",        self._on_right_click)
        self.canvas.bind("<Motion>",          self._on_motion)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)

    def _build_statusbar(self):
        sb = tk.Frame(self.root, bg="#080808", pady=3, padx=10)
        sb.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_var = tk.StringVar(value="Готов.")
        tk.Label(sb, textvariable=self.status_var,
                 bg="#080808", fg=self.C["txt"],
                 font=("Courier", 9), anchor="w").pack(side=tk.LEFT)
        self.coord_var = tk.StringVar(value="x:0 y:0")
        tk.Label(sb, textvariable=self.coord_var,
                 bg="#080808", fg="#555555",
                 font=("Courier", 9)).pack(side=tk.RIGHT)

    # ─────────────────────────────────────────────────────────────
    #  GRID
    # ─────────────────────────────────────────────────────────────

    def _draw_grid(self):
        self.canvas.delete("grid")
        if not self.show_grid.get():
            return
        w = self.canvas.winfo_width()  or 1440
        h = self.canvas.winfo_height() or 800
        g = self.grid_size
        for x in range(0, w, g):
            self.canvas.create_line(x,0,x,h, fill=self.C["grid"], width=1, tags="grid")
        for y in range(0, h, g):
            self.canvas.create_line(0,y,w,y, fill=self.C["grid"], width=1, tags="grid")
        self.canvas.tag_lower("grid")

    # ─────────────────────────────────────────────────────────────
    #  TOOL / FILL SELECTION
    # ─────────────────────────────────────────────────────────────

    def _sel_tool(self, tool):
        if tool == "Hull: Graham":
            self._run_hull("Graham"); return
        if tool == "Hull: Jarvis":
            self._run_hull("Jarvis"); return
        self.current_tool.set(tool)
        self._update_tool_btns()
        hints = {
            "Polygon":            "ЛКМ — вершина | ПКМ/двойной клик — закрыть полигон",
            "Line":               "ЛКМ — начало | ЛКМ ещё раз — конец",
            "Select Point":       "ЛКМ — проверить принадлежность точки",
            "Check Intersection": "ЛКМ — найти пересечения",
            "Seed":               "ЛКМ — выбрать затравку заполнения",
            "DVPoint":            "ЛКМ — добавить точку | ПКМ по точке — удалить",
        }
        self.status_var.set(hints.get(tool, ""))

    def _update_tool_btns(self):
        cur = self.current_tool.get()
        for key, btn in self._tool_btns.items():
            active = (cur == key)
            btn.configure(bg=self.C["btn_act"] if active else self.C["tb"],
                          fg=self.C["accent"] if active else self.C["txt"])

    def _sel_fill(self, key):
        self.fill_algo.set(key)
        self._update_fill_btns()
        self.status_var.set(f"Алгоритм заполнения: {dict(self.FILL_ALGOS)[key]}")

    def _update_fill_btns(self):
        cur = self.fill_algo.get()
        fc = {"ET": self.C["f_et"], "AEL": self.C["f_ael"],
              "Flood": self.C["f_flood"], "Scan": self.C["f_scan"]}
        for key, btn in self._fill_btns.items():
            btn.configure(bg="#111122" if cur==key else self.C["tb2"],
                          fg=fc[key],
                          relief="sunken" if cur==key else "flat")

    def _toggle_debug(self):
        self.debug_mode.set(not self.debug_mode.get())
        on = self.debug_mode.get()
        self._debug_btn.configure(
            text="⚙ Отладка ВКЛ" if on else "⚙ Отладка ВЫКЛ",
            fg="#00ff99" if on else "#444455",
            bg="#060f06" if on else self.C["tb2"])
        if on:
            self._open_debug_panel()

    def _open_debug_panel(self):
        if self._debug_panel and self._debug_panel.winfo_exists():
            self._debug_panel.lift()
            return
        self._debug_panel = DebugPanel(self.root)

    # ─────────────────────────────────────────────────────────────
    #  CANVAS EVENTS
    # ─────────────────────────────────────────────────────────────

    def _snap(self, x, y):
        if self.snap_to_grid.get():
            g = self.grid_size
            x = round(x/g)*g
            y = round(y/g)*g
        return (x, y)

    def _on_motion(self, event):
        x, y = self._snap(event.x, event.y)
        self.coord_var.set(f"x:{x} y:{y}")
        self.preview_pos = (x, y)
        self.canvas.delete("preview")
        tool = self.current_tool.get()
        if tool == "Polygon" and self.polygon_points:
            lx, ly = self.polygon_points[-1]
            self.canvas.create_line(lx,ly,x,y, fill=self.C["preview"],
                                    width=1, tags="preview")
            if len(self.polygon_points) >= 2:
                fx, fy = self.polygon_points[0]
                self.canvas.create_line(x,y,fx,fy, fill=self.C["preview"],
                                        width=1, dash=(4,6), tags="preview")
        elif tool == "Line" and len(self.line_points) == 1:
            lx, ly = self.line_points[0]
            self.canvas.create_line(lx,ly,x,y, fill=self.C["preview"],
                                    width=1, tags="preview")

    def _on_left_click(self, event):
        x, y = self._snap(event.x, event.y)
        tool = self.current_tool.get()

        if tool == "Polygon":
            self.polygon_points.append((x,y))
            self._redraw_all()
            self.status_var.set(f"Вершина ({x},{y}) — {len(self.polygon_points)} шт.")

        elif tool == "Line":
            self.line_points.append((x,y))
            if len(self.line_points) == 2:
                self.lines.append(tuple(self.line_points))
                self.line_points = []
                self._redraw_all()
                self.status_var.set("Линия нарисована.")
            else:
                self.status_var.set(f"Начало ({x},{y}). Кликните для конца.")

        elif tool == "Select Point":
            self._test_point(x, y)

        elif tool == "Check Intersection":
            self._find_intersections()

        elif tool == "Seed":
            self.seed_point = (x,y)
            self._fill_selected(seed_override=(x,y))

        elif tool == "DVPoint":
            self.dv_points.append((x,y))
            self._dv_count_var.set(f"Точек: {len(self.dv_points)}")
            self._redraw_dv_points()
            self.status_var.set(
                f"Точка ({x},{y}) добавлена. Всего: {len(self.dv_points)}")

    def _on_right_click(self, event):
        tool = self.current_tool.get()
        if tool == "Polygon":
            self._close_polygon()
        elif tool == "DVPoint":
            x, y = event.x, event.y
            if self.dv_points:
                nearest = min(self.dv_points, key=lambda p: dist(p,(x,y)))
                if dist(nearest,(x,y)) < 12:
                    self.dv_points.remove(nearest)
                    self._dv_count_var.set(f"Точек: {len(self.dv_points)}")
                    # Invalidate computed results
                    self.dv_triangles.clear()
                    self.dv_circumcenters.clear()
                    self.dv_voronoi_edges.clear()
                    self._redraw_dv_points()

    def _on_double_click(self, event):
        if self.current_tool.get() == "Polygon":
            self._close_polygon()

    # ─────────────────────────────────────────────────────────────
    #  POLYGON OPERATIONS
    # ─────────────────────────────────────────────────────────────

    def _close_polygon(self):
        if len(self.polygon_points) < 3:
            messagebox.showwarning("Полигон", "Минимум 3 вершины.")
            return
        self.polygons.append(list(self.polygon_points))
        self.polygon_points = []
        self._redraw_all()
        self.status_var.set(f"Полигон P{len(self.polygons)} добавлен.")

    def _check_convexity(self):
        if not self.polygons:
            messagebox.showinfo("Выпуклость", "Нет полигонов.")
            return
        res = [f"P{i+1}: {'ВЫПУКЛЫЙ ✔' if is_convex(p) else 'НЕВЫПУКЛЫЙ ✘'}"
               for i,p in enumerate(self.polygons)]
        messagebox.showinfo("Проверка выпуклости", "\n".join(res))

    def _collect_pts(self):
        pts = [p for poly in self.polygons for p in poly]
        pts.extend(self.polygon_points)
        return pts

    def _run_hull(self, method):
        pts = self._collect_pts()
        if len(pts) < 3:
            messagebox.showwarning("Оболочка", "Нужно >= 3 точек.")
            return
        self.hull_polygon = graham_scan(pts) if method=="Graham" else jarvis_march(pts)
        self.hull_method  = method
        self._redraw_all()
        self.status_var.set(f"Оболочка {method}: {len(self.hull_polygon)} вершин")

    # ─────────────────────────────────────────────────────────────
    #  DELAUNAY & VORONOI
    # ─────────────────────────────────────────────────────────────

    def _run_delaunay(self):
        if len(self.dv_points) < 3:
            messagebox.showwarning("Делоне", "Нужно минимум 3 точки.")
            return
        tris, ccs = delaunay(self.dv_points)
        self.dv_triangles     = tris
        self.dv_circumcenters = ccs
        self.dv_voronoi_edges = []
        self._redraw_dv()
        self.status_var.set(
            f"Триангуляция Делоне (Bowyer–Watson): "
            f"{len(tris)} треугольников, {len(self.dv_points)} точек")

    def _run_voronoi(self):
        if not self.dv_triangles:
            self._run_delaunay()
            if not self.dv_triangles:
                return
        cw = self.canvas.winfo_width()  or 1440
        ch = self.canvas.winfo_height() or 800
        self.dv_voronoi_edges = voronoi_edges(
            self.dv_triangles, self.dv_circumcenters,
            self.dv_points, cw, ch)
        self._redraw_dv()
        self.status_var.set(
            f"Диаграмма Вороного: {len(self.dv_voronoi_edges)} рёбер")

    def _run_both(self):
        if len(self.dv_points) < 3:
            messagebox.showwarning("Делоне/Вороной", "Нужно минимум 3 точки.")
            return
        tris, ccs = delaunay(self.dv_points)
        self.dv_triangles     = tris
        self.dv_circumcenters = ccs
        cw = self.canvas.winfo_width()  or 1440
        ch = self.canvas.winfo_height() or 800
        self.dv_voronoi_edges = voronoi_edges(tris, ccs, self.dv_points, cw, ch)
        self._redraw_dv()
        self.status_var.set(
            f"Делоне: {len(tris)} треуг. | "
            f"Вороной: {len(self.dv_voronoi_edges)} рёбер | "
            f"Точек: {len(self.dv_points)}")

    def _clear_dv(self):
        self.dv_points.clear()
        self.dv_triangles.clear()
        self.dv_circumcenters.clear()
        self.dv_voronoi_edges.clear()
        self._dv_count_var.set("Точек: 0")
        self.canvas.delete("dv")
        self.status_var.set("Делоне/Вороной очищен.")

    # ── Draw Delaunay/Voronoi ─────────────────────────────────────

    def _redraw_dv_points(self):
        """Lightweight: only redraw site dots (no full recompute)."""
        self.canvas.delete("dv_pts")
        if self.show_sites.get():
            for i, p in enumerate(self.dv_points):
                self.canvas.create_oval(p[0]-4,p[1]-4,p[0]+4,p[1]+4,
                                        fill=self.C["site"], outline="",
                                        tags=("dv","dv_pts"))
                self.canvas.create_text(p[0]+7,p[1]-7,
                                        text=str(i+1),
                                        fill=self.C["site"],
                                        font=("Courier",8),
                                        tags=("dv","dv_pts"))

    def _redraw_dv(self):
        self.canvas.delete("dv")
        pts = self.dv_points

        # ── Delaunay triangles ────────────────────────────────────
        if self.show_delaunay.get() and self.dv_triangles:
            for tri in self.dv_triangles:
                coords = [c for i in tri for c in pts[i]]
                self.canvas.create_polygon(
                    coords,
                    fill=self.C["tri_fill"],
                    outline=self.C["delaunay"],
                    width=1,
                    tags=("dv","dv_del"))

        # ── Circumscribed circles ─────────────────────────────────
        if self.show_circum.get() and self.dv_circumcenters:
            for i, cc in enumerate(self.dv_circumcenters):
                if cc is None:
                    continue
                cx, cy = cc
                r = dist(cc, pts[self.dv_triangles[i][0]])
                self.canvas.create_oval(cx-r,cy-r,cx+r,cy+r,
                                        outline=self.C["circum"],
                                        fill="", width=1,
                                        dash=(4,4),
                                        tags=("dv","dv_circ"))
                self.canvas.create_oval(cx-2,cy-2,cx+2,cy+2,
                                        fill=self.C["circum"],
                                        outline="",
                                        tags=("dv","dv_circ"))

        # ── Voronoi edges ─────────────────────────────────────────
        if self.show_voronoi.get() and self.dv_voronoi_edges:
            for x0,y0,x1,y1 in self.dv_voronoi_edges:
                self.canvas.create_line(x0,y0,x1,y1,
                                        fill=self.C["voronoi"],
                                        width=1,
                                        tags=("dv","dv_vor"))

        # ── Site points (topmost) ─────────────────────────────────
        if self.show_sites.get():
            for i, p in enumerate(pts):
                self.canvas.create_oval(p[0]-5,p[1]-5,p[0]+5,p[1]+5,
                                        fill=self.C["site"],
                                        outline="#ffffff", width=1,
                                        tags=("dv","dv_pts"))
                self.canvas.create_text(p[0]+8,p[1]-8,
                                        text=str(i+1),
                                        fill=self.C["site"],
                                        font=("Courier",8),
                                        tags=("dv","dv_pts"))

    # ─────────────────────────────────────────────────────────────
    #  FILL
    # ─────────────────────────────────────────────────────────────

    def _fill_selected(self, seed_override=None):
        if not self.polygons:
            messagebox.showwarning("Заполнение", "Нет полигонов.")
            return
        algo  = self.fill_algo.get()
        debug = self.debug_mode.get()
        fc = {"ET": self.C["f_et"], "AEL": self.C["f_ael"],
              "Flood": self.C["f_flood"], "Scan": self.C["f_scan"]}
        color = fc[algo]
        needs_seed = algo in ("Flood","Scan")

        if needs_seed:
            if seed_override:
                seed = seed_override
            elif (self.seed_point and
                  any(point_in_polygon(self.seed_point,p) for p in self.polygons)):
                seed = self.seed_point
            else:
                messagebox.showinfo(
                    "Затравка",
                    "Переключитесь на инструмент 'Seed' и кликните внутри полигона.")
                self._sel_tool("Seed")
                return
            target_idx = next(
                (i for i,p in enumerate(self.polygons) if point_in_polygon(seed,p)),
                None)
            if target_idx is None:
                messagebox.showwarning("Заполнение", "Затравка вне полигонов.")
                return
        else:
            target_idx = len(self.polygons)-1
            seed = None

        poly = self.polygons[target_idx]
        cw   = self.canvas.winfo_width()  or 1440
        ch   = self.canvas.winfo_height() or 800

        if algo == "ET":
            gen = fill_scanline_et(poly, color, debug)
        elif algo == "AEL":
            gen = fill_scanline_ael(poly, color, debug)
        elif algo == "Flood":
            gen = fill_flood_simple(poly, seed, cw, ch, debug)
        else:
            gen = fill_flood_scanline(poly, seed, cw, ch, debug)

        tag = f"fill_{target_idx}"
        self.canvas.delete(tag)
        is_et = algo in ("ET","AEL")

        if debug:
            if not (self._debug_panel and self._debug_panel.winfo_exists()):
                self._debug_panel = DebugPanel(self.root)
            def on_step(pixels, y, msg):
                self._draw_fill_step(pixels, color, tag, y, is_et)
            self._debug_panel.attach(gen, on_step)
        else:
            for pixels, y, _ in gen:
                pass
            self._draw_fill_instant(pixels, color, tag, is_et)

    def _draw_fill_instant(self, pixels, color, tag, is_et=True):
        if is_et:
            for xl, xr, y in pixels:
                if xl <= xr:
                    self.canvas.create_line(xl,y,xr,y,
                                            fill=color, width=1, tags=tag)
        else:
            rows = defaultdict(list)
            for x, y in pixels:
                rows[y].append(x)
            for y, xs in rows.items():
                xs.sort()
                rs = xs[0]; pv = xs[0]
                for x in xs[1:]:
                    if x > pv+1:
                        self.canvas.create_line(rs,y,pv,y,
                                                fill=color,width=1,tags=tag)
                        rs = x
                    pv = x
                self.canvas.create_line(rs,y,pv,y,fill=color,width=1,tags=tag)
        self.canvas.tag_raise("polygon_edge")

    def _draw_fill_step(self, pixels, color, tag, scanline_y=-1, is_et=True):
        self.canvas.delete("fill_debug")
        self._draw_fill_instant(pixels, color, tag, is_et)
        if is_et and scanline_y >= 0:
            cw = self.canvas.winfo_width() or 1440
            self.canvas.create_line(0,scanline_y,cw,scanline_y,
                                    fill=self.C["dbg_step"],width=1,
                                    dash=(4,3),tags="fill_debug")
        elif not is_et:
            for x, y in list(pixels)[:200]:
                self.canvas.create_rectangle(x-1,y-1,x+1,y+1,
                                             fill=self.C["dbg_step"],
                                             outline="",tags="fill_debug")
        self.canvas.tag_raise("polygon_edge")
        self.canvas.update_idletasks()

    def _clear_fills(self):
        for i in range(len(self.polygons)):
            self.canvas.delete(f"fill_{i}")
        self.canvas.delete("fill_debug")
        self.status_var.set("Заливка сброшена.")

    # ─────────────────────────────────────────────────────────────
    #  ANALYSIS
    # ─────────────────────────────────────────────────────────────

    def _test_point(self, x, y):
        self.check_point = (x,y)
        self.canvas.delete("check_point")
        inside = [f"P{i+1}" for i,p in enumerate(self.polygons)
                  if point_in_polygon((x,y),p)]
        color = self.C["pt_in"] if inside else self.C["pt_out"]
        self.canvas.create_oval(x-6,y-6,x+6,y+6,
                                outline=color,fill=color,width=2,
                                tags="check_point")
        lbl = ("✔ "+",".join(inside)) if inside else "✘ вне"
        self.canvas.create_text(x+10,y-10,text=lbl,fill=color,
                                font=("Courier",9,"bold"),anchor="w",
                                tags="check_point")
        self.status_var.set(
            f"({x},{y}): "
            f"{'внутри '+', '.join(inside) if inside else 'вне всех полигонов'}")

    def _find_intersections(self):
        self.intersections = []
        self.canvas.delete("intersections")
        for p1,p2 in self.lines:
            for poly in self.polygons:
                n = len(poly)
                for i in range(n):
                    pt = segment_intersect(p1,p2,poly[i],poly[(i+1)%n])
                    if pt:
                        self.intersections.append(pt)
        for pt in self.intersections:
            px, py = int(pt[0]), int(pt[1])
            self.canvas.create_oval(px-5,py-5,px+5,py+5,
                                    outline=self.C["intersect"],
                                    fill=self.C["intersect"],
                                    width=2,tags="intersections")
            self.canvas.create_text(px+8,py-8,
                                    text=f"({px},{py})",
                                    fill=self.C["intersect"],
                                    font=("Courier",8),
                                    tags="intersections")
        self.status_var.set(f"Пересечений: {len(self.intersections)}")

    # ─────────────────────────────────────────────────────────────
    #  FULL REDRAW
    # ─────────────────────────────────────────────────────────────

    def _redraw_all(self):
        self.canvas.delete("all")
        self._draw_grid()
        self._draw_lines()
        self._draw_polygons()
        if self.polygon_points:
            self._draw_in_progress()
        self._draw_hull()
        self._redraw_dv()
        # restore analysis overlays
        for pt in self.intersections:
            px, py = int(pt[0]), int(pt[1])
            self.canvas.create_oval(px-5,py-5,px+5,py+5,
                                    outline=self.C["intersect"],
                                    fill=self.C["intersect"],
                                    width=2,tags="intersections")
        if self.check_point:
            x, y = self.check_point
            inside = any(point_in_polygon(self.check_point,p) for p in self.polygons)
            color = self.C["pt_in"] if inside else self.C["pt_out"]
            self.canvas.create_oval(x-6,y-6,x+6,y+6,
                                    outline=color,fill=color,width=2)

    def _draw_lines(self):
        for p1, p2 in self.lines:
            self.canvas.create_line(p1[0],p1[1],p2[0],p2[1],
                                    fill=self.C["line"],width=2)
            for ep in (p1,p2):
                self.canvas.create_oval(ep[0]-3,ep[1]-3,ep[0]+3,ep[1]+3,
                                        fill=self.C["line"],outline="")

    def _draw_polygons(self):
        for idx, poly in enumerate(self.polygons):
            n = len(poly)
            for i in range(n):
                a, b = poly[i], poly[(i+1)%n]
                self.canvas.create_line(a[0],a[1],b[0],b[1],
                                        fill=self.C["polygon"],width=2,
                                        tags="polygon_edge")
            for pt in poly:
                self.canvas.create_oval(pt[0]-4,pt[1]-4,pt[0]+4,pt[1]+4,
                                        fill=self.C["vertex"],
                                        outline=self.C["polygon"],width=2,
                                        tags="polygon_edge")
            cx = sum(p[0] for p in poly)/n
            cy = sum(p[1] for p in poly)/n
            conv = is_convex(poly)
            self.canvas.create_text(cx,cy,
                                    text=f"P{idx+1} {'◈' if conv else '◇'}",
                                    fill=self.C["polygon"],
                                    font=("Courier",9,"bold"),
                                    tags="polygon_edge")
            if self.show_normals.get():
                for i, nm in enumerate(inward_normals(poly)):
                    a, b = poly[i], poly[(i+1)%n]
                    mx, my = (a[0]+b[0])/2, (a[1]+b[1])/2
                    self.canvas.create_line(mx,my,
                                            mx+nm[0]*24,my+nm[1]*24,
                                            fill=self.C["normal"],width=1,
                                            arrow=tk.LAST,arrowshape=(8,10,3),
                                            tags="polygon_edge")

    def _draw_in_progress(self):
        pts = self.polygon_points
        for i in range(len(pts)-1):
            self.canvas.create_line(pts[i][0],pts[i][1],
                                    pts[i+1][0],pts[i+1][1],
                                    fill=self.C["polygon"],width=2,dash=(6,3))
        for pt in pts:
            self.canvas.create_oval(pt[0]-4,pt[1]-4,pt[0]+4,pt[1]+4,
                                    fill=self.C["vertex"],
                                    outline=self.C["polygon"],width=2)

    def _draw_hull(self):
        if not self.hull_polygon or len(self.hull_polygon) < 2:
            return
        color = self.C["hull_g"] if self.hull_method=="Graham" else self.C["hull_j"]
        hull  = self.hull_polygon
        flat  = [c for pt in hull for c in pt]
        self.canvas.create_polygon(flat, outline=color, fill="", width=2, dash=(8,4))
        for i, pt in enumerate(hull):
            self.canvas.create_oval(pt[0]-5,pt[1]-5,pt[0]+5,pt[1]+5,
                                    fill=color,outline="white",width=1)
            self.canvas.create_text(pt[0]+8,pt[1]-8,
                                    text=str(i+1),
                                    fill=color,font=("Courier",8,"bold"))
        cx = sum(p[0] for p in hull)/len(hull)
        cy = sum(p[1] for p in hull)/len(hull)
        self.canvas.create_text(cx,cy,
                                text=f"Hull ({self.hull_method})",
                                fill=color,font=("Courier",9,"bold"))

    # ─────────────────────────────────────────────────────────────
    #  CLEAR
    # ─────────────────────────────────────────────────────────────

    def _clear_all(self):
        self.polygons.clear()
        self.polygon_points.clear()
        self.lines.clear()
        self.line_points.clear()
        self.hull_polygon = None
        self.hull_method  = None
        self.check_point  = None
        self.intersections.clear()
        self.seed_point   = None
        self._fill_pixels.clear()
        self._clear_dv()
        self.canvas.delete("all")
        self._draw_grid()
        self.status_var.set("Холст очищен.")


# ═══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    root = tk.Tk()
    app  = PolygonEditor(root)
    root.bind("<Configure>", lambda e: app._draw_grid())
    root.mainloop()
