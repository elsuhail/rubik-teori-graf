import { useState } from 'react';
import { Hand, Move, X, Orbit, Box, Info } from 'lucide-react';

export function TutorialOverlay() {
  const [isOpen, setIsOpen] = useState(true);

  if (!isOpen) {
    return (
      <button 
        onClick={() => setIsOpen(true)}
        className="absolute top-6 right-6 bg-white/70 backdrop-blur-md border border-slate-200 p-3 rounded-full shadow-lg text-slate-700 hover:bg-white hover:text-primary transition-all pointer-events-auto flex items-center justify-center group"
      >
        <Info className="w-6 h-6" />
        <span className="max-w-0 overflow-hidden whitespace-nowrap group-hover:max-w-xs group-hover:ml-2 transition-all duration-300 ease-in-out font-medium text-sm">
          Tampilkan Tutorial
        </span>
      </button>
    );
  }

  return (
    <div className="absolute top-6 right-6 bg-white/80 backdrop-blur-xl shadow-2xl border border-white/50 rounded-3xl w-80 overflow-hidden pointer-events-auto transition-all animate-in slide-in-from-top-8 duration-500">
      {/* Header */}
      <div className="bg-gradient-to-r from-primary/10 to-indigo-500/10 px-5 py-4 border-b border-white/50 flex justify-between items-center">
        <h3 className="font-semibold text-slate-800 flex items-center gap-2">
          <Hand className="w-5 h-5 text-primary" />
          Tutorial Bermain
        </h3>
        <button 
          onClick={() => setIsOpen(false)}
          className="text-slate-400 hover:text-slate-700 transition-colors bg-white/50 hover:bg-white p-1 rounded-full"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div className="p-5 space-y-4">
        {/* Item 1 */}
        <div className="flex gap-4 items-start group">
          <div className="bg-blue-100 text-blue-600 p-2.5 rounded-2xl shadow-inner group-hover:scale-110 transition-transform mt-1">
            <Move className="w-5 h-5" />
          </div>
          <div className="flex-1">
            <h4 className="font-semibold text-slate-800 text-sm">Putar Sisi Luar (X / Y)</h4>
            <p className="text-xs text-slate-500 mt-1 mb-1.5 leading-relaxed font-medium">
              Cubit <span className="font-bold text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded">Jempol + Telunjuk</span>
            </p>
            <ul className="text-[11px] text-slate-500 space-y-1 list-disc pl-3">
              <li><strong className="text-slate-600">Tangan Kanan:</strong> Putar sisi Kanan (R) & Atas (U).</li>
              <li><strong className="text-slate-600">Tangan Kiri:</strong> Putar sisi Kiri (L) & Bawah (D).</li>
            </ul>
          </div>
        </div>

        <div className="h-px bg-gradient-to-r from-transparent via-slate-200 to-transparent" />

        {/* Item 2 */}
        <div className="flex gap-4 items-start group">
          <div className="bg-fuchsia-100 text-fuchsia-600 p-2.5 rounded-2xl shadow-inner group-hover:scale-110 transition-transform mt-1">
            <Box className="w-5 h-5" />
          </div>
          <div className="flex-1">
            <h4 className="font-semibold text-slate-800 text-sm">Putar Kedalaman (Z)</h4>
            <p className="text-xs text-slate-500 mt-1 mb-1.5 leading-relaxed font-medium">
              Cubit <span className="font-bold text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded">Jempol + Kelingking</span>
            </p>
            <ul className="text-[11px] text-slate-500 space-y-1 list-disc pl-3">
              <li><strong className="text-slate-600">Tangan Kanan:</strong> Putar sisi Depan (F).</li>
              <li><strong className="text-slate-600">Tangan Kiri:</strong> Putar sisi Belakang (B).</li>
            </ul>
          </div>
        </div>

        <div className="h-px bg-gradient-to-r from-transparent via-slate-200 to-transparent" />

        {/* Item 3 */}
        <div className="flex gap-4 items-start group">
          <div className="bg-emerald-100 text-emerald-600 p-2.5 rounded-2xl shadow-inner group-hover:scale-110 transition-transform">
            <Orbit className="w-5 h-5" />
          </div>
          <div>
            <h4 className="font-semibold text-slate-800 text-sm">Orbit Kamera 3D</h4>
            <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">
              Buat <span className="font-medium text-slate-700">Kepalan Tangan</span> (Fist) dan geser untuk melihat sisi belakang Rubik.
            </p>
          </div>
        </div>
      </div>

      {/* Footer Note */}
      <div className="bg-slate-50/50 px-5 py-3 text-[10px] text-slate-400 text-center flex items-center justify-center gap-1">
        <Info className="w-3 h-3" /> Gestur kamera (Kanan/Kiri) kini cerdas menyesuaikan sudut pandang.
      </div>
    </div>
  );
}
