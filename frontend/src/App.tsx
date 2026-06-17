import React, { useEffect, useState, useRef } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Environment } from '@react-three/drei';
import { RubikCube } from './components/3d/RubikCube';
import { useRubikStore } from './store/useRubikStore';
import { BrainCircuit, Loader2, RotateCcw, Camera, CameraOff } from 'lucide-react';
import { TutorialOverlay } from './components/ui/TutorialOverlay';

class ErrorBoundary extends React.Component<{children: any}, {hasError: boolean, error: any}> {
  constructor(props: any) { super(props); this.state = { hasError: false, error: null }; }
  static getDerivedStateFromError(error: any) { return { hasError: true, error }; }
  render() {
    if (this.state.hasError) {
      return <div className="absolute inset-0 bg-black text-red-500 p-10 z-50 overflow-auto font-mono text-sm">{String(this.state.error)}</div>;
    }
    return this.props.children;
  }
}

const WS_URL = 'ws://localhost:8000/ws';

// Komponen untuk menangani rotasi kamera (orbit) secara custom
const HandOrbitControls = ({ velocityRef, azimuthRef }: { velocityRef: any, azimuthRef: any }) => {
  const { camera } = useThree();
  
  useFrame(() => {
    // Terapkan friksi/redaman (damping)
    velocityRef.current.az *= 0.92;
    velocityRef.current.pol *= 0.92;

    // Update sudut kamera
    azimuthRef.current += velocityRef.current.az;
    let newPol = Math.atan2(camera.position.y, Math.sqrt(camera.position.x**2 + camera.position.z**2)) + velocityRef.current.pol;
    newPol = Math.max(-Math.PI/2 + 0.1, Math.min(Math.PI/2 - 0.1, newPol)); // Batasi polar angle

    const radius = 8;
    camera.position.x = radius * Math.cos(newPol) * Math.sin(azimuthRef.current);
    camera.position.z = radius * Math.cos(newPol) * Math.cos(azimuthRef.current);
    camera.position.y = radius * Math.sin(newPol);
    
    camera.lookAt(0, 0, 0);
  });

  return null;
};

