"use client";
import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { UploadCloud, AlertCircle, Check, Loader2, FileText, ArrowRight, Sparkles } from 'lucide-react';

type PipelineState = 'idle' | 'checking' | 'confirming' | 'processing' | 'completed';

export default function GeminiPipeline() {
  const [state, setState] = useState<PipelineState>('idle');
  const [filename, setFilename] = useState('');
  const [logs, setLogs] = useState<{ step: number, message: string } | null>(null);
  
  // WebSocket ref
  const socketRef = useRef<WebSocket | null>(null);

  const connectWebSocket = () => {
    if (socketRef.current) socketRef.current.close();
    // Assuming port 8000 for backend based on previous context
    const socket = new WebSocket("ws://localhost:8000/ws/pipeline");
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setLogs(data);
      if (data.status === 'completed') setState('completed');
    };
    socketRef.current = socket;
  };

  // 1. Upload & Check
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setState('checking');
    setFilename(file.name);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('http://localhost:8000/check-file', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();

      if (data.exists) {
        setState('confirming');
      } else {
        startPipeline(file.name, false);
      }
    } catch (err) {
      console.error(err);
      setState('idle');
    }
  };

  // 2. Start Pipeline
  const startPipeline = async (name: string, overwrite: boolean) => {
    setState('processing');
    connectWebSocket();
    
    await fetch('http://localhost:8000/start-rag', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename: name, overwrite }),
    });
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background text-foreground font-sans selection:bg-accent selection:text-accent-foreground">
      <div className="w-full max-w-lg p-8">
        
        {/* Header Gemini Style */}
        <motion.div layout className="mb-10 text-center">
          <div className="inline-flex items-center gap-2 mb-2 px-3 py-1 rounded-full bg-secondary/50 border border-border">
            <Sparkles className="w-3 h-3 text-accent-foreground" />
            <span className="text-[10px] uppercase tracking-widest text-muted-foreground font-medium">Gemini 2.0 Ingestion</span>
          </div>
          <h1 className="text-2xl font-medium tracking-tight text-foreground bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text text-transparent">
            Knowledge Base
          </h1>
        </motion.div>

        <div className="relative min-h-[220px] flex flex-col items-center justify-center bg-secondary/30 border border-border rounded-2xl p-6 backdrop-blur-sm">
          <AnimatePresence mode='wait'>
            
            {/* STATE: IDLE */}
            {state === 'idle' && (
              <motion.div
                key="idle"
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.98 }}
                className="w-full"
              >
                <label className="flex flex-col items-center justify-center w-full h-48 border border-dashed border-muted-foreground/30 rounded-xl cursor-pointer hover:bg-secondary/50 transition-all duration-300 group">
                  <div className="flex flex-col items-center justify-center">
                    <div className="p-4 rounded-full bg-secondary mb-4 group-hover:scale-110 transition-transform duration-300 shadow-sm">
                        <UploadCloud className="w-6 h-6 text-accent-foreground" strokeWidth={1.5} />
                    </div>
                    <p className="text-sm text-foreground/80 font-medium">Upload Document</p>
                    <p className="text-xs text-muted-foreground mt-1">PDF files supported</p>
                  </div>
                  <input type="file" accept=".pdf" className="hidden" onChange={handleFileUpload} />
                </label>
              </motion.div>
            )}

            {/* STATE: CHECKING */}
            {state === 'checking' && (
              <motion.div
                key="checking"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex flex-col items-center gap-4 py-8"
              >
                <div className="relative">
                    <div className="absolute inset-0 bg-accent/20 blur-xl rounded-full" />
                    <Loader2 className="w-8 h-8 animate-spin text-accent-foreground relative z-10" />
                </div>
                <span className="text-sm text-muted-foreground animate-pulse">Analyzing content...</span>
              </motion.div>
            )}

            {/* STATE: CONFIRMING */}
            {state === 'confirming' && (
              <motion.div
                key="confirming"
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -5 }}
                className="w-full"
              >
                <div className="flex flex-col items-center text-center p-2">
                  <div className="p-3 bg-amber-500/10 rounded-full text-amber-500 mb-3 border border-amber-500/20">
                    <AlertCircle size={24} strokeWidth={1.5} />
                  </div>
                  <h3 className="text-base font-medium text-foreground">File Exists</h3>
                  <p className="text-sm text-muted-foreground mt-2 mb-6 leading-relaxed max-w-xs">
                    <span className="text-foreground font-medium">{filename}</span> is already in the database.
                  </p>
                  <div className="flex gap-3 w-full justify-center">
                    <button 
                      onClick={() => setState('idle')}
                      className="px-4 py-2 rounded-lg text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                    >
                      Cancel
                    </button>
                    <button 
                      onClick={() => startPipeline(filename, true)}
                      className="px-4 py-2 bg-accent text-accent-foreground rounded-lg text-sm font-medium hover:brightness-110 transition-all shadow-[0_0_15px_-3px_var(--color-accent)] flex items-center gap-2"
                    >
                      Overwrite <ArrowRight size={14} />
                    </button>
                  </div>
                </div>
              </motion.div>
            )}

            {/* STATE: PROCESSING */}
            {state === 'processing' && (
              <motion.div
                key="processing"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="w-full space-y-6 px-2"
              >
                <div className="flex items-center gap-3 pb-4 border-b border-border/50">
                    <FileText className="w-4 h-4 text-accent-foreground" />
                    <span className="text-sm text-foreground/90 font-medium truncate">{filename}</span>
                </div>

                <div className="space-y-5 relative pl-2">
                    <div className="absolute left-[11px] top-2 bottom-2 w-[1px] bg-border/50" />
                    
                    {[1, 2, 3].map((stepIdx) => {
                        const currentStep = logs?.step || 0;
                        const isActive = currentStep === stepIdx;
                        const isDone = currentStep > stepIdx;
                        
                        return (
                            <div key={stepIdx} className="relative flex items-center gap-4">
                                <motion.div 
                                    className={`w-5 h-5 rounded-full border flex items-center justify-center z-10 
                                        ${isActive ? 'border-accent-foreground bg-accent text-accent-foreground' : 
                                          isDone ? 'border-primary/50 bg-primary/20 text-primary' : 'border-border bg-background'}`}
                                    animate={{ scale: isActive ? 1.1 : 1 }}
                                    transition={{ type: "spring", stiffness: 300, damping: 20 }}
                                >
                                    {isDone && <Check size={10} />}
                                    {isActive && <div className="w-1.5 h-1.5 bg-current rounded-full animate-pulse" />}
                                </motion.div>
                                <div className={`${isActive ? 'opacity-100' : isDone ? 'opacity-60' : 'opacity-30'} transition-opacity`}>
                                    <p className="text-[10px] font-bold uppercase tracking-widest mb-0.5">Phase 0{stepIdx}</p>
                                    <p className="text-sm font-medium">
                                        {stepIdx === 1 ? 'Smart Splitting' : 
                                         stepIdx === 2 ? 'OCR & Reasoning' : 
                                         'Vector Indexing'}
                                    </p>
                                </div>
                            </div>
                        )
                    })}
                </div>
                
                <div className="pt-2">
                    <p className="text-xs text-muted-foreground font-mono text-center opacity-70">
                        {`> ${logs?.message || "Initializing system..."}`}
                    </p>
                </div>
              </motion.div>
            )}

             {/* STATE: COMPLETED */}
             {state === 'completed' && (
                <motion.div
                    key="completed"
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="flex flex-col items-center text-center py-4"
                >
                    <div className="w-14 h-14 bg-green-500/10 text-green-400 rounded-full flex items-center justify-center mb-5 border border-green-500/20 shadow-[0_0_30px_-10px_rgba(74,222,128,0.3)]">
                        <Check size={28} />
                    </div>
                    <h3 className="text-lg font-medium text-foreground">Ingestion Complete</h3>
                    <p className="text-sm text-muted-foreground mt-2 mb-8 max-w-[200px]">
                        The document has been securely indexed.
                    </p>
                    <button 
                        onClick={() => { setState('idle'); setLogs(null); }}
                        className="text-sm px-6 py-2 rounded-full border border-border hover:bg-secondary text-foreground transition-all duration-300"
                    >
                        Upload New
                    </button>
                </motion.div>
             )}

          </AnimatePresence>
        </div>
        
        {/* Footer */}
        <div className="mt-8 text-center">
            <p className="text-[10px] text-muted-foreground/50 font-mono">POWERED BY MEDCHAT RAG ENGINE</p>
        </div>
      </div>
    </div>
  );
}
