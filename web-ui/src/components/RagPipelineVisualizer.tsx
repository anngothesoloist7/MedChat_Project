import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FileText, Scan, Database, CheckCircle, BrainCircuit } from 'lucide-react';

// Configuration based on your rag-pipeline.md
const PHASES = [
  {
    id: 1,
    title: "Phase 1: Splitting & Metadata",
    description: "Splitting large PDF & Extracting Metadata (Gemini)",
    icon: FileText,
    color: "text-blue-500",
    bg: "bg-blue-500"
  },
  {
    id: 2,
    title: "Phase 2: OCR & Parsing",
    description: "Mistral AI OCR & Medical Translation",
    icon: Scan,
    color: "text-purple-500",
    bg: "bg-purple-500"
  },
  {
    id: 3,
    title: "Phase 3: Vector Indexing",
    description: "Hybrid Embedding (Dense+Sparse) -> Qdrant",
    icon: Database,
    color: "text-emerald-500",
    bg: "bg-emerald-500"
  }
];

interface RagPipelineVisualizerProps {
    currentPhase?: number | null;
    isLoading?: boolean;
    currentAction?: string;
}

const RagPipelineVisualizer = ({ currentPhase = 1, isLoading = true, currentAction }: RagPipelineVisualizerProps) => {
  // Ensure currentPhase is valid (1-3), default to 1 if null/undefined
  const activePhase = currentPhase || 1;

  return (
    <div className="w-full max-w-2xl p-6 bg-slate-900 rounded-xl shadow-2xl border border-slate-800 mx-auto">
      <div className="flex justify-between mb-8 relative">
        {/* Connecting Line */}
        <div className="absolute top-1/2 left-0 w-full h-1 bg-slate-800 -z-0 transform -translate-y-1/2" />
        
        {PHASES.map((phase, index) => {
          const isActive = activePhase === phase.id;
          const isCompleted = activePhase > phase.id;
          const Icon = isCompleted ? CheckCircle : phase.icon;

          return (
            <div key={phase.id} className="relative z-10 flex flex-col items-center">
              <motion.div
                initial={false}
                animate={{
                  scale: isActive ? 1.2 : 1,
                  backgroundColor: isActive || isCompleted ? "#0f172a" : "#1e293b",
                  borderColor: isActive || isCompleted ? (index === 0 ? '#3b82f6' : index === 1 ? '#a855f7' : '#10b981') : '#334155',
                }}
                className={`w-12 h-12 rounded-full border-2 flex items-center justify-center transition-colors duration-500`}
              >
                <Icon size={20} className={isCompleted || isActive ? phase.color : "text-slate-500"} />
              </motion.div>
              
              <div className="mt-2 text-xs font-mono text-slate-400">Step {phase.id}</div>
            </div>
          );
        })}
      </div>

      {/* Active Phase Content Animation */}
      <div className="h-64 relative bg-slate-800/50 rounded-lg overflow-hidden border border-slate-700">
        <AnimatePresence mode="wait">
          {activePhase === 1 && isLoading && <SplittingAnimation key="p1" />}
          {activePhase === 2 && isLoading && <OcrAnimation key="p2" />}
          {activePhase === 3 && isLoading && <EmbeddingAnimation key="p3" />}
          {!isLoading && <CompleteAnimation key="done" />}
        </AnimatePresence>
        
        <div className="absolute bottom-0 w-full p-4 bg-slate-900/90 border-t border-slate-700 backdrop-blur-sm">
           <div className="flex justify-between items-end">
             <div>
               <h3 className="text-slate-200 font-bold text-sm">
                 {isLoading ? PHASES[activePhase - 1]?.title : "Pipeline Completed"}
               </h3>
               <p className="text-slate-400 text-xs mt-1">
                 {isLoading ? PHASES[activePhase - 1]?.description : "All chunks indexed successfully."}
               </p>
             </div>
             {isLoading && currentAction && (
               <motion.div 
                 initial={{ opacity: 0, y: 10 }}
                 animate={{ opacity: 1, y: 0 }}
                 key={currentAction}
                 className="text-xs font-mono text-primary bg-primary/10 px-2 py-1 rounded border border-primary/20"
               >
                 {currentAction}
               </motion.div>
             )}
           </div>
        </div>
      </div>
    </div>
  );
};

