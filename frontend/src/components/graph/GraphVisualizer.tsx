import { useRef, useEffect } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { useRubikStore } from '../../store/useRubikStore';

export function GraphVisualizer() {
  const { graphNodes, graphLinks } = useRubikStore();
  const fgRef = useRef<any>(null);

  // Memaksa kamera graph agar selalu fokus ke node terbaru
  useEffect(() => {
    if (fgRef.current && graphNodes.length > 0) {
      // Tunggu sedikit agar animasi fisika bisa mulai
      setTimeout(() => {
        if (fgRef.current) {
          fgRef.current.zoomToFit(400, 50);
        }
      }, 300);
    }
  }, [graphNodes.length]);

  return (
    <div className="absolute top-48 left-6 w-80 h-80 rounded-2xl border border-white/20 bg-black/40 backdrop-blur-md overflow-hidden pointer-events-none">
      <div className="absolute top-2 left-4 text-xs text-white/70 font-semibold tracking-wider z-10">
        CAYLEY GRAPH (REAL-TIME)
      </div>
      <ForceGraph2D
        ref={fgRef}
        width={320}
        height={320}
        graphData={{ nodes: graphNodes, links: graphLinks }}
        nodeAutoColorBy="group"
        nodeColor={(node: any) => node.color || '#00ffff'}
        nodeVal={(node: any) => node.val}
        linkColor={() => 'rgba(255, 255, 255, 0.4)'}
        linkWidth={2}
        enableNodeDrag={false}
        enableZoomInteraction={true}
        enablePanInteraction={true}
        dagMode="radialout"
        dagLevelDistance={20}
        d3VelocityDecay={0.3}
      />
      <div className="absolute bottom-2 left-4 text-[10px] text-white/70 space-y-1.5 z-10 bg-black/50 p-2.5 rounded-xl backdrop-blur-md border border-white/10">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-[#00ffff] shadow-[0_0_5px_#00ffff]"></div> 
          <span>Eksplorasi Manual (Tersesat)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-[#00ff00] shadow-[0_0_5px_#00ff00]"></div> 
          <span>Shortest Path (Kociemba)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-[#ffd700] shadow-[0_0_5px_#ffd700]"></div> 
          <span>Goal State (Selesai)</span>
        </div>
      </div>
    </div>
  );
}
