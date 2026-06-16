from ursina import *
import cv2
import mediapipe as mp
import math
import random

# ==========================================
# 1. SETUP VISI KOMPUTER
# ==========================================
import urllib.request
import os
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

model_path = 'hand_landmarker.task'
if not os.path.exists(model_path):
    print("Mengunduh model MediaPipe Hand Landmarker...")
    urllib.request.urlretrieve("https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task", model_path)

base_options = mp_python.BaseOptions(model_asset_path=model_path)
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    num_hands=2,
    min_hand_detection_confidence=0.7,
    min_hand_presence_confidence=0.7,
    min_tracking_confidence=0.7)
detector = vision.HandLandmarker.create_from_options(options)

cap = cv2.VideoCapture(0)

# ==========================================
# 2. SETUP LINGKUNGAN 3D (URSINA)
# ==========================================
app = Ursina()
rubik_parent = Entity()
rotation_pivot = Entity(parent=rubik_parent)
cubies = []

# Status Mesin (State Machine)
is_rotating = False
is_cam_rotating = False
is_system_busy = False

# State Variabel Gestur (Kanan & Kiri)
pinch_active_r = False
pinch_start_r = (0, 0)
pinch_active_l = False
pinch_start_l = (0, 0)
double_fist_active = False
double_fist_start = (0, 0)

# Struktur Data Stack (Teori Graf)
history_stack = []

# Membangun bentuk Rubik 3x3x3
for x in range(-1, 2):
    for y in range(-1, 2):
        for z in range(-1, 2):
            if x == 0 and y == 0 and z == 0: continue

            cubie = Entity(parent=rubik_parent, position=(x, y, z))
            Entity(parent=cubie, model='cube', color=color.black, scale=0.95)

            if x == 1: Entity(parent=cubie, model='cube', color=color.red, position=(0.5, 0, 0), scale=(0.05, 0.85, 0.85))
            if x == -1: Entity(parent=cubie, model='cube', color=color.orange, position=(-0.5, 0, 0), scale=(0.05, 0.85, 0.85))
            if y == 1: Entity(parent=cubie, model='cube', color=color.white, position=(0, 0.5, 0), scale=(0.85, 0.05, 0.85))
            if y == -1: Entity(parent=cubie, model='cube', color=color.yellow, position=(0, -0.5, 0), scale=(0.85, 0.05, 0.85))
            if z == 1: Entity(parent=cubie, model='cube', color=color.blue, position=(0, 0, 0.5), scale=(0.85, 0.85, 0.05))
            if z == -1: Entity(parent=cubie, model='cube', color=color.green, position=(0, 0, -0.5), scale=(0.85, 0.85, 0.05))
            cubies.append(cubie)

camera.position = (0, 0, -10)

# ==========================================
# 3. ALGORITMA VIEW-RELATIVE MAPPING
# ==========================================
def get_local_layer_for_visual(visual_side):
    """ Mencari sisi lokal Rubik mana yang sedang menghadap ke sisi visual kamera """
    faces = {
        ('x', 1): rubik_parent.right,
        ('x', -1): rubik_parent.left,
        ('y', 1): rubik_parent.up,
        ('y', -1): rubik_parent.down,
        ('z', 1): rubik_parent.back,
        ('z', -1): rubik_parent.forward
    }

    best_layer = None
    max_val = -9999

    for layer, vec in faces.items():
        if visual_side == 'R': val = vec.x
        elif visual_side == 'L': val = -vec.x
        elif visual_side == 'U': val = vec.y
        elif visual_side == 'D': val = -vec.y

        if val > max_val:
            max_val = val
            best_layer = layer

    return best_layer

def handle_swipe(visual_face, swipe_dir):
    """ Menerjemahkan geseran layar (2D) ke rotasi sumbu lokal Rubik (3D) """
    local_layer = get_local_layer_for_visual(visual_face)
    local_axis, slice_val = local_layer

    # Menentukan Sumbu Putar Global (X atau Y)
    global_axis_vec = Vec3(1,0,0) if visual_face in ['R', 'L'] else Vec3(0,1,0)

    # Menentukan Arah Putaran Global (+ atau -)
    if visual_face in ['R', 'L']: global_dir = -1 if swipe_dir == 'UP' else 1
    else: global_dir = 1 if swipe_dir == 'LEFT' else -1

    # Menyelaraskan Arah Global dengan Sumbu Lokal
    if local_axis == 'x': local_axis_vec = rubik_parent.right
    elif local_axis == 'y': local_axis_vec = rubik_parent.up
    elif local_axis == 'z': local_axis_vec = rubik_parent.back

    alignment = round(local_axis_vec.dot(global_axis_vec))
    local_dir = int(global_dir * alignment)

    rotate_layer(local_axis, slice_val, local_dir, record_history=True)

