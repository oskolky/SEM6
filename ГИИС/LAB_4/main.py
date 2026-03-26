import pygame
import math
import sys

def mat4_identity():
    return [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]

def mat4_mul(A,B):
    return [[sum(A[i][k]*B[k][j] for k in range(4)) for j in range(4)] for i in range(4)]

def mat4_vec_mul(M,v):
    return [sum(M[i][j]*v[j] for j in range(4)) for i in range(4)]

def translation_matrix(dx,dy,dz):
    return [[1,0,0,dx],[0,1,0,dy],[0,0,1,dz],[0,0,0,1]]

def scaling_matrix(sx,sy,sz):
    return [[sx,0,0,0],[0,sy,0,0],[0,0,sz,0],[0,0,0,1]]

def rotation_x_matrix(a):
    c,s=math.cos(a),math.sin(a)
    return [[1,0,0,0],[0,c,-s,0],[0,s,c,0],[0,0,0,1]]

def rotation_y_matrix(a):
    c,s=math.cos(a),math.sin(a)
    return [[c,0,s,0],[0,1,0,0],[-s,0,c,0],[0,0,0,1]]

def rotation_z_matrix(a):
    c,s=math.cos(a),math.sin(a)
    return [[c,-s,0,0],[s,c,0,0],[0,0,1,0],[0,0,0,1]]

