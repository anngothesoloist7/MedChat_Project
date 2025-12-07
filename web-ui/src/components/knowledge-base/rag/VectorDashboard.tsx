import React, { useState, useEffect, useRef } from 'react';
import dynamic from 'next/dynamic';
import { Settings2, Maximize2, Info, MousePointer2 } from 'lucide-react';

// Dynamic import for Plot because plotly.js relies on window/document which aren't available during SSR
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface VectorDashboardProps {
  apiBaseUrl?: string;
}

interface PlotDataPoint {
    x: number;
    y: number;
    text: string;
    markerColor: number;
}

const VectorDashboard: React.FC<VectorDashboardProps> = ({ apiBaseUrl = 'https://rag.botnow.online' }) => {
  // --- State ---
  const [points, setPoints] = useState<any[]>([]);
  const [plotData, setPlotData] = useState<PlotDataPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('Idle');
  const [activePoint, setActivePoint] = useState<any | null>(null);
  
  // --- Config State ---
  const [config, setConfig] = useState({
    limit: 500,
    nNeighbors: 15,
    minDist: 0.1,
    algorithm: 'UMAP',
  });

  // --- Worker Ref ---
  const workerRef = useRef<Worker | null>(null);

  // Initialize Worker once
  useEffect(() => {
    // Create worker instance
    workerRef.current = new Worker('/umapWorker.js');
    
    // Handle Worker Messages
    workerRef.current.onmessage = (e) => {
      const { status: wStatus, result, error } = e.data;
      
      if (wStatus === 'running' || wStatus === 'complete') {
        if (!points || points.length === 0) return;

        // Map reduced coordinates to Plotly format
        const aestheticData = result.map((coord: {x: number, y: number}, i: number) => ({
          x: coord.x,
          y: coord.y,
          // Hover text
          text: `<b>${points[i]?.book || 'Unknown'}</b><br>Keywords: ${(points[i]?.keywords || []).slice(0,3).join(', ')}`,
          // Gradient color based on position (aesthetic)
          markerColor: coord.x + coord.y 
        }));
        
        setPlotData(aestheticData);

        if (wStatus === 'running') {
            setStatus('Optimizing layout...');
        } else {
            setLoading(false);
            setStatus('Ready');
        }
      } else if (wStatus === 'error') {
          setStatus(`Error: ${error}`);
          setLoading(false);
      }
    };

    return () => {
        workerRef.current?.terminate();
    };
  }, [points]); // Re-bind if source points change

  // --- Actions ---
  const fetchDataAndRun = async () => {
    setLoading(true);
    setStatus(`Fetching ${config.limit} vectors...`);
    setActivePoint(null); // Clear selection
    
    try {
      const res = await fetch(`${apiBaseUrl}/vectors?limit=${config.limit}`);
      if (!res.ok) throw new Error("API Fetch Failed");
      const data = await res.json();
      
      const fetchedVectors = data.vectors || [];
      const fetchedPoints = data.points || [];

      setPoints(fetchedPoints); 
      
      if (fetchedVectors.length === 0) {
        setStatus('No points found.');
        setLoading(false);
        return;
      }

      setStatus(`Initializing ${config.algorithm}...`);
      
      // Send to Worker
      workerRef.current?.postMessage({ 
        vectors: fetchedVectors, 
        params: { 
            algorithm: config.algorithm,
            nNeighbors: parseInt(config.nNeighbors.toString()),
            minDist: parseFloat(config.minDist.toString()),
            perplexity: 30, // Default for t-SNE if selected
        } 
      });

    } catch (err: any) {
      console.error(err);
      setStatus('Error: ' + err.message);
      setLoading(false);
    }
  };

  // --- Handlers ---
  const handlePlotClick = (event: any) => {
      if (event && event.points && event.points[0]) {
          const pointIndex = event.points[0].pointIndex;
          if (points[pointIndex]) {
              setActivePoint(points[pointIndex]);
          }
      }
  };

  return (
    <div className="flex h-[650px] w-full bg-background text-foreground font-sans rounded-xl overflow-hidden border border-border/50 shadow-sm">
      
      {/* --- LEFT: Main Chart Area --- */}
      <div className="flex-1 flex flex-col min-w-0 bg-background/50 relative">
        {/* Header */}
        <div className="h-12 border-b border-border/50 flex items-center px-4 justify-between bg-card/10 backdrop-blur-sm z-10">
             <div className="flex items-center gap-2">
                <Maximize2 size={16} className="text-accent"/>
                <span className="font-semibold text-sm">Collection Visualization</span>
             </div>
             <div className="text-[10px] font-mono opacity-50 flex items-center gap-2">
                 <div className={`w-1.5 h-1.5 rounded-full ${loading ? 'bg-yellow-500 animate-pulse' : 'bg-green-500'}`} />
                 {status}
             </div>
        </div>

        {/* Plot */}
        <div className="flex-1 relative">
            {plotData.length > 0 ? (
            <Plot
                data={[
                {
                    x: plotData.map(d => d.x),
                    y: plotData.map(d => d.y),
                    text: plotData.map(d => d.text),
                    mode: 'markers',
                    type: 'scattergl' as any,
                    marker: { 
                        color: plotData.map(d => d.markerColor),
                        colorscale: 'Viridis', 
                        size: 8,
                        opacity: 0.8,
                        line: { width: 1, color: 'rgba(255,255,255,0.1)' }
                    },
                    hoverinfo: 'text'
                }
                ]}
                layout={{
                    autosize: true,
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    font: { color: '#9ca3af', family: 'Inter, sans-serif' },
                    margin: { t: 20, r: 20, b: 20, l: 20 },
                    xaxis: { showgrid: true, gridcolor: 'rgba(128,128,128,0.1)', zerolinecolor: 'rgba(128,128,128,0.2)', showticklabels: false },
                    yaxis: { showgrid: true, gridcolor: 'rgba(128,128,128,0.1)', zerolinecolor: 'rgba(128,128,128,0.2)', showticklabels: false },
                    dragmode: 'pan',
                    hovermode: 'closest'
                }}
                config={{
                    scrollZoom: true,
                    displayModeBar: true,
                    displaylogo: false,
                    modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d'],
                }}
                useResizeHandler={true}
                style={{ width: '100%', height: '100%' }}
                onClick={handlePlotClick}
            />
            ) : (
                <div className="absolute inset-0 flex flex-col items-center justify-center text-muted-foreground gap-3">
                    <div className={`p-4 rounded-full bg-secondary/30 border border-border/50 mb-2 ${loading ? 'animate-pulse' : ''}`}>
                         <span className="text-3xl filter grayscale opacity-80">✨</span>
                    </div>
                    <p className="text-sm font-medium">Ready to Visualize</p>
                    <p className="text-xs opacity-50 max-w-[200px] text-center">Click 'Run Simulation' to fetch and map vectors</p>
                </div>
            )}
        </div>
      </div>

      {/* --- RIGHT: Sidebar (Controls + Details) --- */}
      <div className="w-80 border-l border-border/50 bg-secondary/5 flex flex-col shrink-0">
        
        {/* Top Pane: Controls */}
        <div className="flex-1 flex flex-col border-b border-border/50 overflow-y-auto">
            <div className="p-3 border-b border-border/50 bg-secondary/10 flex items-center gap-2">
                <Settings2 size={14} className="text-muted-foreground"/>
                <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Controls</span>
            </div>
            
            <div className="p-5 space-y-6">
                <div>
                     <label className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold mb-2 block">Algorithm</label>
                     <div className="flex p-1 bg-secondary/30 rounded-lg border border-border/50">
                        {['UMAP', 'TSNE'].map(algo => (
                            <button
                                key={algo}
                                onClick={() => setConfig({...config, algorithm: algo})}
                                className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-all ${
                                    config.algorithm === algo 
                                    ? 'bg-background shadow-sm text-accent' 
                                    : 'text-muted-foreground hover:text-foreground'
                                }`}
                            >
                                {algo}
                            </button>
                        ))}
                     </div>
                </div>

                <div>
                    <div className="flex justify-between items-center mb-2">
                        <label className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">Sample Limit</label>
                        <span className="text-[10px] font-mono text-muted-foreground bg-secondary/50 px-1.5 py-0.5 rounded">{config.limit} pts</span>
                    </div>
                    <input 
                        type="range" min="100" max="2000" step="100"
                        value={config.limit}
                        onChange={(e) => setConfig({...config, limit: parseInt(e.target.value)})}
                        className="w-full h-1.5 bg-secondary/50 rounded-lg appearance-none cursor-pointer accent-accent"
                    />
                </div>
                
                {config.algorithm === 'UMAP' && (
                <>
                <div>
                    <div className="flex justify-between items-center mb-2">
                        <label className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">Neighbors</label>
                        <span className="text-[10px] font-mono text-muted-foreground bg-secondary/50 px-1.5 py-0.5 rounded">{config.nNeighbors}</span>
                    </div>
                    <input 
                        type="range" min="2" max="50" 
                        value={config.nNeighbors}
                        onChange={(e) => setConfig({...config, nNeighbors: parseInt(e.target.value)})}
                        className="w-full h-1.5 bg-secondary/50 rounded-lg appearance-none cursor-pointer accent-accent"
                    />
                </div>

                <div>
                    <div className="flex justify-between items-center mb-2">
                        <label className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">Min Distance</label>
                        <span className="text-[10px] font-mono text-muted-foreground bg-secondary/50 px-1.5 py-0.5 rounded">{config.minDist}</span>
                    </div>
                    <input 
                        type="range" min="0.01" max="1" step="0.01"
                        value={config.minDist}
                        onChange={(e) => setConfig({...config, minDist: parseFloat(e.target.value)})}
                        className="w-full h-1.5 bg-secondary/50 rounded-lg appearance-none cursor-pointer accent-accent"
                    />
                </div>
                </>
                )}

                <button 
                  onClick={fetchDataAndRun}
                  disabled={loading}
                  className={`w-full py-2.5 px-4 rounded-lg text-xs font-bold shadow-lg transition-all transform active:scale-[0.98] flex justify-center items-center gap-2 ${
                    loading 
                      ? 'bg-secondary text-muted-foreground cursor-not-allowed' 
                      : 'bg-primary text-primary-foreground hover:bg-primary/90'
                  }`}
                >
                  {loading && <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
                  {loading ? 'Processing...' : 'Run Simulation'}
                </button>
            </div>
        </div>

        {/* Bottom Pane: Point Details */}
        <div className="h-1/3 min-h-[200px] flex flex-col bg-background relative">
             <div className="p-3 border-b border-border/50 bg-secondary/10 flex items-center gap-2">
                <Info size={14} className="text-muted-foreground"/>
                <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Point Details</span>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4">
                {activePoint ? (
                    <div className="space-y-4">
                        <div className="space-y-1">
                            <label className="text-[10px] uppercase tracking-wide text-muted-foreground">Document</label>
                            <p className="text-sm font-medium leading-normal">{activePoint.book}</p>
                        </div>
                        
                        <div className="space-y-2">
                            <label className="text-[10px] uppercase tracking-wide text-muted-foreground">Keywords</label>
                            <div className="flex flex-wrap gap-1.5">
                                {activePoint.keywords?.map((k: string, i: number) => (
                                    <span key={i} className="px-2 py-0.5 rounded-md bg-secondary/50 border border-border/50 text-[10px] text-muted-foreground">
                                        {k}
                                    </span>
                                ))}
                            </div>
                        </div>

                         {/* Placeholder for future metadata */}
                         <div className="p-3 rounded bg-secondary/20 border border-border/30 text-[10px] font-mono text-muted-foreground break-all">
                             ID: {Math.random().toString(36).substr(2, 9).toUpperCase()}
                             <br/>
                             Score: {(Math.random() * 0.5 + 0.5).toFixed(4)}
                         </div>
                    </div>
                ) : (
                    <div className="h-full flex flex-col items-center justify-center text-muted-foreground/40 gap-2">
                         <MousePointer2 size={24} className="opacity-50"/>
                         <p className="text-xs">Click a point to view details</p>
                    </div>
                )}
            </div>
        </div>
        
      </div>
    </div>
  );
};

export default VectorDashboard;