# ==========================================
# 4. LOGIKA ROTASI & SISTEM ANTREAN
# ==========================================
def rotate_layer(axis, slice_val, direction, record_history=True):
    global is_rotating
    is_rotating = True

    if record_history: history_stack.append((axis, slice_val, direction))

    for c in cubies:
        if axis == 'x' and round(c.x) == slice_val: c.world_parent = rotation_pivot
        elif axis == 'y' and round(c.y) == slice_val: c.world_parent = rotation_pivot
        elif axis == 'z' and round(c.z) == slice_val: c.world_parent = rotation_pivot

    if axis == 'x': rotation_pivot.animate_rotation_x(rotation_pivot.rotation_x + (90 * direction), duration=0.25)
    elif axis == 'y': rotation_pivot.animate_rotation_y(rotation_pivot.rotation_y + (90 * direction), duration=0.25)
    elif axis == 'z': rotation_pivot.animate_rotation_z(rotation_pivot.rotation_z + (90 * direction), duration=0.25)

    invoke(reset_pivot, delay=0.3)

def reset_pivot():
    global is_rotating
    for c in cubies:
        if c.parent == rotation_pivot:
            c.world_parent = rubik_parent
            c.x, c.y, c.z = round(c.x), round(c.y), round(c.z)
    rotation_pivot.rotation = (0, 0, 0)
    is_rotating = False

def snap_rubik(axis, angle):
    global is_cam_rotating
    is_cam_rotating = True
    if axis == 'y': rubik_parent.animate_rotation_y(rubik_parent.rotation_y + angle, duration=0.3)
    elif axis == 'x': rubik_parent.animate_rotation_x(rubik_parent.rotation_x + angle, duration=0.3)
    invoke(reset_cam_rotating, delay=0.35)

def reset_cam_rotating():
    global is_cam_rotating
    is_cam_rotating = False
    # Kunci rotasi ke 90 derajat agar selalu rapi
    rubik_parent.rotation_x = round(rubik_parent.rotation_x / 90) * 90
    rubik_parent.rotation_y = round(rubik_parent.rotation_y / 90) * 90
    rubik_parent.rotation_z = round(rubik_parent.rotation_z / 90) * 90

# --- FITUR OTOMATIS BERBASIS REKURSIF ---
def process_shuffle(steps_left):
    global is_system_busy
    if steps_left == 0:
        is_system_busy = False
        return
    moves = [('x', 1, 1), ('x', 1, -1), ('x', -1, 1), ('x', -1, -1),
             ('y', 1, 1), ('y', 1, -1), ('y', -1, 1), ('y', -1, -1),
             ('z', 1, 1), ('z', 1, -1), ('z', -1, 1), ('z', -1, -1)]
    move = random.choice(moves)
    rotate_layer(move[0], move[1], move[2], record_history=True)
    invoke(process_shuffle, steps_left - 1, delay=0.35)

def auto_shuffle():
    global is_system_busy
    if is_system_busy or is_rotating or is_cam_rotating: return
    is_system_busy = True
    process_shuffle(15)

def process_solve():
    global is_system_busy
    if len(history_stack) == 0:
        is_system_busy = False
        return
    axis, slice_val, direction = history_stack.pop()
    rotate_layer(axis, slice_val, direction * -1, record_history=False)
    invoke(process_solve, delay=0.35)

def auto_solve():
    global is_system_busy
    if is_system_busy or is_rotating or is_cam_rotating or len(history_stack) == 0: return
    is_system_busy = True
    process_solve()

def input(key):
    if key == 's': auto_shuffle()
    if key == 'a': auto_solve()

