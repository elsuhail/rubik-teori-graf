import { create } from 'zustand';
// @ts-expect-error
import '../lib/cubejs/cube.js';
import '../lib/cubejs/solve.js';
const Cube = (typeof window !== "undefined" && (window as any).Cube);

const globalCube = new Cube();

export type RotationCommand = {
  axis: 'x' | 'y' | 'z';
  slice: number | 'all';
  direction: number; // 1 or -1
};

interface RubikState {
  isSystemBusy: boolean;
  historyStackCount: number;
  rotationQueue: RotationCommand[];
  isSolved: boolean;
  resetCounter: number;
  enqueueRotation: (command: RotationCommand, isSolveMove?: boolean) => void;
  dequeueRotation: () => void;
  setSystemBusy: (busy: boolean) => void;
  solveVirtualCube: () => void;
  resetGraph: () => void;
}

function toSingmaster(axis: string, slice: number, direction: number): string {
  if (axis === 'x' && slice === 1) return direction === -1 ? "R" : "R'";
  if (axis === 'x' && slice === -1) return direction === 1 ? "L" : "L'";
  if (axis === 'y' && slice === 1) return direction === -1 ? "U" : "U'";
  if (axis === 'y' && slice === -1) return direction === 1 ? "D" : "D'";
  if (axis === 'z' && slice === 1) return direction === -1 ? "F" : "F'";
  if (axis === 'z' && slice === -1) return direction === 1 ? "B" : "B'";
  return "";
}

function fromSingmaster(move: string): RotationCommand[] {
  const baseMove = move[0];
  const isDouble = move.length > 1 && move[1] === '2';
  const isPrime = move.length > 1 && move[1] === "'";
  
  const map: Record<string, any> = {
    "R": { axis: 'x', slice: 1, direction: -1 },
    "L": { axis: 'x', slice: -1, direction: 1 },
    "U": { axis: 'y', slice: 1, direction: -1 },
    "D": { axis: 'y', slice: -1, direction: 1 },
    "F": { axis: 'z', slice: 1, direction: -1 },
    "B": { axis: 'z', slice: -1, direction: 1 },
  };
  
  const baseCmd = map[baseMove];
  if (!baseCmd) return [];
  
  const cmd = { ...baseCmd, direction: isPrime ? baseCmd.direction * -1 : baseCmd.direction };
  
  if (isDouble) return [cmd, cmd];
  return [cmd];
}

export const useRubikStore = create<RubikState>((set, get) => ({
  isSystemBusy: false,
  historyStackCount: 0,
  rotationQueue: [],
  isSolved: true,
  resetCounter: 0,
  
  // FASE EKSPLORASI GRAF (Manual Moves)
  enqueueRotation: (command, isSolveMove = false) => set((state) => {
    let historyCount = state.historyStackCount;
    
    if (command.slice !== 'all') {
      const notation = toSingmaster(command.axis, command.slice as number, command.direction);
      if (notation) {
        // Mengeksekusi transisi pada State Space Graph (Bergerak 1 Edge menjauhi kondisi Solved)
        globalCube.move(notation);
        
        if (!isSolveMove) {
          historyCount += 1;
        }
      }
    }
    
    return {
      rotationQueue: [...state.rotationQueue, command],
      historyStackCount: historyCount,
      isSolved: globalCube.isSolved()
    };
  }),
  
  dequeueRotation: () => set((state) => {
    const nextQueue = state.rotationQueue.slice(1);
    const isFinished = nextQueue.length === 0;
    return {
      rotationQueue: nextQueue,
      isSystemBusy: isFinished ? false : state.isSystemBusy
    };
  }),

  setSystemBusy: (busy) => set({ isSystemBusy: busy }),
  
  // FASE PENCARIAN JALUR TERPENDEK (Auto-Solve / Shortest Path)
  solveVirtualCube: () => {
    set({ isSystemBusy: true });
    
    // Inisialisasi solver Kociemba.
    // Algoritma ini berjalan dalam 2 fase pencarian mendalam pada graf (Two-Phase Algorithm).
    // Dilakukan secara lazy agar tidak membekukan UI saat web pertama kali di-load.
    Cube.initSolver();
    
    // Algoritma Kociemba akan menelusuri 43 Quintillion status kombinasi
    // dan mereturn "Shortest Path" kembali ke Simpul Solved (misal: "U2 F' R ...")
    const solutionStr = globalCube.solve();
    
    if (!solutionStr) {
       set({ isSystemBusy: false });
       return; // Graf sudah berada di titik awal (Already Solved)
    }
    
    // Terjemahkan rentetan Edge (Shortest Path) menjadi Visual Matriks Rotasi 3D
    const moves = solutionStr.split(' ');
    moves.forEach((m: string) => {
       const cmds = fromSingmaster(m);
       cmds.forEach(cmd => get().enqueueRotation(cmd, true));
    });
  },

  resetGraph: () => {
    globalCube.identity(); // Reset posisi graf kembali ke titik asal (Identity Node)
    set((state) => ({
      historyStackCount: 0,
      rotationQueue: [],
      isSystemBusy: false,
      isSolved: true,
      resetCounter: state.resetCounter + 1
    }));
  }
}));
