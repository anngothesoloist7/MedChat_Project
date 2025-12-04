'use client';

import { useState, useEffect, useRef } from 'react';
import { Upload, FileText, Database, CheckCircle, XCircle, Clock, Play, Pause, Settings, ChevronDown, ChevronRight, AlertTriangle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import RagPipelineVisualizer from '@/components/RagPipelineVisualizer';

interface ProcessingFile {
  id: string;
  file?: File;
  url?: string;
  name: string;
  size: number;
  status: 'pending' | 'processing' | 'completed' | 'error' | 'waiting_for_decision';
  currentPhase?: 1 | 2 | 3 | null;
  progress: {
    phase1: { status: 'pending' | 'processing' | 'completed' | 'error' | 'skipped'; message?: string };
    phase2: { status: 'pending' | 'processing' | 'completed' | 'error' | 'skipped'; message?: string };
    phase3: { status: 'pending' | 'processing' | 'completed' | 'error' | 'skipped'; message?: string };
  };
  logs: string[];
  currentAction?: string;
}

interface PipelineSettings {
  selectedPhases: { p1: boolean; p2: boolean; p3: boolean };
  cleanup: boolean;
  targetChunkSize: number;
  maxPages: number;
  chunkSize: number;
  chunkOverlap: number;
}

export default function PipelinePage() {
  const [files, setFiles] = useState<ProcessingFile[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [expandedFiles, setExpandedFiles] = useState<Set<string>>(new Set());
  const [showSettings, setShowSettings] = useState(false);
  const [settings, setSettings] = useState<PipelineSettings>({
    selectedPhases: { p1: true, p2: true, p3: true },
    cleanup: false,
    targetChunkSize: 50,
    maxPages: 500,
    chunkSize: 1000,
    chunkOverlap: 200,
  });

  // Modal State
  const [showOverwriteModal, setShowOverwriteModal] = useState(false);
  const [currentConflictFile, setCurrentConflictFile] = useState<{ id: string, name: string, count: number } | null>(null);

  // Polling ref to access latest files state inside interval
  const filesRef = useRef(files);
  useEffect(() => { filesRef.current = files; }, [files]);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    const newFiles: ProcessingFile[] = selectedFiles.map(file => ({
      id: Math.random().toString(36).substr(2, 9),
      file: file,
      name: file.name,
      size: file.size,
      status: 'pending',
      currentPhase: null,
      progress: {
        phase1: { status: 'pending' },
        phase2: { status: 'pending' },
        phase3: { status: 'pending' },
      },
      logs: [],
      currentAction: 'Initializing...',
    }));
    setFiles(prev => [...prev, ...newFiles]);
  };

  const toggleFileExpanded = (id: string) => {
    setExpandedFiles(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const startProcessing = async () => {
    setIsProcessing(true);
    
    const pendingFiles = files.filter(f => f.status === 'pending');
    
    for (const file of pendingFiles) {
      // Step 1: Check if file exists
      try {
        const checkFormData = new FormData();
        if (file.file) checkFormData.append('file', file.file);
        checkFormData.append('check_only', 'true');

        const checkRes = await fetch('http://localhost:8000/process', {
            method: 'POST',
            body: checkFormData
        });
        
        if (!checkRes.ok) throw new Error('Failed to check file existence');
        
        const checkData = await checkRes.json();
        // Assuming single file upload per request for now, or we handle the first result
        const result = checkData.results && checkData.results[0];
        
        if (result && result.exists) {
            // Pause and ask user
            setFiles(prev => prev.map(f => f.id === file.id ? { ...f, status: 'waiting_for_decision' } : f));
            setCurrentConflictFile({ id: file.id, name: file.name, count: result.count });
            setShowOverwriteModal(true);
            
            // We need to wait for user input. 
            // Since we are in a loop, we can't easily "pause" execution here without a promise that resolves on user action.
            // But React state updates are async.
            // A simple way is to break the loop and let the Modal's action trigger the next step.
            // However, we want to process other files too?
            // For simplicity, let's stop the loop and handle this one file. 
            // The user will have to click "Start" again for remaining files or we chain them.
            // Better: Just return and let the Modal callbacks handle the actual processing call.
            return; 
        } else {
            // No conflict, proceed directly
            await executePipeline(file, true);
        }

      } catch (error) {
        console.error(error);
        setFiles(prev => prev.map(f => f.id === file.id ? { 
            ...f, 
            status: 'error', 
            logs: [...f.logs, `[ERROR] Failed to check existence: ${String(error)}`] 
        } : f));
      }
    }
    
    // If we reached here without returning, it means all pending files (that didn't have conflicts) are started.
    // If there was a conflict, we returned early.
  };

  const executePipeline = async (file: ProcessingFile, runPhase1: boolean) => {
      const formData = new FormData();
      if (file.file) formData.append('file', file.file);
      
      formData.append('p1', runPhase1.toString());
      formData.append('p2', settings.selectedPhases.p2.toString());
      formData.append('p3', settings.selectedPhases.p3.toString());
      formData.append('clean', settings.cleanup.toString());
      formData.append('overwrite', runPhase1 ? 'true' : 'false');

      try {
        setFiles(prev => prev.map(f => f.id === file.id ? { ...f, status: 'processing' } : f));
        
        const response = await fetch('http://localhost:8000/process', {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
           const err = await response.json();
           throw new Error(err.detail || 'Failed to start pipeline');
        }
        
      } catch (error) {
        console.error(error);
        setFiles(prev => prev.map(f => f.id === file.id ? { 
            ...f, 
            status: 'error', 
            logs: [...f.logs, `[ERROR] Failed to start: ${String(error)}`] 
        } : f));
      }
  };

  const handleOverwriteDecision = async (overwrite: boolean) => {
      setShowOverwriteModal(false);
      if (!currentConflictFile) return;

      const file = files.find(f => f.id === currentConflictFile.id);
      if (file) {
          // If overwrite, we run Phase 1 (p1=true).
          // If NOT overwrite (Use Existing), we skip Phase 1 (p1=false).
          await executePipeline(file, overwrite);
      }
      
      setCurrentConflictFile(null);
      
      // Continue processing other pending files?
      // We can call startProcessing() again to pick up the next pending file.
      // Use setTimeout to allow state updates to settle.
      setTimeout(() => startProcessing(), 100);
  };

  // Polling for status
  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    // Only poll if there are processing files
    const hasProcessing = files.some(f => f.status === 'processing');
    
    if (hasProcessing || isProcessing) {
      interval = setInterval(async () => {
        try {
          const res = await fetch('http://localhost:8000/status?limit=100');
          const data = await res.json();
          const logs: string[] = data.logs || [];
          
          setFiles(prevFiles => prevFiles.map(f => {
            if (f.status !== 'processing') return f;

            // Simple log matching logic
            const stem = f.name.replace(/\.pdf$/i, '');
            const relevantLogs = logs.filter((l: string) => l.includes(stem) || l.includes(f.name));
            
            let newProgress = { ...f.progress };
            let currentPhase = f.currentPhase;
            let overallStatus: ProcessingFile['status'] = f.status;

            let currentAction = f.currentAction;

            relevantLogs.forEach((log: string) => {
                // Phase 1
                if (log.includes("PHASE: Split")) {
                    if (log.includes("STARTED")) {
                        newProgress.phase1.status = 'processing';
                        currentPhase = 1;
                        currentAction = "Starting Split Phase...";
                    }
                    if (log.includes("COMPLETED")) newProgress.phase1.status = 'completed';
                    if (log.includes("SKIPPED")) newProgress.phase1.status = 'skipped';
                    if (log.includes("FAILED") || log.includes("ERROR")) newProgress.phase1.status = 'error';
                }
                if (log.includes("Extracting metadata")) currentAction = "Extracting Metadata...";
                if (log.includes("Splitting...")) currentAction = "Splitting PDF...";
                if (log.includes("Created:")) currentAction = "Created Chunk...";

                // Phase 2
                if (log.includes("PHASE: OCR")) {
                    if (log.includes("STARTED")) {
                        newProgress.phase2.status = 'processing';
                        currentPhase = 2;
                        currentAction = "Starting OCR Phase...";
                    }
                    if (log.includes("COMPLETED")) newProgress.phase2.status = 'completed';
                    if (log.includes("SKIPPED")) newProgress.phase2.status = 'skipped';
                    if (log.includes("ERROR")) newProgress.phase2.status = 'error';
                }
                if (log.includes("Uploading")) currentAction = "Uploading to Mistral...";
                if (log.includes("Requesting OCR")) currentAction = "Requesting OCR...";
                if (log.includes("OCR Done")) currentAction = "OCR Completed";
                if (log.includes("Parsing markdown")) currentAction = "Parsing Markdown...";

                // Phase 3
                if (log.includes("PHASE: Embedding")) {
                    if (log.includes("STARTED")) {
                        newProgress.phase3.status = 'processing';
                        currentPhase = 3;
                        currentAction = "Starting Embedding Phase...";
                    }
                    if (log.includes("COMPLETED")) {
                        newProgress.phase3.status = 'completed';
                        overallStatus = 'completed';
                        currentPhase = null;
                        currentAction = "Pipeline Completed";
                    }
                    if (log.includes("SKIPPED")) {
                        newProgress.phase3.status = 'skipped';
                        overallStatus = 'completed';
                        currentAction = "Pipeline Skipped";
                    }
                    if (log.includes("ERROR")) newProgress.phase3.status = 'error';
                }
                if (log.includes("Indexing")) {
                    // Extract batch info if possible
                    const match = log.match(/Indexing ([\d,]+) chunks/);
                    currentAction = match ? `Indexing ${match[1]} Chunks...` : "Indexing Chunks...";
                }
                if (log.includes("VERIFY")) currentAction = "Verifying Index...";
            });

            const uniqueLogs = Array.from(new Set([...f.logs, ...relevantLogs]));
            
            return {
                ...f,
                status: overallStatus,
                currentPhase,
                progress: newProgress,
                logs: uniqueLogs,
                currentAction
            };
          }));

        } catch (e) {
          console.error("Polling error:", e);
        }
      }, 500);
    }
    
    return () => clearInterval(interval);
  }, [files, isProcessing]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'error': return <XCircle className="w-5 h-5 text-red-500" />;
      case 'processing': return <Clock className="w-5 h-5 text-blue-500 animate-spin" />;
      case 'skipped': return <div className="w-5 h-5 text-muted-foreground">-</div>;
      case 'waiting_for_decision': return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
      default: return <div className="w-5 h-5 rounded-full border-2 border-muted" />;
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="min-h-screen bg-background text-foreground relative">
      {/* Overwrite Modal */}
      <AnimatePresence>
        {showOverwriteModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-background border border-border rounded-xl p-6 max-w-md w-full shadow-xl"
            >
              <div className="flex items-center gap-3 mb-4 text-yellow-500">
                <AlertTriangle className="w-8 h-8" />
                <h3 className="text-lg font-semibold text-foreground">File Already Exists</h3>
              </div>
              <p className="text-muted-foreground mb-6">
                The file <span className="font-medium text-foreground">{currentConflictFile?.name}</span> has already been processed ({currentConflictFile?.count} items found in Database/Local).
                <br /><br />
                Do you want to re-process and overwrite the existing data, or use the existing data for subsequent phases?
              </p>
              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => handleOverwriteDecision(false)}
                  className="px-4 py-2 bg-secondary hover:bg-secondary/80 text-secondary-foreground rounded-lg transition"
                >
                  Use Existing
                </button>
                <button
                  onClick={() => handleOverwriteDecision(true)}
                  className="px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg transition"
                >
                  Overwrite
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Header */}
      <header className="border-b border-border bg-secondary/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-foreground">RAG Pipeline Manager</h1>
              <p className="text-sm text-muted-foreground mt-1">Process medical PDFs through the complete RAG pipeline</p>
            </div>
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="px-4 py-2 bg-primary/10 hover:bg-primary/20 border border-primary/30 rounded-lg transition-all flex items-center gap-2"
            >
              <Settings className="w-4 h-4" />
              Settings
            </button>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-6 py-8 max-w-7xl">
        {/* Settings Panel */}
        <AnimatePresence>
          {showSettings && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mb-8 overflow-hidden"
            >
              <div className="bg-secondary/30 border border-border rounded-xl p-6">
                <h2 className="text-lg font-semibold mb-4">Pipeline Configuration</h2>
                
                {/* Phase Selection */}
                <div className="mb-6">
                  <h3 className="text-sm font-medium text-muted-foreground mb-3">Select Phases</h3>
                  <div className="flex gap-4">
                    {[
                      { key: 'p1', label: 'Phase 1: Splitting & Metadata', icon: FileText },
                      { key: 'p2', label: 'Phase 2: OCR & Parsing', icon: Upload },
                      { key: 'p3', label: 'Phase 3: Embedding & Indexing', icon: Database },
                    ].map(({ key, label, icon: Icon }) => (
                      <label key={key} className="flex items-center gap-3 cursor-pointer group">
                        <input
                          type="checkbox"
                          checked={settings.selectedPhases[key as keyof typeof settings.selectedPhases]}
                          onChange={(e) => setSettings(prev => ({
                            ...prev,
                            selectedPhases: {
                              ...prev.selectedPhases,
                              [key]: e.target.checked
                            }
                          }))}
                          className="w-4 h-4 rounded border-border text-primary focus:ring-2 focus:ring-primary/50"
                        />
                        <Icon className="w-4 h-4 text-muted-foreground group-hover:text-foreground transition" />
                        <span className="text-sm group-hover:text-foreground transition">{label}</span>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Advanced Settings */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <label className="text-xs text-muted-foreground block mb-1">Target Chunk Size (MB)</label>
                    <input
                      type="number"
                      value={settings.targetChunkSize}
                      onChange={(e) => setSettings(prev => ({ ...prev, targetChunkSize: parseInt(e.target.value) }))}
                      className="w-full px-3 py-2 bg-input border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground block mb-1">Max Pages per Chunk</label>
                    <input
                      type="number"
                      value={settings.maxPages}
                      onChange={(e) => setSettings(prev => ({ ...prev, maxPages: parseInt(e.target.value) }))}
                      className="w-full px-3 py-2 bg-input border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground block mb-1">Chunk Size (chars)</label>
                    <input
                      type="number"
                      value={settings.chunkSize}
                      onChange={(e) => setSettings(prev => ({ ...prev, chunkSize: parseInt(e.target.value) }))}
                      className="w-full px-3 py-2 bg-input border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground block mb-1">Chunk Overlap</label>
                    <input
                      type="number"
                      value={settings.chunkOverlap}
                      onChange={(e) => setSettings(prev => ({ ...prev, chunkOverlap: parseInt(e.target.value) }))}
                      className="w-full px-3 py-2 bg-input border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                  </div>
                </div>

                {/* Cleanup Option */}
                <div className="mt-4">
                  <label className="flex items-center gap-3 cursor-pointer group">
                    <input
                      type="checkbox"
                      checked={settings.cleanup}
                      onChange={(e) => setSettings(prev => ({ ...prev, cleanup: e.target.checked }))}
                      className="w-4 h-4 rounded border-border text-primary focus:ring-2 focus:ring-primary/50"
                    />
                    <span className="text-sm group-hover:text-foreground transition">Clean up temporary files after processing</span>
                  </label>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Upload Area */}
        <div className="mb-8">
          <div className="border-2 border-dashed border-border rounded-xl p-12 text-center hover:border-primary/50 transition-colors bg-secondary/20">
            <Upload className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="text-lg font-semibold mb-2">Upload PDF Files</h3>
            <p className="text-sm text-muted-foreground mb-4">Select one or more PDF files to process through the pipeline</p>
            <label className="inline-block">
              <input
                type="file"
                accept=".pdf"
                multiple
                onChange={handleFileUpload}
                className="hidden"
              />
              <span className="px-6 py-3 bg-primary text-primary-foreground rounded-lg font-medium cursor-pointer hover:opacity-90 transition inline-block">
                Select Files
              </span>
            </label>
          </div>
        </div>

        {/* Visualizer */}
        {(isProcessing || files.some(f => f.status === 'completed')) && (
          <div className="mb-8 flex justify-center">
             <RagPipelineVisualizer 
                currentPhase={files.find(f => f.status === 'processing')?.currentPhase || (files.every(f => f.status === 'completed') ? 3 : 1)} 
                isLoading={isProcessing} 
                currentAction={files.find(f => f.status === 'processing')?.currentAction}
             />
          </div>
        )}

        {/* File Queue */}
        {files.length > 0 && (
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">Processing Queue ({files.length})</h2>
              <button
                onClick={startProcessing}
                disabled={isProcessing || files.every(f => f.status !== 'pending')}
                className="px-6 py-3 bg-primary text-primary-foreground rounded-lg font-medium hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isProcessing ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                {isProcessing ? 'Processing...' : 'Start Pipeline'}
              </button>
            </div>

            <div className="space-y-3">
              {files.map(file => (
                <div key={file.id} className="bg-secondary/30 border border-border rounded-xl overflow-hidden">
                  {/* File Header */}
                  <div
                    onClick={() => toggleFileExpanded(file.id)}
                    className="p-4 cursor-pointer hover:bg-secondary/50 transition flex items-center justify-between"
                  >
                    <div className="flex items-center gap-3 flex-1">
                      <button className="text-muted-foreground hover:text-foreground transition">
                        {expandedFiles.has(file.id) ? (
                          <ChevronDown className="w-5 h-5" />
                        ) : (
                          <ChevronRight className="w-5 h-5" />
                        )}
                      </button>
                      <FileText className="w-5 h-5 text-blue-500" />
                      <div className="flex-1">
                        <div className="font-medium">{file.name}</div>
                        <div className="text-xs text-muted-foreground">{formatBytes(file.size)}</div>
                      </div>
                    </div>

                    {/* Status Badge */}
                    <div className={`px-3 py-1 rounded-full text-xs font-medium ${
                      file.status === 'completed' ? 'bg-green-500/20 text-green-500' :
                      file.status === 'error' ? 'bg-red-500/20 text-red-500' :
                      file.status === 'processing' ? 'bg-blue-500/20 text-blue-500' :
                      file.status === 'waiting_for_decision' ? 'bg-yellow-500/20 text-yellow-500' :
                      'bg-muted/50 text-muted-foreground'
                    }`}>
                      {file.status.toUpperCase().replace(/_/g, ' ')}
                    </div>
                  </div>

                  {/* Expanded Details */}
                  <AnimatePresence>
                    {expandedFiles.has(file.id) && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="border-t border-border overflow-hidden"
                      >
                        <div className="p-4 space-y-4">
                          {/* Phase Progress */}
                          <div className="space-y-3">
                            {[
                              { num: 1, label: 'Splitting & Metadata Extraction', key: 'phase1' },
                              { num: 2, label: 'OCR & Parsing', key: 'phase2' },
                              { num: 3, label: 'Embedding & Indexing', key: 'phase3' },
                            ].map(({ num, label, key }) => {
                              const phase = file.progress[key as keyof typeof file.progress];
                              return (
                                <div key={key} className="flex items-center gap-3">
                                  {getStatusIcon(phase.status)}
                                  <div className="flex-1">
                                    <div className="text-sm font-medium">Phase {num}: {label}</div>
                                    {phase.message && (
                                      <div className="text-xs text-muted-foreground">{phase.message}</div>
                                    )}
                                  </div>
                                </div>
                              );
                            })}
                          </div>

                          {/* Logs */}
                          {file.logs.length > 0 && (
                            <div className="bg-input/50 rounded-lg p-3 border border-border">
                              <div className="text-xs font-medium text-muted-foreground mb-2">Processing Logs</div>
                              <div className="space-y-1 max-h-40 overflow-y-auto custom-scrollbar">
                                {file.logs.map((log, i) => (
                                  <div key={i} className="text-xs font-mono text-foreground/80">{log}</div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Pipeline Architecture Info */}
        {files.length === 0 && (
          <div className="bg-gradient-to-br from-primary/5 to-accent/5 border border-primary/20 rounded-xl p-8">
            <h2 className="text-xl font-semibold mb-4">Pipeline Architecture</h2>
            <div className="grid md:grid-cols-3 gap-6">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center">
                    <FileText className="w-4 h-4 text-primary" />
                  </div>
                  <h3 className="font-semibold">Phase 1: Splitting</h3>
                </div>
                <p className="text-sm text-muted-foreground">
                  Intelligently splits large PDFs based on size and page limits, extracts metadata using Gemini AI
                </p>
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center">
                    <Upload className="w-4 h-4 text-primary" />
                  </div>
                  <h3 className="font-semibold">Phase 2: OCR</h3>
                </div>
                <p className="text-sm text-muted-foreground">
                  Uses Mistral AI OCR for text extraction, optional translation, and creates optimal-sized chunks
                </p>
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center">
                    <Database className="w-4 h-4 text-primary" />
                  </div>
                  <h3 className="font-semibold">Phase 3: Embedding</h3>
                </div>
                <p className="text-sm text-muted-foreground">
                  Generates hybrid embeddings (dense + sparse) and indexes in Qdrant for optimal retrieval
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