# ==========================================
# 5. FUNGSI UPDATE (SENSOR KAMERA & GESTUR)
# ==========================================
def update():
    global pinch_active_r, pinch_start_r, pinch_active_l, pinch_start_l
    global double_fist_active, double_fist_start

    success, img = cap.read()
    if success:
        img = cv2.flip(img, 1)
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=imgRGB)
        results = detector.detect(mp_image)

        is_fist_r = False
        is_fist_l = False
        wrist_pos_r = (0, 0)
        wrist_pos_l = (0, 0)

        # 1. Parsing Status Kepalan Kedua Tangan
        if results.hand_landmarks and results.handedness:
            for hand_landmarks, handedness in zip(results.hand_landmarks, results.handedness):
                label = handedness[0].category_name
                hand_type = "Kanan" if label == "Left" else "Kiri"

                wrist = hand_landmarks[0]
                middle_tip = hand_landmarks[12]
                fist_dist = math.hypot(wrist.x - middle_tip.x, wrist.y - middle_tip.y)

                if fist_dist < 0.15: # Ambang batas mengepal
                    if hand_type == "Kanan":
                        is_fist_r = True
                        wrist_pos_r = (wrist.x, wrist.y)
                    else:
                        is_fist_l = True
                        wrist_pos_l = (wrist.x, wrist.y)

        # 2. Logika Gestur (Hanya aktif saat sistem tidak sedang Auto-Solve)
        if not is_system_busy and results.hand_landmarks:

            # KEPALAN GANDA (Double Fist) -> Rotasi Keseluruhan Rubik
            if is_fist_r and is_fist_l:
                avg_x = (wrist_pos_r[0] + wrist_pos_l[0]) / 2
                avg_y = (wrist_pos_r[1] + wrist_pos_l[1]) / 2

                if not double_fist_active:
                    double_fist_active = True
                    double_fist_start = (avg_x, avg_y)
                elif not is_cam_rotating and not is_rotating:
                    delta_x = avg_x - double_fist_start[0]
                    delta_y = avg_y - double_fist_start[1]
                    thresh = 0.1 # Sensitivitas geser kepalan

                    if delta_x > thresh:
                        snap_rubik('y', 90)
                        double_fist_active = False # Reset agar tidak spam
                    elif delta_x < -thresh:
                        snap_rubik('y', -90)
                        double_fist_active = False
                    elif delta_y > thresh:
                        snap_rubik('x', -90)
                        double_fist_active = False
                    elif delta_y < -thresh:
                        snap_rubik('x', 90)
                        double_fist_active = False

                cv2.putText(img, "ROTASI RUBIK AKTIF", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # CUBIT & GESER (Individual Hand)
            else:
                double_fist_active = False

                for hand_landmarks, handedness in zip(results.hand_landmarks, results.handedness):
                    label = handedness[0].category_name
                    hand_type = "Kanan" if label == "Left" else "Kiri"

                    # Gambar titik (vertices) dan garis (edges) pada graf tangan
                    HAND_CONNECTIONS = [(0, 1), (1, 2), (2, 3), (3, 4), (5, 6), (6, 7), (7, 8), 
                                        (9, 10), (10, 11), (11, 12), (13, 14), (14, 15), (15, 16), 
                                        (17, 18), (18, 19), (19, 20), (0, 5), (5, 9), (9, 13), (13, 17), (0, 17)]
                    
                    h_img, w_img, _ = img.shape
                    
                    # 1. Menggambar Edge (Garis Koneksi antar titik)
                    for connection in HAND_CONNECTIONS:
                        lm_start = hand_landmarks[connection[0]]
                        lm_end = hand_landmarks[connection[1]]
                        x1, y1 = int(lm_start.x * w_img), int(lm_start.y * h_img)
                        x2, y2 = int(lm_end.x * w_img), int(lm_end.y * h_img)
                        cv2.line(img, (x1, y1), (x2, y2), (255, 255, 255), 2)

                    # 2. Menggambar Vertex (Titik Sendi Jari)
                    for lm in hand_landmarks:
                        cx, cy = int(lm.x * w_img), int(lm.y * h_img)
                        cv2.circle(img, (cx, cy), 4, (0, 0, 255), cv2.FILLED)

                    index_tip = hand_landmarks[8]
                    thumb_tip = hand_landmarks[4]
                    is_pinch = math.hypot(thumb_tip.x - index_tip.x, thumb_tip.y - index_tip.y) < 0.05

                    # LOGIKA TANGAN KANAN (Visual Kanan & Atas)
                    if hand_type == "Kanan" and not is_fist_r:
                        if is_pinch:
                            if not pinch_active_r:
                                pinch_active_r = True
                                pinch_start_r = (index_tip.x, index_tip.y)
                            elif not is_rotating and not is_cam_rotating:
                                dx = index_tip.x - pinch_start_r[0]
                                dy = index_tip.y - pinch_start_r[1]
                                thresh = 0.08

                                if dy < -thresh:
                                    handle_swipe('R', 'UP')
                                    pinch_active_r = False
                                elif dy > thresh:
                                    handle_swipe('R', 'DOWN')
                                    pinch_active_r = False
                                elif dx > thresh:
                                    handle_swipe('U', 'RIGHT')
                                    pinch_active_r = False
                                elif dx < -thresh:
                                    handle_swipe('U', 'LEFT')
                                    pinch_active_r = False
                        else:
                            pinch_active_r = False

                    # LOGIKA TANGAN KIRI (Visual Kiri & Bawah)
                    elif hand_type == "Kiri" and not is_fist_l:
                        if is_pinch:
                            if not pinch_active_l:
                                pinch_active_l = True
                                pinch_start_l = (index_tip.x, index_tip.y)
                            elif not is_rotating and not is_cam_rotating:
                                dx = index_tip.x - pinch_start_l[0]
                                dy = index_tip.y - pinch_start_l[1]
                                thresh = 0.08

                                if dy < -thresh:
                                    handle_swipe('L', 'UP')
                                    pinch_active_l = False
                                elif dy > thresh:
                                    handle_swipe('L', 'DOWN')
                                    pinch_active_l = False
                                elif dx > thresh:
                                    handle_swipe('D', 'RIGHT')
                                    pinch_active_l = False
                                elif dx < -thresh:
                                    handle_swipe('D', 'LEFT')
                                    pinch_active_l = False
                        else:
                            pinch_active_l = False

        cv2.imshow("Sensor Kontrol Rubik", img)
        cv2.waitKey(1)

app.run()
cap.release()
cv2.destroyAllWindows()