import asyncio
import json
import numpy as np
import cv2 # Hanya untuk frame dummy sementara (tidak wajib)
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

import vision

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
server_loop = None

@app.on_event("startup")
async def startup_event():
    global server_loop
    server_loop = asyncio.get_running_loop()

# Queue untuk mengirim pesan ke Web Client
ws_queues = []

def broadcast_event(event_data: dict):
    """
    Kirim event (JSON) ke seluruh client WebSocket yang terhubung.
    Dipanggil dari thread mana saja secara aman.
    """
    global server_loop
    for q in ws_queues:
        if server_loop and server_loop.is_running():
            server_loop.call_soon_threadsafe(q.put_nowait, event_data)

def handle_gesture(event_data: dict):
    """
    Callback yang dipanggil oleh vision.py setiap kali gestur terdeteksi.
    """
    broadcast_event(event_data)

# --- MJPEG STREAMING ENDPOINT ---
async def frame_generator():
    import asyncio
    
    # Buat frame kosong sebagai placeholder
    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(blank, "Menyalakan Kamera...", (100, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    _, buffer = cv2.imencode('.jpg', blank)
    dummy_frame = buffer.tobytes()

    while True:
        frame_to_yield = dummy_frame
        if vision.is_camera_running():
            latest = vision.get_latest_frame()
            if latest is not None:
                frame_to_yield = latest

        try:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_to_yield + b'\r\n')
        except asyncio.CancelledError:
            break
        except Exception:
            break
            
        await asyncio.sleep(0.01)

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")

# --- WEBSOCKET ENDPOINT ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    q = asyncio.Queue()
    ws_queues.append(q)
    
    async def receive_from_client():
        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                print(f"[SERVER] Menerima pesan WebSocket: {message.get('action')}", flush=True)
                
                # Menyalakan/Mematikan Kamera
                if message.get("action") == "toggle_camera":
                    status = message.get("status")
                    if status == "start" and not vision.is_camera_running():
                        vision.start_camera(on_gesture_callback=handle_gesture)
                    elif status == "stop" and vision.is_camera_running():
                        vision.stop_camera()
        except WebSocketDisconnect:
            pass

    async def send_to_client():
        try:
            while True:
                event = await q.get()
                await websocket.send_text(json.dumps(event))
        except WebSocketDisconnect:
            pass

    recv_task = asyncio.create_task(receive_from_client())
    send_task = asyncio.create_task(send_to_client())

    done, pending = await asyncio.wait(
        [recv_task, send_task],
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()
    if q in ws_queues:
        ws_queues.remove(q)

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
