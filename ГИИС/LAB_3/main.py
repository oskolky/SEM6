import tkinter as tk

WIDTH = 1200
HEIGHT = 800

ORIGIN_X = WIDTH // 2
ORIGIN_Y = HEIGHT // 2

current_curve_type = "Bezier"

finished_curves = []
control_points = []

selected_point = None


# -------- МАТРИЦЫ --------

def mat_vec_mul(M, v):

    result = [0]*len(M)

    for i in range(len(M)):
        for j in range(len(v)):
            result[i] += M[i][j] * v[j]

    return result


# -------- КРИВЫЕ --------

def hermite_curve(p0,p1,r0,r1,steps=500):

    M = [
        [2,-2,1,1],
        [-3,3,-2,-1],
        [0,0,1,0],
        [1,0,0,0]
    ]

    Gx=[p0[0],p1[0],r0[0],r1[0]]
    Gy=[p0[1],p1[1],r0[1],r1[1]]

    points=[]

    for i in range(steps+1):

        t=i/steps
        T=[t**3,t**2,t,1]

        ax=mat_vec_mul(M,Gx)
        ay=mat_vec_mul(M,Gy)

        x=sum(T[j]*ax[j] for j in range(4))
        y=sum(T[j]*ay[j] for j in range(4))

        points.append((x,y))

    return points


def bezier_curve(p0,p1,p2,p3,steps=500):

    M = [
        [-1,3,-3,1],
        [3,-6,3,0],
        [-3,3,0,0],
        [1,0,0,0]
    ]

    Gx=[p0[0],p1[0],p2[0],p3[0]]
    Gy=[p0[1],p1[1],p2[1],p3[1]]

    points=[]

    for i in range(steps+1):

        t=i/steps
        T=[t**3,t**2,t,1]

        ax=mat_vec_mul(M,Gx)
        ay=mat_vec_mul(M,Gy)

        x=sum(T[j]*ax[j] for j in range(4))
        y=sum(T[j]*ay[j] for j in range(4))

        points.append((x,y))

    return points


def bspline_curve(p0,p1,p2,p3,steps=500):

    M=[
        [-1/6,3/6,-3/6,1/6],
        [3/6,-6/6,3/6,0],
        [-3/6,0,3/6,0],
        [1/6,4/6,1/6,0]
    ]

    Gx=[p0[0],p1[0],p2[0],p3[0]]
    Gy=[p0[1],p1[1],p2[1],p3[1]]

    points=[]

    for i in range(steps+1):

        t=i/steps
        T=[t**3,t**2,t,1]

        ax=mat_vec_mul(M,Gx)
        ay=mat_vec_mul(M,Gy)

        x=sum(T[j]*ax[j] for j in range(4))
        y=sum(T[j]*ay[j] for j in range(4))

        points.append((x,y))

    return points


# -------- ГЕНЕРАЦИЯ КРИВОЙ --------

def generate_curve(points):

    segments=[]

    if current_curve_type=="Bezier":

        if len(points)<4:
            return []

        for i in range(0,len(points)-3,3):

            p0,p1,p2,p3=points[i:i+4]
            segments += bezier_curve(p0,p1,p2,p3)


    elif current_curve_type=="B-spline":

        if len(points)<4:
            return []

        for i in range(len(points)-3):

            p0,p1,p2,p3=points[i:i+4]
            segments += bspline_curve(p0,p1,p2,p3)


    elif current_curve_type=="Hermite":

        for i in range(len(points)-1):

            p0=points[i]
            p1=points[i+1]

            if i==0:
                r0=(points[i+1][0]-points[i][0],
                    points[i+1][1]-points[i][1])
            else:
                r0=((points[i+1][0]-points[i-1][0])/2,
                    (points[i+1][1]-points[i-1][1])/2)

            if i==len(points)-2:
                r1=(points[i+1][0]-points[i][0],
                    points[i+1][1]-points[i][1])
            else:
                r1=((points[i+2][0]-points[i][0])/2,
                    (points[i+2][1]-points[i][1])/2)

            segments += hermite_curve(p0,p1,r0,r1)

    return segments


# -------- ОТРИСОВКА --------

def draw_axes():

    canvas.create_line(ORIGIN_X,0,ORIGIN_X,HEIGHT,width=2)
    canvas.create_line(0,ORIGIN_Y,WIDTH,ORIGIN_Y,width=2)


def draw_pixel(x,y):

    sx=ORIGIN_X+x
    sy=ORIGIN_Y-y

    canvas.create_line(sx,sy,sx+1,sy)


def redraw():

    canvas.delete("all")

    draw_axes()

    for curve in finished_curves:
        for x,y in curve:
            draw_pixel(int(x),int(y))

    temp_curve=generate_curve(control_points)

    for x,y in temp_curve:
        draw_pixel(int(x),int(y))

    for x,y in control_points:

        sx=ORIGIN_X+x
        sy=ORIGIN_Y-y

        canvas.create_oval(
            sx-4,sy-4,
            sx+4,sy+4,
            fill="red"
        )


# -------- ПОИСК ТОЧКИ --------

def find_point(x,y):

    for i,(px,py) in enumerate(control_points):

        if abs(px-x)<10 and abs(py-y)<10:
            return i

    return None


# -------- МЫШЬ --------

def on_click(event):

    global selected_point

    x=event.x-ORIGIN_X
    y=ORIGIN_Y-event.y

    idx=find_point(x,y)

    if idx is not None:
        selected_point=idx
    else:
        control_points.append((x,y))

    redraw()


def on_drag(event):

    global selected_point

    if selected_point is None:
        return

    x=event.x-ORIGIN_X
    y=ORIGIN_Y-event.y

    control_points[selected_point]=(x,y)

    redraw()


def on_release(event):

    global selected_point
    selected_point=None


# -------- UI --------

def new_curve():

    global control_points

    curve=generate_curve(control_points)

    if curve:
        finished_curves.append(curve)

    control_points=[]

    redraw()


def set_curve(name):

    global current_curve_type
    current_curve_type=name

    redraw()


def clear_all():

    global finished_curves,control_points

    finished_curves=[]
    control_points=[]

    redraw()


root=tk.Tk()
root.title("Parametric Curves")

canvas=tk.Canvas(root,width=WIDTH,height=HEIGHT,bg="white")
canvas.pack()

draw_axes()

canvas.bind("<Button-1>",on_click)
canvas.bind("<B1-Motion>",on_drag)
canvas.bind("<ButtonRelease-1>",on_release)

toolbar=tk.Frame(root)
toolbar.pack()

tk.Button(toolbar,text="Bezier",command=lambda:set_curve("Bezier")).pack(side=tk.LEFT)
tk.Button(toolbar,text="B-spline",command=lambda:set_curve("B-spline")).pack(side=tk.LEFT)
tk.Button(toolbar,text="Hermite",command=lambda:set_curve("Hermite")).pack(side=tk.LEFT)

tk.Button(toolbar,text="New Curve",command=new_curve).pack(side=tk.LEFT)
tk.Button(toolbar,text="Clear",command=clear_all).pack(side=tk.LEFT)

root.mainloop()