def reflection_x_matrix():
    return [[-1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
def reflection_y_matrix():
    return [[1,0,0,0],[0,-1,0,0],[0,0,1,0],[0,0,0,1]]
def reflection_z_matrix():
    return [[1,0,0,0],[0,1,0,0],[0,0,-1,0],[0,0,0,1]]

def perspective_matrix(fov_deg,aspect,near,far):
    f=1/math.tan(math.radians(fov_deg)/2)
    return [[f/aspect,0,0,0],[0,f,0,0],[0,0,(far+near)/(near-far),(2*far*near)/(near-far)],[0,0,-1,0]]

def orthographic_matrix(l,r,b,t,n,f):
    return [[2/(r-l),0,0,-(r+l)/(r-l)],[0,2/(t-b),0,-(t+b)/(t-b)],[0,0,-2/(f-n),-(f+n)/(f-n)],[0,0,0,1]]

def load_object(filename):
    vertices,edges=[],[]
    with open(filename,'r') as f:
        for line in f:
            line=line.strip()
            if not line or line[0]=='#': continue
            parts=line.split()
            if parts[0]=='v': vertices.append([float(parts[1]),float(parts[2]),float(parts[3])])
            elif parts[0]=='e': edges.append((int(parts[1]),int(parts[2])))
    return vertices,edges

def print_help():
    global use_perspective_global
    print("\n=== 3D ТРАНСФОРМАЦИИ ===")
    print("← → ↑ ↓ : перемещение X,Y   Q/E : перемещение Z")
    print("W/S X ось, A/D Y ось, Z/C Z ось - вращение")
    print("+/- : масштаб    X/Y/Z : отражение")
    print("P : переключение перспективы    R : сброс")
    print("H : справка, ESC : выход")
    print(f"Текущая проекция: {'Перспектива' if use_perspective_global else 'Ортографическая'}\n")

use_perspective_global=True

def main():
    global use_perspective_global
    if len(sys.argv)!=2:
        print("Использование: python 3d_transform.py <файл_объекта>")
        sys.exit(1)
    filename=sys.argv[1]
    vertices,edges=load_object(filename)
    if not vertices: sys.exit("Файл не содержит вершин.")
    print(f"Загружен объект: {filename}, Вершин: {len(vertices)}, Рёбер: {len(edges)}")
    print_help()

    pygame.init()
    w,h=800,600
    screen=pygame.display.set_mode((w,h))
    pygame.display.set_caption("3D Transformations")
    clock=pygame.time.Clock()
    BLACK=(0,0,0);WHITE=(255,255,255);YELLOW=(255,255,0)
    model=mat4_identity()
    view=translation_matrix(0,0,-5)
    use_perspective=True
    use_perspective_global=True
    fov=60;aspect=w/h;near=0.1;far=100
    ortho=(-2,2,-2,2,0.1,100)
    font=pygame.font.Font(None,24)
    message="";message_timer=0
    def show_message(msg,duration=60): nonlocal message,message_timer;message=msg;message_timer=duration
    def get_proj(): return perspective_matrix(fov,aspect,near,far) if use_perspective else orthographic_matrix(*ortho)

    running=True
    while running:
        for event in pygame.event.get():
            if event.type==pygame.QUIT: running=False
            elif event.type==pygame.KEYDOWN:
                k=event.key
                if k==pygame.K_LEFT: model=mat4_mul(translation_matrix(-0.1,0,0),model); show_message("← X")
                elif k==pygame.K_RIGHT: model=mat4_mul(translation_matrix(0.1,0,0),model); show_message("→ X")
                elif k==pygame.K_UP: model=mat4_mul(translation_matrix(0,0.1,0),model); show_message("↑ Y")
                elif k==pygame.K_DOWN: model=mat4_mul(translation_matrix(0,-0.1,0),model); show_message("↓ Y")
                elif k==pygame.K_q: model=mat4_mul(translation_matrix(0,0,-0.1),model); show_message("Z")
                elif k==pygame.K_e: model=mat4_mul(translation_matrix(0,0,0.1),model); show_message("Z")
                elif k==pygame.K_w: model=mat4_mul(rotation_x_matrix(math.radians(5)),model); show_message("X+")
                elif k==pygame.K_s: model=mat4_mul(rotation_x_matrix(math.radians(-5)),model); show_message("X-")
                elif k==pygame.K_a: model=mat4_mul(rotation_y_matrix(math.radians(5)),model); show_message("Y+")
                elif k==pygame.K_d: model=mat4_mul(rotation_y_matrix(math.radians(-5)),model); show_message("Y-")
                elif k==pygame.K_z: model=mat4_mul(rotation_z_matrix(math.radians(5)),model); show_message("Z+")
                elif k==pygame.K_c: model=mat4_mul(rotation_z_matrix(math.radians(-5)),model); show_message("Z-")
                elif k==pygame.K_PLUS or k==pygame.K_EQUALS: model=mat4_mul(scaling_matrix(1.1,1.1,1.1),model); show_message("+")
                elif k==pygame.K_MINUS: model=mat4_mul(scaling_matrix(0.9,0.9,0.9),model); show_message("-")
                elif k==pygame.K_x: model=mat4_mul(reflection_x_matrix(),model); show_message("X-reflection")
                elif k==pygame.K_y: model=mat4_mul(reflection_y_matrix(),model); show_message("Y-reflection")
                elif k==pygame.K_p: use_perspective=not use_perspective; use_perspective_global=use_perspective; show_message("Проекция переключена")
                elif k==pygame.K_r: model=mat4_identity(); show_message("Сброс")
                elif k==pygame.K_h: print_help(); show_message("Справка в консоли",120)
                elif k==pygame.K_ESCAPE: running=False

        screen.fill(BLACK)
        proj=get_proj()
        mvp=mat4_mul(proj,mat4_mul(view,model))
        screen_v=[]
        for v in vertices:
            v_h=[v[0],v[1],v[2],1]
            v_clip=mat4_vec_mul(mvp,v_h)
            if v_clip[3]!=0: ndc=[v_clip[0]/v_clip[3],v_clip[1]/v_clip[3],v_clip[2]/v_clip[3]]
            else: ndc=[0,0,0]
            sx=int((ndc[0]+1)*w/2)
            sy=int((1-ndc[1])*h/2)
            screen_v.append((sx,sy))
        for i,j in edges:
            if i<len(screen_v) and j<len(screen_v): pygame.draw.line(screen,WHITE,screen_v[i],screen_v[j],2)
        proj_text="Перспектива" if use_perspective else "Ортографическая"
        screen.blit(font.render(f"Проекция: {proj_text}  |  H - справка",True,YELLOW),(10,10))
        if message_timer>0:
            msg_surf=font.render(message,True,YELLOW)
            msg_rect=msg_surf.get_rect(center=(w//2,h-30))
            screen.blit(msg_surf,msg_rect)
            message_timer-=1
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()

if __name__=="__main__":
    main()