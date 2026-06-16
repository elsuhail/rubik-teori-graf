import cv2
import math
import urllib.request
import os
import threading
import time

from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

# --- MEDIA PIPE SETUP ---
model_path = 'hand_landmarker.task'
if not os.path.exists(model_path):
    print("Mengunduh model MediaPipe Hand Landmarker...")
    urllib.request.urlretrieve(
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task", 
        model_path
    )

base_options = mp_python.BaseOptions(model_asset_path=model_path)
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    num_hands=2,
    min_hand_detection_confidence=0.7,
    min_hand_presence_confidence=0.7,
    min_tracking_confidence=0.7
)
detector = vision.HandLandmarker.create_from_options(options)

# --- GLOBAL STATE ---
camera_running = False
latest_frame = None

# Gestur State
pinch_active_r = False
pinch_start_r = (0, 0)
pinch_active_l = False
pinch_start_l = (0, 0)
pinch_pinky_active_r = False
pinch_pinky_start_r = (0, 0)
pinch_pinky_active_l = False
pinch_pinky_start_l = (0, 0)
double_fist_active = False
double_fist_start = (0, 0)
orbit_active = False
orbit_start = (0, 0)

# --- PUBLIC API ---

def start_camera(on_gesture_callback):
    """Memulai thread kamera dan mengirim event gestur ke callback yang diberikan"""
    global camera_running
    if not camera_running:
        camera_running = True
        threading.Thread(target=_process_camera_thread, args=(on_gesture_callback,), daemon=True).start()

def stop_camera():
    """Menghentikan thread kamera"""
    global camera_running
    camera_running = False

def get_latest_frame():
    """Mengambil frame MJPEG terakhir"""
    return latest_frame

def is_camera_running():
    """Mengecek status kamera"""
    return camera_running

# --- CORE VISION LOOP ---

