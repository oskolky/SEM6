import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import math
import random


# ─────────────────────────── Geometry helpers ───────────────────────────────

def cross2d(o, a, b):
    """2D cross product of OA × OB."""
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def dist(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def normalize(v):
    n = math.hypot(v[0], v[1])
    if n < 1e-9:
        return (0, 0)
    return (v[0] / n, v[1] / n)


def segment_intersect(p1, p2, p3, p4):
    """Return intersection point of segments p1-p2 and p3-p4, or None."""
    d1 = (p2[0] - p1[0], p2[1] - p1[1])
    d2 = (p4[0] - p3[0], p4[1] - p3[1])
    cross = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(cross) < 1e-9:
        return None
    t = ((p3[0] - p1[0]) * d2[1] - (p3[1] - p1[1]) * d2[0]) / cross
    u = ((p3[0] - p1[0]) * d1[1] - (p3[1] - p1[1]) * d1[0]) / cross
    if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
        return (p1[0] + t * d1[0], p1[1] + t * d1[1])
    return None


def point_in_polygon(point, polygon):
    """Ray-casting algorithm. Returns True if inside."""
    if len(polygon) < 3:
        return False
    x, y = point
    n = len(polygon)
    inside = False
    px, py = polygon[-1]
    for i in range(n):
        cx, cy = polygon[i]
        if ((cy > y) != (py > y)) and (x < (px - cx) * (y - cy) / (py - cy + 1e-12) + cx):
            inside = not inside
        px, py = cx, cy
    return inside


def is_convex(polygon):
    """Check if polygon is convex (consistent cross product sign)."""
    n = len(polygon)
    if n < 3:
        return False
    sign = None
    for i in range(n):
        o = polygon[i]
        a = polygon[(i + 1) % n]
        b = polygon[(i + 2) % n]
        c = cross2d(o, a, b)
        if abs(c) < 1e-9:
            continue
        s = 1 if c > 0 else -1
        if sign is None:
            sign = s
        elif sign != s:
            return False
    return True


def inward_normals(polygon):
    """Compute inward-facing unit normals for each edge."""
    n = len(polygon)
    # Determine orientation (signed area)
    area = sum(cross2d(polygon[0], polygon[i], polygon[(i + 1) % n])
               for i in range(1, n - 1))
    normals = []
    for i in range(n):
        a = polygon[i]
        b = polygon[(i + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        # Rotate 90° – direction depends on orientation
        if area > 0:          # CCW → inward is right-turn
            nx, ny = dy, -dx
        else:                  # CW  → inward is left-turn
            nx, ny = -dy, dx
        normals.append(normalize((nx, ny)))
    return normals


# ─────────────────────────── Convex Hull algorithms ─────────────────────────

def graham_scan(points):
    """Graham scan convex hull. Returns hull vertices in CCW order."""
    pts = list(set(points))
    if len(pts) < 3:
        return pts
    pivot = min(pts, key=lambda p: (p[1], p[0]))

    def angle_key(p):
        a = math.atan2(p[1] - pivot[1], p[0] - pivot[0])
        d = dist(pivot, p)
        return (a, d)

    pts.sort(key=angle_key)
    hull = []
    for p in pts:
        while len(hull) >= 2 and cross2d(hull[-2], hull[-1], p) <= 0:
            hull.pop()
        hull.append(p)
    return hull


def jarvis_march(points):
    """Jarvis march (gift wrapping) convex hull."""
    pts = list(set(points))
    if len(pts) < 3:
        return pts
    start = min(pts, key=lambda p: (p[0], p[1]))
    hull = []
    current = start
    while True:
        hull.append(current)
        next_pt = pts[0]
        for p in pts[1:]:
            c = cross2d(current, next_pt, p)
            if c < 0 or (abs(c) < 1e-9 and dist(current, p) > dist(current, next_pt)):
                next_pt = p
        current = next_pt
        if current == start:
            break
    return hull


# ─────────────────────────── Bresenham line ─────────────────────────────────

def bresenham(x0, y0, x1, y1):
    """Integer Bresenham line pixels."""
    pts = []
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy
    return pts


# ─────────────────────────── Main Application ────────────────────────────────

class PolygonEditor:
    TOOLS = ["Polygon", "Line", "Select Point", "Check Intersection", "Hull: Graham", "Hull: Jarvis"]
    COLORS = {
        "bg": "#000000",  # фон окна
        "canvas": "#000000",  # фон канвы
        "grid": "#333333",  # линии сетки
        "polygon": "#ffffff",  # контур полигона
        "polygon_fill": "#666666",  # заливка полигона (темно-серый)
        "hull_graham": "#ffffff",  # контур Грэхема — белый
        "hull_jarvis": "#aaaaaa",  # контур Джарвиса — светло-серый
        "normal": "#ffffff",  # обычные линии
        "line": "#ffffff",  # линии рисования
        "intersection": "#ff0000",  # точки пересечения
        "point_inside": "#ffffff",  # точки внутри полигона
        "point_outside": "#000000",  # точки вне полигона
        "vertex": "#ffffff",  # вершины
        "preview": "#999999",  # предварительный просмотр линий
        "toolbar_bg": "#111111",  # панель инструментов
        "btn_active": "#555555",  # активная кнопка
        "accent": "#ffffff",  # акцентный цвет
        "text": "#ffffff"  # текст
    }

    def __init__(self, root):
        self.root = root
        self.root.title("Polygon Graphics Editor")
        self.root.configure(bg=self.COLORS["bg"])
        self.root.geometry("1280x820")

        self.current_tool = tk.StringVar(value="Polygon")
        self.show_normals = tk.BooleanVar(value=True)
        self.show_grid = tk.BooleanVar(value=True)
        self.snap_to_grid = tk.BooleanVar(value=False)
        self.grid_size = 20

        # State
        self.polygon_points = []        # current polygon being drawn
        self.polygons = []              # list of finished polygons
        self.line_points = []           # current line segment
        self.lines = []                 # finished lines
        self.hull_polygon = None        # last computed hull
        self.hull_method = None
        self.check_point = None
        self.intersections = []
        self.preview_pos = None
        self.drawn_objects = []         # canvas item ids for cleanup

        self._build_ui()
        self._draw_grid()

    # ── UI construction ────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_menu()
        self._build_toolbar()
        self._build_canvas()
        self._build_statusbar()

    def _build_menu(self):
        menubar = tk.Menu(self.root, bg=self.COLORS["toolbar_bg"],
                          fg=self.COLORS["text"], activebackground=self.COLORS["btn_active"],
                          activeforeground=self.COLORS["accent"], relief="flat", bd=0)
        self.root.config(menu=menubar)

        # File
        fm = tk.Menu(menubar, tearoff=0, bg=self.COLORS["toolbar_bg"],
                     fg=self.COLORS["text"], activebackground=self.COLORS["btn_active"])
        menubar.add_cascade(label="Файл", menu=fm)
        fm.add_command(label="Очистить всё", command=self._clear_all)
        fm.add_separator()
        fm.add_command(label="Выход", command=self.root.quit)

        # Polygon tools
        pm = tk.Menu(menubar, tearoff=0, bg=self.COLORS["toolbar_bg"],
                     fg=self.COLORS["text"], activebackground=self.COLORS["btn_active"])
        menubar.add_cascade(label="Построение полигонов", menu=pm)
        pm.add_command(label="Новый полигон", command=lambda: self.current_tool.set("Polygon"))
        pm.add_separator()
        pm.add_command(label="Выпуклая оболочка — Грэхем",
                       command=lambda: self._run_hull("Graham"))
        pm.add_command(label="Выпуклая оболочка — Джарвис",
                       command=lambda: self._run_hull("Jarvis"))
        pm.add_separator()
        pm.add_command(label="Проверить выпуклость", command=self._check_convexity)
        pm.add_command(label="Показать внутренние нормали", command=self._toggle_normals_and_redraw)

        # Analysis
        am = tk.Menu(menubar, tearoff=0, bg=self.COLORS["toolbar_bg"],
                     fg=self.COLORS["text"], activebackground=self.COLORS["btn_active"])
        menubar.add_cascade(label="Анализ", menu=am)
        am.add_command(label="Рисовать линию", command=lambda: self.current_tool.set("Line"))
        am.add_command(label="Пересечения линии с полигоном",
                       command=lambda: self.current_tool.set("Check Intersection"))
        am.add_command(label="Принадлежность точки",
                       command=lambda: self.current_tool.set("Select Point"))

        # View
        vm = tk.Menu(menubar, tearoff=0, bg=self.COLORS["toolbar_bg"],
                     fg=self.COLORS["text"], activebackground=self.COLORS["btn_active"])
        menubar.add_cascade(label="Вид", menu=vm)
        vm.add_checkbutton(label="Сетка", variable=self.show_grid,
                           command=self._redraw_all)
        vm.add_checkbutton(label="Привязка к сетке", variable=self.snap_to_grid)
        vm.add_checkbutton(label="Нормали", variable=self.show_normals,
                           command=self._redraw_all)

    def _build_toolbar(self):
        tb = tk.Frame(self.root, bg=self.COLORS["toolbar_bg"], pady=6, padx=8)
        tb.pack(side=tk.TOP, fill=tk.X)

        tk.Label(tb, text="POLYGON EDITOR", bg=self.COLORS["toolbar_bg"],
                 fg=self.COLORS["accent"], font=("Courier", 13, "bold")).pack(side=tk.LEFT, padx=(0, 18))

        self._tool_btns = {}
        tool_defs = [
            ("Polygon", "✏ Полигон", "Polygon"),
            ("Line", "╱ Линия", "Line"),
            ("Select Point", "✦ Точка", "Select Point"),
            ("Check Intersection", "✕ Пересечение", "Check Intersection"),
            ("Hull: Graham", "⬡ Грэхем", "Hull: Graham"),
            ("Hull: Jarvis", "⬡ Джарвис", "Hull: Jarvis"),
        ]
        for key, label, tool in tool_defs:
            btn = tk.Button(
                tb, text=label,
                bg=self.COLORS["toolbar_bg"], fg=self.COLORS["text"],
                activebackground=self.COLORS["btn_active"],
                activeforeground=self.COLORS["accent"],
                relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
                font=("Courier", 9),
                command=lambda t=tool: self._select_tool(t)
            )
            btn.pack(side=tk.LEFT, padx=2)
            self._tool_btns[key] = btn

        # Separator
        tk.Frame(tb, bg=self.COLORS["accent"], width=1, height=28).pack(side=tk.LEFT, padx=10)

        tk.Button(tb, text="↺ Очистить", bg=self.COLORS["toolbar_bg"],
                  fg="#ff6b6b", relief="flat", bd=0, padx=10, pady=4,
                  font=("Courier", 9), cursor="hand2",
                  command=self._clear_all).pack(side=tk.LEFT, padx=2)

        tk.Button(tb, text="✔ Закрыть полигон", bg=self.COLORS["toolbar_bg"],
                  fg=self.COLORS["hull_graham"], relief="flat", bd=0, padx=10, pady=4,
                  font=("Courier", 9), cursor="hand2",
                  command=self._close_polygon).pack(side=tk.LEFT, padx=2)

        self._update_tool_buttons()

    def _build_canvas(self):
        frame = tk.Frame(self.root, bg=self.COLORS["bg"])
        frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.canvas = tk.Canvas(frame, bg=self.COLORS["canvas"],
                                cursor="crosshair", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.bind("<Button-1>", self._on_left_click)
        self.canvas.bind("<Button-3>", self._on_right_click)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)

    def _build_statusbar(self):
        sb = tk.Frame(self.root, bg=self.COLORS["toolbar_bg"], pady=4, padx=10)
        sb.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_var = tk.StringVar(value="Готов. Выберите инструмент.")
        tk.Label(sb, textvariable=self.status_var, bg=self.COLORS["toolbar_bg"],
                 fg=self.COLORS["text"], font=("Courier", 9), anchor="w").pack(side=tk.LEFT)
        self.coord_var = tk.StringVar(value="x: 0  y: 0")
        tk.Label(sb, textvariable=self.coord_var, bg=self.COLORS["toolbar_bg"],
                 fg=self.COLORS["accent"], font=("Courier", 9)).pack(side=tk.RIGHT)

    # ── Grid ──────────────────────────────────────────────────────────────

    def _draw_grid(self):
        self.canvas.delete("grid")
        if not self.show_grid.get():
            return
        w = self.canvas.winfo_width() or 1280
        h = self.canvas.winfo_height() or 740
        g = self.grid_size
        for x in range(0, w, g):
            self.canvas.create_line(x, 0, x, h, fill=self.COLORS["grid"],
                                    width=1, tags="grid")
        for y in range(0, h, g):
            self.canvas.create_line(0, y, w, y, fill=self.COLORS["grid"],
                                    width=1, tags="grid")
        self.canvas.tag_lower("grid")

    # ── Tool selection ─────────────────────────────────────────────────────

    def _select_tool(self, tool):
        if tool in ("Hull: Graham", "Hull: Jarvis"):
            method = "Graham" if "Graham" in tool else "Jarvis"
            self._run_hull(method)
        else:
            self.current_tool.set(tool)
            self._update_tool_buttons()
            hints = {
                "Polygon": "ЛКМ — добавить вершину | ПКМ или двойной клик — закрыть полигон",
                "Line": "ЛКМ — начало линии | ЛКМ ещё раз — конец линии",
                "Select Point": "ЛКМ — проверить принадлежность точки полигону",
                "Check Intersection": "Нарисуйте линию, затем выберите этот инструмент",
            }
            self.status_var.set(hints.get(tool, ""))

    def _update_tool_buttons(self):
        cur = self.current_tool.get()
        key_map = {
            "Polygon": "Polygon",
            "Line": "Line",
            "Select Point": "Select Point",
            "Check Intersection": "Check Intersection",
        }
        for key, btn in self._tool_btns.items():
            tool_key = key_map.get(key, key)
            active = (cur == tool_key or cur == key)
            btn.configure(
                bg=self.COLORS["btn_active"] if active else self.COLORS["toolbar_bg"],
                fg=self.COLORS["accent"] if active else self.COLORS["text"]
            )

    # ── Canvas events ──────────────────────────────────────────────────────

    def _snap(self, x, y):
        if self.snap_to_grid.get():
            g = self.grid_size
            x = round(x / g) * g
            y = round(y / g) * g
        return (x, y)

    def _on_motion(self, event):
        x, y = self._snap(event.x, event.y)
        self.coord_var.set(f"x: {x}  y: {y}")
        self.preview_pos = (x, y)
        self.canvas.delete("preview")
        tool = self.current_tool.get()
        if tool == "Polygon" and self.polygon_points:
            lx, ly = self.polygon_points[-1]
            self._draw_preview_line(lx, ly, x, y)
            if len(self.polygon_points) >= 2:
                fx, fy = self.polygon_points[0]
                self._draw_preview_line(x, y, fx, fy, dash=(4, 6))
        elif tool == "Line" and len(self.line_points) == 1:
            lx, ly = self.line_points[0]
            self._draw_preview_line(lx, ly, x, y)

    def _draw_preview_line(self, x0, y0, x1, y1, dash=()):
        self.canvas.create_line(x0, y0, x1, y1, fill=self.COLORS["preview"],
                                width=1, dash=dash, tags="preview")

    def _on_left_click(self, event):
        x, y = self._snap(event.x, event.y)
        tool = self.current_tool.get()
        if tool == "Polygon":
            self.polygon_points.append((x, y))
            self._redraw_all()
            self.status_var.set(f"Вершина добавлена ({x}, {y}). Вершин: {len(self.polygon_points)}")
        elif tool == "Line":
            self.line_points.append((x, y))
            if len(self.line_points) == 2:
                self.lines.append(tuple(self.line_points))
                self.line_points = []
                self._redraw_all()
                self.status_var.set("Линия нарисована.")
            else:
                self.status_var.set(f"Начало линии: ({x}, {y}). Кликните для конца.")
        elif tool == "Select Point":
            self._test_point_in_polygons(x, y)
        elif tool == "Check Intersection":
            self._find_all_intersections(x, y)

    def _on_right_click(self, event):
        if self.current_tool.get() == "Polygon":
            self._close_polygon()

    def _on_double_click(self, event):
        if self.current_tool.get() == "Polygon":
            self._close_polygon()

    # ── Polygon operations ────────────────────────────────────────────────

    def _close_polygon(self):
        if len(self.polygon_points) < 3:
            messagebox.showwarning("Полигон", "Нужно минимум 3 вершины.")
            return
        self.polygons.append(list(self.polygon_points))
        self.polygon_points = []
        self._redraw_all()
        self.status_var.set(f"Полигон добавлен. Всего: {len(self.polygons)}")

    def _check_convexity(self):
        if not self.polygons:
            messagebox.showinfo("Выпуклость", "Нет полигонов.")
            return
        results = []
        for i, poly in enumerate(self.polygons):
            c = is_convex(poly)
            results.append(f"Полигон {i+1}: {'ВЫПУКЛЫЙ ✔' if c else 'НЕВЫПУКЛЫЙ ✘'}")
        messagebox.showinfo("Проверка выпуклости", "\n".join(results))

    def _toggle_normals_and_redraw(self):
        self.show_normals.set(not self.show_normals.get())
        self._redraw_all()

    # ── Hull algorithms ───────────────────────────────────────────────────

    def _collect_all_points(self):
        pts = []
        for poly in self.polygons:
            pts.extend(poly)
        pts.extend(self.polygon_points)
        return pts

    def _run_hull(self, method):
        pts = self._collect_all_points()
        if len(pts) < 3:
            messagebox.showwarning("Оболочка", "Нужно минимум 3 точки (вершины полигонов).")
            return
        if method == "Graham":
            hull = graham_scan(pts)
        else:
            hull = jarvis_march(pts)
        self.hull_polygon = hull
        self.hull_method = method
        self._redraw_all()
        self.status_var.set(
            f"Выпуклая оболочка ({method}): {len(hull)} вершин | "
            f"{'Грэхем: сортировка по углу + стек' if method=='Graham' else 'Джарвис: метод подарочной упаковки'}"
        )

    # ── Analysis ──────────────────────────────────────────────────────────

    def _test_point_in_polygons(self, x, y):
        self.check_point = (x, y)
        self.canvas.delete("check_point")
        inside_any = False
        for i, poly in enumerate(self.polygons):
            inside = point_in_polygon((x, y), poly)
            if inside:
                inside_any = True
                self.status_var.set(f"Точка ({x},{y}) ВНУТРИ полигона {i+1} ✔")
        color = self.COLORS["point_inside"] if inside_any else self.COLORS["point_outside"]
        if not inside_any:
            self.status_var.set(f"Точка ({x},{y}) ВНЕ всех полигонов ✘")
        self.canvas.create_oval(x - 6, y - 6, x + 6, y + 6,
                                outline=color, fill=color + "88", width=2,
                                tags="check_point")
        self.canvas.create_text(x + 12, y - 10,
                                text="✔ inside" if inside_any else "✘ outside",
                                fill=color, font=("Courier", 9, "bold"),
                                anchor="w", tags="check_point")

    def _find_all_intersections(self, x=None, y=None):
        self.intersections = []
        self.canvas.delete("intersections")
        for seg in self.lines:
            p1, p2 = seg
            for poly in self.polygons:
                n = len(poly)
                for i in range(n):
                    a = poly[i]
                    b = poly[(i + 1) % n]
                    pt = segment_intersect(p1, p2, a, b)
                    if pt:
                        self.intersections.append(pt)
        for pt in self.intersections:
            px, py = int(pt[0]), int(pt[1])
            r = 6
            self.canvas.create_oval(px - r, py - r, px + r, py + r,
                                    outline=self.COLORS["intersection"],
                                    fill=self.COLORS["intersection"],
                                    width=2, tags="intersections")
            self.canvas.create_text(px + 10, py - 10,
                                    text=f"({px},{py})",
                                    fill=self.COLORS["intersection"],
                                    font=("Courier", 8), tags="intersections")
        self.status_var.set(f"Пересечений найдено: {len(self.intersections)}")

    # ── Drawing / Redraw ─────────────────────────────────────────────────

    def _redraw_all(self):
        self.canvas.delete("all")
        self._draw_grid()
        self._draw_lines()
        self._draw_polygons()
        if self.polygon_points:
            self._draw_in_progress_polygon()
        self._draw_hull()
        # re-draw analytical overlays
        for pt in self.intersections:
            px, py = int(pt[0]), int(pt[1])
            r = 6
            self.canvas.create_oval(px - r, py - r, px + r, py + r,
                                    outline=self.COLORS["intersection"],
                                    fill=self.COLORS["intersection"],
                                    width=2, tags="intersections")
            self.canvas.create_text(px + 10, py - 10,
                                    text=f"({px},{py})",
                                    fill=self.COLORS["intersection"],
                                    font=("Courier", 8), tags="intersections")
        if self.check_point:
            x, y = self.check_point
            inside_any = any(point_in_polygon(self.check_point, p) for p in self.polygons)
            color = self.COLORS["point_inside"] if inside_any else self.COLORS["point_outside"]
            self.canvas.create_oval(x - 6, y - 6, x + 6, y + 6,
                                    outline=color, fill=color + "88", width=2)
            self.canvas.create_text(x + 12, y - 10,
                                    text="✔ inside" if inside_any else "✘ outside",
                                    fill=color, font=("Courier", 9, "bold"), anchor="w")

    def _draw_lines(self):
        for seg in self.lines:
            p1, p2 = seg
            # Bresenham
            pts = bresenham(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]))
            # Draw as one canvas line (visual; Bresenham confirms pixel-level)
            self.canvas.create_line(p1[0], p1[1], p2[0], p2[1],
                                    fill=self.COLORS["line"], width=2)
            # Draw endpoints
            for ep in (p1, p2):
                self.canvas.create_oval(ep[0] - 3, ep[1] - 3, ep[0] + 3, ep[1] + 3,
                                        fill=self.COLORS["line"], outline="")

    def _draw_polygons(self):
        for idx, poly in enumerate(self.polygons):
            flat = [c for pt in poly for c in pt]
            # Fill
            self.canvas.create_polygon(flat, fill=self.COLORS["polygon_fill"],
                                       outline="")
            # Edges
            n = len(poly)
            for i in range(n):
                a = poly[i]
                b = poly[(i + 1) % n]
                self.canvas.create_line(a[0], a[1], b[0], b[1],
                                        fill=self.COLORS["polygon"], width=2)
            # Vertices
            for pt in poly:
                self.canvas.create_oval(pt[0] - 4, pt[1] - 4, pt[0] + 4, pt[1] + 4,
                                        fill=self.COLORS["vertex"],
                                        outline=self.COLORS["polygon"], width=2)
            # Label
            cx = sum(p[0] for p in poly) / n
            cy = sum(p[1] for p in poly) / n
            conv = is_convex(poly)
            label = f"P{idx+1} {'◈' if conv else '◇'}"
            self.canvas.create_text(cx, cy, text=label,
                                    fill=self.COLORS["polygon"],
                                    font=("Courier", 9, "bold"))
            # Normals
            if self.show_normals.get():
                normals = inward_normals(poly)
                for i, norm in enumerate(normals):
                    a = poly[i]
                    b = poly[(i + 1) % n]
                    mx = (a[0] + b[0]) / 2
                    my = (a[1] + b[1]) / 2
                    length = 24
                    ex = mx + norm[0] * length
                    ey = my + norm[1] * length
                    self.canvas.create_line(mx, my, ex, ey,
                                            fill=self.COLORS["normal"], width=1,
                                            arrow=tk.LAST, arrowshape=(8, 10, 3))

    def _draw_in_progress_polygon(self):
        pts = self.polygon_points
        color = self.COLORS["polygon"]
        for i in range(len(pts) - 1):
            self.canvas.create_line(pts[i][0], pts[i][1],
                                    pts[i+1][0], pts[i+1][1],
                                    fill=color, width=2, dash=(6, 3))
        for pt in pts:
            self.canvas.create_oval(pt[0] - 4, pt[1] - 4, pt[0] + 4, pt[1] + 4,
                                    fill=self.COLORS["vertex"],
                                    outline=color, width=2)
        if len(pts) >= 2 and self.preview_pos:
            self.canvas.create_line(pts[-1][0], pts[-1][1],
                                    self.preview_pos[0], self.preview_pos[1],
                                    fill=self.COLORS["preview"], width=1, dash=(4, 4))

    def _draw_hull(self):
        if not self.hull_polygon or len(self.hull_polygon) < 2:
            return
        color = (self.COLORS["hull_graham"] if self.hull_method == "Graham"
                 else self.COLORS["hull_jarvis"])
        hull = self.hull_polygon
        flat = [c for pt in hull for c in pt]
        self.canvas.create_polygon(flat, outline=color,
                                   fill=color, width=2, dash=(8, 4))
        for i, pt in enumerate(hull):
            self.canvas.create_oval(pt[0] - 5, pt[1] - 5, pt[0] + 5, pt[1] + 5,
                                    fill=color, outline="white", width=1)
            self.canvas.create_text(pt[0] + 8, pt[1] - 8,
                                    text=str(i + 1), fill=color,
                                    font=("Courier", 8, "bold"))
        # Label
        cx = sum(p[0] for p in hull) / len(hull)
        cy = sum(p[1] for p in hull) / len(hull)
        self.canvas.create_text(cx, cy,
                                text=f"Hull ({self.hull_method})",
                                fill=color, font=("Courier", 9, "bold"))

    # ── Misc ──────────────────────────────────────────────────────────────

    def _clear_all(self):
        self.polygons.clear()
        self.polygon_points.clear()
        self.lines.clear()
        self.line_points.clear()
        self.hull_polygon = None
        self.hull_method = None
        self.check_point = None
        self.intersections.clear()
        self.canvas.delete("all")
        self._draw_grid()
        self.status_var.set("Холст очищен.")


# ─────────────────────────── Entry point ─────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app = PolygonEditor(root)

    def on_resize(event):
        app._draw_grid()

    root.bind("<Configure>", on_resize)
    root.mainloop()