// --- Sub-Animations ---

// Phase 1: File splitting into chunks
const SplittingAnimation = () => {
  return (
    <div className="w-full h-full flex items-center justify-center relative">
      <motion.div
        animate={{ x: -60, opacity: 0.5 }}
        transition={{ duration: 2, repeat: Infinity, repeatType: "reverse" }}
      >
        <FileText size={64} className="text-slate-600" />
      </motion.div>
      
      {/* Generated Chunks flying out */}
      {[1, 2, 3].map((i) => (
        <motion.div
          key={i}
          initial={{ x: 0, opacity: 0, scale: 0.5 }}
          animate={{ x: 40 + (i * 20), opacity: 1, scale: 1 }}
          transition={{ duration: 1.5, delay: i * 0.3, repeat: Infinity }}
          className="absolute"
        >
           <div className="w-10 h-12 bg-blue-900/80 border border-blue-500/50 rounded flex items-center justify-center">
             <span className="text-[8px] text-blue-200">PDF {i}</span>
           </div>
        </motion.div>
      ))}
    </div>
  );
};

// Phase 2: Scanning Effect (Mistral)
const OcrAnimation = () => {
  return (
    <div className="w-full h-full flex flex-col items-center justify-center p-8">
      <div className="relative w-48 h-32 bg-slate-700 rounded-md overflow-hidden border border-slate-600">
        {/* Mock Text Lines */}
        <div className="p-4 space-y-2">
          <div className="h-2 w-3/4 bg-slate-500 rounded" />
          <div className="h-2 w-full bg-slate-500 rounded" />
          <div className="h-2 w-5/6 bg-slate-500 rounded" />
          <div className="h-2 w-4/5 bg-slate-500 rounded" />
        </div>
        
        {/* Scanning Beam */}
        <motion.div
          animate={{ top: ["0%", "100%"] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
          className="absolute left-0 w-full h-1 bg-purple-500 shadow-[0_0_15px_rgba(168,85,247,0.8)]"
        />
      </div>
      <motion.div 
        animate={{ opacity: [0, 1, 0] }}
        transition={{ duration: 2, repeat: Infinity }}
        className="mt-4 text-xs text-purple-400 font-mono flex items-center gap-2"
      >
        <BrainCircuit size={12} /> Detecting Medical Terms...
      </motion.div>
    </div>
  );
};

// Phase 3: Embedding (Text to Vector)
const EmbeddingAnimation = () => {
  return (
    <div className="w-full h-full flex items-center justify-center gap-8">
      {/* Source Chunk */}
      <div className="w-16 h-20 bg-slate-700 border border-slate-600 rounded flex items-center justify-center">
        <span className="text-[10px] text-slate-300">Chunk</span>
      </div>

      {/* Transformation Stream */}
      <div className="flex gap-1">
        {[...Array(5)].map((_, i) => (
          <motion.div
            key={i}
            animate={{ 
              x: [0, 60],
              opacity: [0, 1, 0],
              scale: [1, 0.5]
            }}
            transition={{ 
              duration: 1, 
              delay: i * 0.2, 
              repeat: Infinity 
            }}
            className="w-2 h-2 rounded-full bg-emerald-400"
          />
        ))}
      </div>

      {/* Qdrant DB */}
      <div className="relative w-24 h-24">
        <Database size={64} className="text-emerald-700 absolute" />
        <motion.div
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="absolute inset-0 flex items-center justify-center pt-2"
        >
          <span className="text-xs font-bold text-emerald-200">Qdrant</span>
        </motion.div>
      </div>
    </div>
  );
};

const CompleteAnimation = () => (
  <div className="w-full h-full flex flex-col items-center justify-center">
    <motion.div
      initial={{ scale: 0 }}
      animate={{ scale: 1 }}
      className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mb-4"
    >
      <CheckCircle size={32} className="text-green-500" />
    </motion.div>
    <h3 className="text-white font-bold">Processing Complete</h3>
  </div>
);

export default RagPipelineVisualizer;