def _process_camera_thread(on_gesture):
    global pinch_active_r, pinch_start_r, pinch_active_l, pinch_start_l
    global pinch_pinky_active_r, pinch_pinky_start_r, pinch_pinky_active_l, pinch_pinky_start_l
    global double_fist_active, double_fist_start, camera_running, latest_frame
    global orbit_active, orbit_start

    print("[VISION] Thread kamera berhasil dimulai! Mengakses hardware kamera...", flush=True)
    # Gunakan auto backend bawaan (tanpa DSHOW) karena DSHOW menghasilkan layar hitam pada webcam ini.
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("[VISION] ERROR KHUSUS: Kamera sama sekali tidak bisa dibuka. Pastikan kamera tidak sedang dipakai aplikasi lain (OBS, Zoom, dll)!", flush=True)
        
    # Optimasi Resolusi
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    HAND_CONNECTIONS = [(0, 1), (1, 2), (2, 3), (3, 4), (5, 6), (6, 7), (7, 8), 
                        (9, 10), (10, 11), (11, 12), (13, 14), (14, 15), (15, 16), 
                        (17, 18), (18, 19), (19, 20), (0, 5), (5, 9), (9, 13), (13, 17), (0, 17)]

    import mediapipe as mp
    frame_count = 0
    last_results = None

    while camera_running:
        success, img = cap.read()
        if not success:
            print("[VISION] PERINGATAN: Kamera terbuka tapi gagal membaca frame! (Kamera mungkin terkunci oleh aplikasi lain)", flush=True)
            time.sleep(1)
            continue

        # Paksa resize tingkat software
        img = cv2.resize(img, (640, 480))
        img = cv2.flip(img, 1)
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        frame_count += 1
        
        # Frame Skipping (Proses AI setiap 3 frame)
        if frame_count % 3 == 0 or last_results is None:
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=imgRGB)
            results = detector.detect(mp_image)
            last_results = results
        else:
            results = last_results

        is_fist_r = False
        is_fist_l = False
        wrist_pos_r = (0, 0)
        wrist_pos_l = (0, 0)

        # 1. Deteksi Kepalan Tangan
        if results.hand_landmarks and results.handedness:
            for hand_landmarks, handedness in zip(results.hand_landmarks, results.handedness):
                label = handedness[0].category_name
                hand_type = "Kanan" if label == "Left" else "Kiri"

                wrist = hand_landmarks[0]
                middle_tip = hand_landmarks[12]
                fist_dist = math.hypot(wrist.x - middle_tip.x, wrist.y - middle_tip.y)

                if fist_dist < 0.15:
                    if hand_type == "Kanan":
                        is_fist_r = True
                        wrist_pos_r = (wrist.x, wrist.y)
                    else:
                        is_fist_l = True
                        wrist_pos_l = (wrist.x, wrist.y)

        # 2. Proses Event Gestur
        if results.hand_landmarks:
            if is_fist_r and is_fist_l:
                avg_x = (wrist_pos_r[0] + wrist_pos_l[0]) / 2
                avg_y = (wrist_pos_r[1] + wrist_pos_l[1]) / 2

                if not double_fist_active:
                    double_fist_active = True
                    double_fist_start = (avg_x, avg_y)
                else:
                    delta_x = avg_x - double_fist_start[0]
                    delta_y = avg_y - double_fist_start[1]
                    thresh = 0.1

                    if delta_x > thresh:
                        on_gesture({"action": "snap_camera", "axis": "y", "angle": 90})
                        double_fist_active = False
                    elif delta_x < -thresh:
                        on_gesture({"action": "snap_camera", "axis": "y", "angle": -90})
                        double_fist_active = False
                    elif delta_y > thresh:
                        on_gesture({"action": "snap_camera", "axis": "x", "angle": -90})
                        double_fist_active = False
                    elif delta_y < -thresh:
                        on_gesture({"action": "snap_camera", "axis": "x", "angle": 90})
                        double_fist_active = False

                cv2.putText(img, "ROTASI RUBIK AKTIF", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                double_fist_active = False

                # Deteksi Gestur Geser Kamera (Single Fist Kanan)
                if is_fist_r and not is_fist_l:
                    if not orbit_active:
                        orbit_active = True
                        orbit_start = wrist_pos_r
                    else:
                        dx = wrist_pos_r[0] - orbit_start[0]
                        dy = wrist_pos_r[1] - orbit_start[1]
                        on_gesture({"action": "orbit", "dx": dx, "dy": dy})
                        orbit_start = wrist_pos_r
                        cv2.putText(img, "MENGGESER KAMERA", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                else:
                    orbit_active = False

                # Gambar Kerangka Tangan
                for hand_landmarks, handedness in zip(results.hand_landmarks, results.handedness):
                    label = handedness[0].category_name
                    hand_type = "Kanan" if label == "Left" else "Kiri"

                    h_img, w_img, _ = img.shape
                    
                    for connection in HAND_CONNECTIONS:
                        lm_start = hand_landmarks[connection[0]]
                        lm_end = hand_landmarks[connection[1]]
                        x1, y1 = int(lm_start.x * w_img), int(lm_start.y * h_img)
                        x2, y2 = int(lm_end.x * w_img), int(lm_end.y * h_img)
                        cv2.line(img, (x1, y1), (x2, y2), (255, 255, 255), 2)

                    for lm in hand_landmarks:
                        cx, cy = int(lm.x * w_img), int(lm.y * h_img)
                        cv2.circle(img, (cx, cy), 4, (0, 0, 255), cv2.FILLED)

                    index_tip = hand_landmarks[8]
                    thumb_tip = hand_landmarks[4]
                    pinky_tip = hand_landmarks[20]
                    wrist = hand_landmarks[0]
                    
                    # Konversi ke piksel
                    cx_0, cy_0 = int(wrist.x * w_img), int(wrist.y * h_img)
                    cx_4, cy_4 = int(thumb_tip.x * w_img), int(thumb_tip.y * h_img)
                    cx_8, cy_8 = int(index_tip.x * w_img), int(index_tip.y * h_img)
                    cx_20, cy_20 = int(pinky_tip.x * w_img), int(pinky_tip.y * h_img)
                    
                    # --- PEMODELAN GRAF PADA COMPUTER VISION ---
                    
                    # 1. Labeling Simpul (Vertex Labeling)
                    # Memberi label pada Simpul-Simpul spesifik di graf kerangka tangan
                    cv2.putText(img, "V0 [Root]", (cx_0 - 20, cy_0 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                    cv2.putText(img, "V4", (cx_4 - 10, cy_4 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                    cv2.putText(img, "V8", (cx_8 - 10, cy_8 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                    cv2.putText(img, "V20", (cx_20 - 10, cy_20 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                    
                    # 2. Kalkulasi Metrik Jarak (Euclidean Distance 3D)
                    # Menghitung jarak geometris antar dua buah Simpul untuk mendeteksi event gestur.
                    # Kita perhitungkan kedalaman (Sumbu Z) agar akurat di ruang 3D.
                    pinch_dist_index = math.sqrt((thumb_tip.x - index_tip.x)**2 + (thumb_tip.y - index_tip.y)**2 + (thumb_tip.z - index_tip.z)**2)
                    pinch_dist_pinky = math.sqrt((thumb_tip.x - pinky_tip.x)**2 + (thumb_tip.y - pinky_tip.y)**2 + (thumb_tip.z - pinky_tip.z)**2)
                    
                    # 3. Logika Ambang Batas (Thresholding & Winner-Takes-All)
                    # Jika jarak euclidean antar simpul (d) < 0.05, maka Sisi tak kasat mata (Dynamic Edge) terbentuk.
                    is_pinch_index = pinch_dist_index < 0.05 and pinch_dist_index < pinch_dist_pinky
                    is_pinch_pinky = pinch_dist_pinky < 0.05 and pinch_dist_pinky < pinch_dist_index

                    # 2. Dynamic Edge Pinch Index (V4 - V8)
                    mid_pinch_x, mid_pinch_y = (cx_4 + cx_8) // 2, (cy_4 + cy_8) // 2
                    
                    if is_pinch_index:
                        cv2.line(img, (cx_4, cy_4), (cx_8, cy_8), (0, 255, 0), 4) # Hijau tebal
                    else:
                        cv2.line(img, (cx_4, cy_4), (cx_8, cy_8), (0, 255, 255), 1) # Kuning pudar
                    
                    cv2.putText(img, f"Pinch: {pinch_dist_index:.3f}", (mid_pinch_x + 10, mid_pinch_y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
                    
                    # 2.5 Dynamic Edge Pinky Pinch (V4 - V20)
                    mid_pinch_pinky_x, mid_pinch_pinky_y = (cx_4 + cx_20) // 2, (cy_4 + cy_20) // 2
                    
                    if is_pinch_pinky:
                        cv2.line(img, (cx_4, cy_4), (cx_20, cy_20), (255, 0, 255), 4) # Magenta tebal
                    else:
                        cv2.line(img, (cx_4, cy_4), (cx_20, cy_20), (255, 0, 255), 1) # Magenta pudar
                    
                    cv2.putText(img, f"Z-Pinch: {pinch_dist_pinky:.3f}", (mid_pinch_pinky_x + 10, mid_pinch_pinky_y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 255), 1)
                    
                    # 3. Dynamic Radius Fist (V0 - V20)
                    fist_dist_val = math.hypot(wrist.x - pinky_tip.x, wrist.y - pinky_tip.y)
                    is_fist_visual = fist_dist_val < 0.15
                    mid_fist_x, mid_fist_y = (cx_0 + cx_20) // 2, (cy_0 + cy_20) // 2
                    
                    if is_fist_visual:
                        cv2.line(img, (cx_0, cy_0), (cx_20, cy_20), (0, 0, 255), 4) # Merah tebal
                    else:
                        cv2.line(img, (cx_0, cy_0), (cx_20, cy_20), (255, 100, 0), 1) # Biru/Orange pudar
                        
                    cv2.putText(img, f"Radius: {fist_dist_val:.3f}", (mid_fist_x - 80, mid_fist_y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 100, 255), 1)

                    if hand_type == "Kanan" and not is_fist_r:
                        if is_pinch_index and not is_pinch_pinky:
                            if not pinch_active_r:
                                pinch_active_r = True
                                pinch_start_r = (index_tip.x, index_tip.y)
                            else:
                                dx = index_tip.x - pinch_start_r[0]
                                dy = index_tip.y - pinch_start_r[1]
                                thresh = 0.08

                                if dy < -thresh:
                                    on_gesture({"action": "swipe", "visual_face": "R", "swipe_dir": "UP"})
                                    pinch_active_r = False
                                elif dy > thresh:
                                    on_gesture({"action": "swipe", "visual_face": "R", "swipe_dir": "DOWN"})
                                    pinch_active_r = False
                                elif dx > thresh:
                                    on_gesture({"action": "swipe", "visual_face": "U", "swipe_dir": "RIGHT"})
                                    pinch_active_r = False
                                elif dx < -thresh:
                                    on_gesture({"action": "swipe", "visual_face": "U", "swipe_dir": "LEFT"})
                                    pinch_active_r = False
                        elif is_pinch_pinky and not is_pinch_index:
                            if not pinch_pinky_active_r:
                                pinch_pinky_active_r = True
                                pinch_pinky_start_r = (pinky_tip.x, pinky_tip.y)
                            else:
                                dy = pinky_tip.y - pinch_pinky_start_r[1]
                                thresh = 0.08

                                if dy < -thresh:
                                    on_gesture({"action": "swipe", "visual_face": "F", "swipe_dir": "UP"})
                                    pinch_pinky_active_r = False
                                elif dy > thresh:
                                    on_gesture({"action": "swipe", "visual_face": "F", "swipe_dir": "DOWN"})
                                    pinch_pinky_active_r = False
                        else:
                            pinch_active_r = False
                            pinch_pinky_active_r = False

                    elif hand_type == "Kiri" and not is_fist_l:
                        if is_pinch_index and not is_pinch_pinky:
                            if not pinch_active_l:
                                pinch_active_l = True
                                pinch_start_l = (index_tip.x, index_tip.y)
                            else:
                                dx = index_tip.x - pinch_start_l[0]
                                dy = index_tip.y - pinch_start_l[1]
                                thresh = 0.08

                                if dy < -thresh:
                                    on_gesture({"action": "swipe", "visual_face": "L", "swipe_dir": "UP"})
                                    pinch_active_l = False
                                elif dy > thresh:
                                    on_gesture({"action": "swipe", "visual_face": "L", "swipe_dir": "DOWN"})
                                    pinch_active_l = False
                                elif dx > thresh:
                                    on_gesture({"action": "swipe", "visual_face": "D", "swipe_dir": "RIGHT"})
                                    pinch_active_l = False
                                elif dx < -thresh:
                                    on_gesture({"action": "swipe", "visual_face": "D", "swipe_dir": "LEFT"})
                                    pinch_active_l = False
                        elif is_pinch_pinky and not is_pinch_index:
                            if not pinch_pinky_active_l:
                                pinch_pinky_active_l = True
                                pinch_pinky_start_l = (pinky_tip.x, pinky_tip.y)
                            else:
                                dy = pinky_tip.y - pinch_pinky_start_l[1]
                                thresh = 0.08

                                if dy < -thresh:
                                    on_gesture({"action": "swipe", "visual_face": "B", "swipe_dir": "UP"})
                                    pinch_pinky_active_l = False
                                elif dy > thresh:
                                    on_gesture({"action": "swipe", "visual_face": "B", "swipe_dir": "DOWN"})
                                    pinch_pinky_active_l = False
                        else:
                            pinch_active_l = False
                            pinch_pinky_active_l = False

        # 3. Encode Frame untuk Web
        ret, buffer = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        if ret:
            latest_frame = buffer.tobytes()
        
    # Bersihkan resource saat loop selesai
    latest_frame = None
    cap.release()
