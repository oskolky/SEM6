import tkinter as tk
import math

#НАСТРОЙКИ

WIDTH = 1600
HEIGHT = 900

ORIGIN_X = WIDTH // 2
ORIGIN_Y = HEIGHT // 2

current_algorithm = "DDA"
debug_mode = False
start_point = None
is_drawing = False
after_id = None

#АЛГОРИТМЫ

def dda_line(x1, y1, x2, y2):
    points = []

    length = max(abs(x2 - x1), abs(y2 - y1))

    if length == 0:
        return [(x1, y1)]

    dx = (x2 - x1)/length
    dy = (y2 - y1)/length

    for p in range(length + 1):
        points.append((round(x1), round(y1)))
        x1 += dx
        y1 += dy

    return points


def bresenham_line(x1, y1, x2, y2):
    points = []

    dx = abs(x2 - x1)
    dy = abs(y2 - y1)

    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1

    err = dx - dy

    while True:
        points.append((x1, y1))

        if x1 == x2 and y1 == y2:
            break

        e2 = 2 * err

        if e2 > -dy:
            err -= dy
            x1 += sx

        if e2 < dx:
            err += dx
            y1 += sy

    return points


def wu_line(x1, y1, x2, y2):
    points = []

    def main_fade(x):
        return x - math.floor(x)

    def sec_fade(x):
        return 1 - main_fade(x)

    steep = abs(y2 - y1) > abs(x2 - x1)

    if steep:
        x1, y1 = y1, x1
        x2, y2 = y2, x2

    if x1 > x2:
        x1, x2 = x2, x1
        y1, y2 = y2, y1

    dx = x2 - x1
    dy = y2 - y1

    gradient = dy / dx if dx != 0 else 1

    y = y1 + gradient * (round(x1) - x1)

    for x in range(round(x1), round(x2) + 1):

        brightness1 = sec_fade(y)
        brightness2 = main_fade(y)

        if steep:
            points.append((int(y), x, brightness1))
            points.append((int(y)+1, x, brightness2))
        else:
            points.append((x, int(y), brightness1))
            points.append((x, int(y)+1, brightness2))

        y += gradient

    return points

def bresenham_circle(xc, yc, R):
    points = []

    x = 0
    y = R

    delta = 2*(1 - R)

    while y >= 0:

        #8 точек
        points.append((xc + x, yc + y))
        points.append((xc - x, yc + y))
        points.append((xc + x, yc - y))
        points.append((xc - x, yc - y))

        points.append((xc + y, yc + x))
        points.append((xc - y, yc + x))
        points.append((xc + y, yc - x))
        points.append((xc - y, yc - x))


        if delta < 0:
            #внутри окружности
            sigma = 2 * delta + 2 * y - 1

            if sigma <= 0:
                x += 1
                delta += 2 * x + 1
            else:
                x += 1
                y -= 1
                delta += 2 * (x - y + 1)

        elif delta > 0:
            #вне окружности
            sigma = 2 * delta - 2 * x - 1

            if sigma <= 0:
                x += 1
                y -= 1
                delta += 2 * (x - y + 1)
            else:
                y -= 1
                delta += -2 * y + 1

        else:
            #на окружности
            x += 1
            y -= 1
            delta += 2 * (x - y + 1)

    return points

def midpoint_ellipse(xc, yc, a, b):
    points = []

    x = 0
    y = b

    a2 = a * a
    b2 = b * b

    dx = 2 * b2 * x
    dy = 2 * a2 * y

    d1 = b2 - a2 * b + 0.25 * a2

    while dx < dy:
        points.append((xc + x, yc + y))
        points.append((xc - x, yc + y))
        points.append((xc + x, yc - y))
        points.append((xc - x, yc - y))

        if d1 < 0:
            x += 1
            dx += 2 * b2
            d1 += dx + b2
        else:
            x += 1
            y -= 1
            dx += 2 * b2
            dy -= 2 * a2
            d1 += dx - dy + b2

    d2 = b2 * (x + 0.5)**2 + a2 * (y - 1)**2 - a2 * b2

    while y >= 0:
        points.append((xc + x, yc + y))
        points.append((xc - x, yc + y))
        points.append((xc + x, yc - y))
        points.append((xc - x, yc - y))

        if d2 > 0:
            y -= 1
            dy -= 2 * a2
            d2 += a2 - dy
        else:
            y -= 1
            x += 1
            dx += 2 * b2
            dy -= 2 * a2
            d2 += dx - dy + a2

    return points


def draw_parabola(xc, yc, a, limit=400):
    points = []
    for x in range(-limit, limit + 1):
        y = (x * x) // (4 * a)
        points.append((xc + x, yc + y))
        points.append((xc - x, yc + y))
    return points