function App() {
  const { 
    isSystemBusy,
    historyStackCount, 
    enqueueRotation,
    solveVirtualCube,
    resetGraph,
    isSolved,
    resetCounter
  } = useRubikStore();
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [lastJsonMessage, setLastJsonMessage] = useState<any>(null);
  
  // Referensi untuk fisika kamera (momentum)
  const orbitVelocityRef = useRef({ az: 0, pol: 0 });
  const cameraAzimuthRef = useRef(0);
  
  // Custom WebSocket hook implementation
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [streamKey, setStreamKey] = useState(Date.now());

  useEffect(() => {
    let ws: WebSocket;
    
    const connect = () => {
      try {
        ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
          resetGraph();
          if (isCameraActive) {
            ws.send(JSON.stringify({ action: "toggle_camera", status: "start" }));
          }
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            setLastJsonMessage(data);
          } catch (e) {
            console.error('Error parsing WebSocket message:', e);
          }
        };

        ws.onclose = () => {
          reconnectTimeoutRef.current = setTimeout(connect, 2000);
        };
      } catch (err) {
        console.error('WebSocket connection error:', err);
      }
    };

    connect();

    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
    };
  }, [isCameraActive, resetGraph]);

  const toggleCamera = () => {
    const newState = !isCameraActive;
    setIsCameraActive(newState);
    if (!newState) setStreamKey(Date.now());
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ 
        action: "toggle_camera", 
        status: newState ? "start" : "stop" 
      }));
    }
  };

  // Dengarkan pesan gestur dari backend (WebSocket Listener)
  useEffect(() => {
    if (lastJsonMessage) {
      const msg = lastJsonMessage;
      
      // LOGIKA TRANSLASI GRAF SPASIAL: Mengubah Geseran 2D layar menjadi Matriks Rotasi 3D Rubik
      if (msg.action === 'swipe') {
        let az = cameraAzimuthRef.current;
        
        // 1. Normalisasi sudut azimuth kamera ke rentang [0, 2PI)
        az = ((az % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
        
        // 2. Menentukan Kuadran Pandangan Kamera (0, 1, 2, atau 3)
        // Hal ini penting karena "Kanan" di layar bisa berarti Sumbu X, Y, atau Z 
        // tergantung dari sudut mana pengguna melihat Rubik.
        const quad = Math.round(az / (Math.PI / 2)) % 4;

        // 3. Mapping Sumbu Relatif (Relative Axis Mapping)
        const getRelativeMapping = (q: number, vFace: string) => {
          // q = kuadran kamera. vFace = Wajah Rubik yang sedang dilihat (F/B/R/L/U/D)
          // Mengembalikan Sumbu absolut Rubik (x,y,z) dan indeks irisan (slice) yang harus diputar.
          const map: Record<number, Record<string, { axis: 'x'|'y'|'z', slice: number, dirMult: number }>> = {
            0: { 'R': { axis: 'x', slice: 1, dirMult: 1 }, 'L': { axis: 'x', slice: -1, dirMult: 1 }, 'F': { axis: 'z', slice: 1, dirMult: 1 }, 'B': { axis: 'z', slice: -1, dirMult: 1 } },
            1: { 'R': { axis: 'z', slice: -1, dirMult: -1 }, 'L': { axis: 'z', slice: 1, dirMult: -1 }, 'F': { axis: 'x', slice: 1, dirMult: 1 }, 'B': { axis: 'x', slice: -1, dirMult: -1 } },
            2: { 'R': { axis: 'x', slice: -1, dirMult: -1 }, 'L': { axis: 'x', slice: 1, dirMult: -1 }, 'F': { axis: 'z', slice: -1, dirMult: -1 }, 'B': { axis: 'z', slice: 1, dirMult: 1 } },
            3: { 'R': { axis: 'z', slice: 1, dirMult: 1 }, 'L': { axis: 'z', slice: -1, dirMult: 1 }, 'F': { axis: 'x', slice: -1, dirMult: -1 }, 'B': { axis: 'x', slice: 1, dirMult: 1 } }
          };
          // Wajah Atas (Up) dan Bawah (Down) selalu memutar sumbu Y absolut
          if (vFace === 'U') return { axis: 'y', slice: 1, dirMult: 1 };
          if (vFace === 'D') return { axis: 'y', slice: -1, dirMult: 1 };
          return map[q][vFace];
        };

        const mapping = getRelativeMapping(quad, msg.visual_face);
        
        // 4. Kalkulasi Vektor Arah Putaran
        let direction = 1; // Default searah jarum jam (Clockwise)
        if (msg.swipe_dir === 'UP' || msg.swipe_dir === 'LEFT') direction = -1; // Berlawanan arah (Counter-Clockwise)
        
        // Koreksi arah putaran berdasarkan matriks pandangan kamera
        direction *= mapping.dirMult;

        // 5. Eksekusi Putaran ke dalam State Rubik
        enqueueRotation({ axis: mapping.axis as 'x' | 'y' | 'z', slice: mapping.slice, direction });
      
      } else if (msg.action === 'snap_camera') {
        // Logika untuk memutar seluruh tubuh rubik (Rotasi Universal / Sumbu Tengah)
        const direction = msg.angle > 0 ? 1 : -1;
        enqueueRotation({ axis: msg.axis, slice: 'all', direction });
      
      } else if (msg.action === 'orbit') {
        // Logika Orbit Kamera Bebas (Gestur Kepalan Tangan Tunggal)
        // Menambahkan velositas fisika sehingga putaran kamera terasa licin (momentum based)
        orbitVelocityRef.current.az += msg.dx * 0.8;
        orbitVelocityRef.current.pol += msg.dy * 0.8;
      }
    }
  }, [lastJsonMessage, enqueueRotation]);

  const handleAutoSolve = () => {
    if (isSystemBusy || isSolved) return;
    solveVirtualCube();
  };

  return (
    <ErrorBoundary>
    <div className="w-screen h-screen overflow-hidden bg-background relative flex">
      {/* 3D Canvas Context */}
      <div className="absolute inset-0 z-0">
        <Canvas camera={{ position: [5, 5, 5], fov: 45 }}>
          <Environment preset="city" />
          <ambientLight intensity={0.5} />
          <directionalLight position={[10, 10, 5]} intensity={1.5} castShadow />
          <RubikCube key={resetCounter} />
          <HandOrbitControls velocityRef={orbitVelocityRef} azimuthRef={cameraAzimuthRef} />
        </Canvas>
      </div>

      {/* UI Overlay */}
      <div className="z-10 absolute inset-0 pointer-events-none p-6 flex flex-col justify-between">
        
        {/* Header */}
        <div className="flex justify-between items-start">
          <div className="bg-white/70 backdrop-blur-md shadow-sm border border-slate-200 rounded-2xl p-5 w-72 pointer-events-auto">
            <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2">
              <BrainCircuit className="text-primary" />
              Kelompok Nabil
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              
            </p>
            
            <div className="mt-6 space-y-3">
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-600 font-medium">History Stack</span>
                <span className="bg-slate-100 text-slate-800 py-1 px-3 rounded-full font-mono text-xs">
                  {historyStackCount} moves
                </span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-600 font-medium">Status</span>
                {isSystemBusy ? (
                  <span className="flex items-center gap-1.5 text-amber-600 font-medium text-xs">
                    <Loader2 className="w-3 h-3 animate-spin" /> Auto-Solving
                  </span>
                ) : (
                  <span className="flex items-center gap-1.5 text-emerald-600 font-medium text-xs">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" /> Ready
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Footer Controls */}
        <div className="flex justify-center pb-4 pointer-events-auto gap-4">
          <button 
            onClick={toggleCamera}
            className={`
              flex items-center gap-2 px-6 py-3 rounded-full font-medium shadow-lg transition-all duration-300 transform hover:scale-105 active:scale-95
              ${isCameraActive 
                ? 'bg-rose-500 hover:bg-rose-600 text-white shadow-rose-500/30' 
                : 'bg-slate-800 hover:bg-slate-900 text-white shadow-slate-800/30'}
            `}
          >
            {isCameraActive ? <CameraOff className="w-5 h-5" /> : <Camera className="w-5 h-5" />}
            {isCameraActive ? 'Stop Camera' : 'Start Camera'}
          </button>

          <button 
            onClick={handleAutoSolve}
            disabled={isSystemBusy || isSolved}
            className={`
              flex items-center gap-2 px-6 py-3 rounded-full font-medium shadow-lg transition-all duration-300 transform hover:scale-105 active:scale-95
              ${(isSystemBusy || isSolved) 
                ? 'bg-slate-200 text-slate-400 cursor-not-allowed shadow-none' 
                : 'bg-primary text-white hover:bg-blue-600 hover:shadow-primary/30'}
            `}
          >
            <RotateCcw className="w-5 h-5" />
            Auto Solve 
          </button>
          
          <button 
            onClick={() => useRubikStore.getState().resetGraph()}
            disabled={isSystemBusy}
            className={`
              flex items-center gap-2 px-6 py-3 rounded-full font-medium shadow-lg transition-all duration-300 transform hover:scale-105 active:scale-95
              ${isSystemBusy
                ? 'bg-slate-200 text-slate-400 cursor-not-allowed shadow-none' 
                : 'bg-slate-800 text-white hover:bg-red-600 hover:shadow-red-500/30'}
            `}
          >
            <RotateCcw className="w-5 h-5" />
            Reset 
          </button>
        </div>

        {/* Floating Camera Video Feed */}
        {isCameraActive && (
          <div className="absolute bottom-6 right-6 w-[640px] aspect-video bg-slate-900/80 backdrop-blur-md rounded-2xl overflow-hidden shadow-2xl border border-white/10 pointer-events-auto transition-all duration-500 animate-in fade-in slide-in-from-bottom-8">
            <img 
              src={`http://localhost:8000/video_feed?t=${streamKey}`} 
              alt="Live Camera Feed" 
              className="w-full h-full object-cover opacity-90"
            />
            <div className="absolute top-3 left-3 flex items-center gap-2 bg-black/50 backdrop-blur-md px-2.5 py-1 rounded-md border border-white/5">
              <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse shadow-[0_0_8px_rgba(239,68,68,0.8)]" />
              <span className="text-[10px] text-white font-medium uppercase tracking-wider">Live Sensor</span>
            </div>
            
            {/* Corner decorations to look techy */}
            <div className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-primary/50 m-2 rounded-tl-sm"></div>
            <div className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-primary/50 m-2 rounded-tr-sm"></div>
            <div className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-primary/50 m-2 rounded-bl-sm"></div>
            <div className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-primary/50 m-2 rounded-br-sm"></div>
          </div>
        )}

      </div>
      <TutorialOverlay />
    </div>
    </ErrorBoundary>
  );
}

export default App;