def draw_hyperbola(xc, yc, a, b, limit=1600):
    points = []

    for x in range(a, limit):
        y = int(b * math.sqrt((x*x)/(a*a) - 1))

        points.append((xc + x, yc + y))
        points.append((xc + x, yc - y))
        points.append((xc - x, yc + y))
        points.append((xc - x, yc - y))

    return points

#ОТРИСОВКА

def draw_axes():
    canvas.create_line(ORIGIN_X, 0, ORIGIN_X, HEIGHT, fill="black", width=2)
    canvas.create_line(0, ORIGIN_Y, WIDTH, ORIGIN_Y, fill="black", width=2)


def draw_pixel(x, y, brightness=1.0):

    screen_x = ORIGIN_X + x
    screen_y = ORIGIN_Y - y

    if screen_x < 0 or screen_y < 0 or screen_x >= WIDTH or screen_y >= HEIGHT:
        return

    gray = int(255 * (1 - brightness))
    color = f"#{gray:02x}{gray:02x}{gray:02x}"

    canvas.create_line(
        screen_x,
        screen_y,
        screen_x + 1,
        screen_y,
        fill=color
    )


def draw_line(x1, y1, x2, y2):

    global is_drawing

    if current_algorithm == "DDA":
        points = [(x, y, 1) for x, y in dda_line(x1, y1, x2, y2)]

    elif current_algorithm == "Bresenham":
        points = [(x, y, 1) for x, y in bresenham_line(x1, y1, x2, y2)]

    elif current_algorithm == "Wu":
        points = wu_line(x1, y1, x2, y2)

    elif current_algorithm == "Circle":
        radius = int((x1**2 + y1**2) ** 0.5)
        points = [(px, py, 1) for px, py in bresenham_circle(0, 0, radius)]

    elif current_algorithm == "Ellipse":
        a = abs(x1)
        b = abs(y1)
        points = [(px, py, 1) for px, py in midpoint_ellipse(0, 0, a, b)]


    elif current_algorithm == "Parabola":
        a = max(1, abs(x1))
        points = [(px, py, 1) for px, py in draw_parabola(0, 0, a)]

    elif current_algorithm == "Hyperbola":
        a = max(1, abs(x1))
        b = max(1, abs(y1))
        points = [(px, py, 1) for px, py in draw_hyperbola(0, 0, a, b)]
    else:
        return

    if not debug_mode:
        for x, y, bright in points:
            draw_pixel(x, y, bright)
    else:
        is_drawing = True
        draw_debug(points, 0)


def draw_debug(points, index):

    global is_drawing, after_id

    if not is_drawing:
        return

    if index >= len(points):
        is_drawing = False
        return

    x, y, bright = points[index]
    draw_pixel(x, y, bright)

    after_id = root.after(10, lambda: draw_debug(points, index + 1))

#КЛИК

def on_click(event):
    global start_point, is_drawing, after_id

    math_x = event.x - ORIGIN_X
    math_y = ORIGIN_Y - event.y

    if is_drawing:
        is_drawing = False
        if after_id:
            root.after_cancel(after_id)

    if start_point is None:
        start_point = (math_x, math_y)
    else:
        draw_line(start_point[0], start_point[1], math_x, math_y)
        start_point = None


#ПЕРЕКЛЮЧЕНИЕ

def set_algorithm(name):
    global current_algorithm
    current_algorithm = name


def toggle_debug():
    global debug_mode
    debug_mode = not debug_mode


def clear_canvas():
    canvas.delete("all")
    draw_axes()


#ИНТЕРФЕЙС

root = tk.Tk()
root.title("Графический редактор")

canvas = tk.Canvas(
    root,
    width=WIDTH,
    height=HEIGHT,
    bg="white"
)
canvas.pack()

draw_axes()

canvas.bind("<Button-1>", on_click)

toolbar = tk.Frame(root)
toolbar.pack()
tk.Button(toolbar, text="Ву", command=lambda: set_algorithm("Wu")).pack(side=tk.LEFT)
tk.Button(toolbar, text="ЦДА", command=lambda: set_algorithm("DDA")).pack(side=tk.LEFT)
tk.Button(toolbar, text="Брезенхем", command=lambda: set_algorithm("Bresenham")).pack(side=tk.LEFT)
tk.Button(toolbar, text="Окружность", command=lambda: set_algorithm("Circle")).pack(side=tk.LEFT)
tk.Button(toolbar, text="Эллипс", command=lambda: set_algorithm("Ellipse")).pack(side=tk.LEFT)
tk.Button(toolbar, text="Парабола", command=lambda: set_algorithm("Parabola")).pack(side=tk.LEFT)
tk.Button(toolbar, text="Гипербола", command=lambda: set_algorithm("Hyperbola")).pack(side=tk.LEFT)
tk.Button(toolbar, text="Отладка", command=toggle_debug).pack(side=tk.LEFT)
tk.Button(toolbar, text="Очистить", command=clear_canvas).pack(side=tk.LEFT)

root.mainloop()