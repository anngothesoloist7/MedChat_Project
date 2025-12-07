import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  UploadCloud, AlertCircle, Check, Loader2, FileText, ArrowRight, Link as LinkIcon 
} from 'lucide-react';
import { PipelineState, LogMessage } from './types';
import { StepIndicator } from './StepIndicator';
import { useSettings } from '@/context/SettingsContext';

interface RagIngestionProps {
    onComplete: (filename: string) => void;
}

export const RagIngestion: React.FC<RagIngestionProps> = ({ onComplete }) => {
    const { t } = useSettings();
    const [state, setState] = useState<PipelineState>('idle');
    const [filename, setFilename] = useState('');
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [selectedUrl, setSelectedUrl] = useState<string | null>(null);
    const [logs, setLogs] = useState<LogMessage | null>(null);
    const [socket, setSocket] = useState<WebSocket | null>(null);
    const [physicalFilename, setPhysicalFilename] = useState<string | null>(null);
    const [fileStats, setFileStats] = useState<{size: string, pages: number, exists: boolean} | null>(null);

    const WS_URL = "ws://localhost:8000/ws/pipeline";
    const API_PROCESS = "http://localhost:8000/process";
    const API_FILES = "http://localhost:8000/files";

    useEffect(() => {
        return () => {
            socket?.close();
        };
    }, [socket]);

    const connectWebSocket = () => {
        if (socket) socket.close();
        const ws = new WebSocket(WS_URL);
        ws.onopen = () => console.log("WS Connected");
        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                setLogs(prev => ({ ...prev, ...data }));
                
                // Only mark as fully completed if it's the final step or a special completion message
                if (data.status === 'completed' && (data.step === 4 || data.message === "Pipeline Finished")) {
                    setState('completed');
                    setTimeout(() => {
                        ws.close();
                        setSocket(null);
                        onComplete(filename);
                    }, 1000);
                } else if (data.status === 'error') {
                    // Show error state with message
                    console.error("Pipeline Error:", data.message);
                    setState('error');
                    setLogs(prev => ({ ...prev, step: 0, message: data.message })); // Ensure message is set
                }
            } catch (e) {
                console.error("WS Parse Error", e);
            }
        };
        ws.onerror = (e) => console.error("WS Error", e);
        setSocket(ws);
    };

    const checkFile = async (formData: FormData, file: File | null = null, url: string | null = null) => {
        setState('checking');
        try {
            const response = await fetch(API_PROCESS, { method: 'POST', body: formData });
            if (!response.ok) {
                const text = await response.text();
                throw new Error(`API Error ${response.status}: ${text}`);
            }
            
            const data = await response.json();
            if (data.results?.[0]) {
                const res = data.results[0];
                const stats = res.stats || { size: 0, pages: 0 };
                const sizeMB = (stats.size / (1024 * 1024)).toFixed(2);
                
                setFilename(res.display_name || res.filename || filename);
                if (res.filename) setPhysicalFilename(res.filename);
                
                setFileStats({ size: sizeMB + " MB", pages: stats.pages, exists: res.exists });
                setState('confirming');
            } else {
                 startPipeline(false, file, url);
            }
        } catch (e) {
            console.error("Check failed", e);
            startPipeline(false, file, url);
        }
    };

    const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        setFilename(file.name);
        setSelectedFile(file);
        setSelectedUrl(null);
        setPhysicalFilename(null);
        
        const formData = new FormData();
        formData.append('file', file);
        formData.append('check_only', 'true');
        checkFile(formData, file, null);
    };

    const handleUrlSubmit = (url: string) => {
        if (!url.trim()) return;
        setFilename(url);
        setSelectedUrl(url);
        setSelectedFile(null);
        setPhysicalFilename(null);

        const formData = new FormData();
        formData.append('url', url);
        formData.append('check_only', 'true');
        checkFile(formData, null, url);
    };

    const startPipeline = async (overwrite: boolean, file: File | null = selectedFile, url: string | null = selectedUrl) => {
        setState('processing');
        connectWebSocket();
        
        const formData = new FormData();
        if (file) formData.append('file', file);
        if (url) formData.append('url', url);
        formData.append('overwrite', overwrite.toString());
        formData.append('p1', 'true');
        formData.append('p2', 'true');
        formData.append('p3', 'true');
        // clean is true by default now in api

        try {
            await fetch(API_PROCESS, { method: 'POST', body: formData });
        } catch (e) {
            console.error("Start pipeline failed", e);
        }
    };

    const reset = async () => {
        if (physicalFilename) {
            try {
                // Delete the physical file from raw folder if user cancels
                console.log("Deleting raw file:", physicalFilename);
                await fetch(`${API_FILES}/${physicalFilename}`, { method: 'DELETE' });
            } catch (e) {
                console.error("Failed to delete raw file:", e);
            }
        }
        
        setState('idle');
        setFilename('');
        setLogs(null);
        setSelectedFile(null);
        setSelectedUrl(null);
        setFileStats(null);
        setPhysicalFilename(null);
    };

    return (
        <motion.div 
             initial={{ opacity: 0, y: 20 }}
             animate={{ opacity: 1, y: 0 }}
             transition={{ duration: 0.5, delay: 0.2 }}
             className="relative min-h-[200px] flex flex-col items-center justify-center w-full max-w-4xl mx-auto"
        >
            <AnimatePresence mode='wait'>
                {state === 'idle' && (
                    <motion.div
                        key="idle"
                        initial={{ opacity: 0, scale: 0.98 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.98 }}
                        className="w-full flex flex-col md:flex-row items-center gap-6 relative z-10"
                    >
                         {/* Upload PDF */}
                         <label className="flex-1 flex flex-col items-center justify-center w-full h-44 border border-dashed border-border/70 rounded-2xl cursor-pointer hover:bg-secondary/20 hover:border-accent/50 transition-all duration-300 group bg-background/20">
                            <div className="p-4 rounded-full bg-secondary/50 mb-3 group-hover:scale-110 transition-transform group-hover:bg-accent group-hover:text-accent-foreground">
                                <UploadCloud className="w-7 h-7 transition-colors" />
                            </div>
                            <p className="text-sm font-medium">{t('rag.upload_pdf')}</p>
                            <span className="text-xs text-muted-foreground mt-1">{t('rag.drag_drop')}</span>
                            <input type="file" accept=".pdf" className="hidden" onChange={handleFileUpload} />
                         </label>
                         
                         {/* OR Divider */}
                         <div className="flex md:flex-col items-center gap-2 text-muted-foreground/50">
                            <div className="w-8 md:w-px h-px md:h-8 bg-border/50" />
                            <span className="text-xs font-medium uppercase tracking-wider">{t('rag.or')}</span>
                            <div className="w-8 md:w-px h-px md:h-8 bg-border/50" />
                         </div>
                         
                         {/* URL Input */}
                         <div className="flex-1 flex flex-col items-center justify-center w-full h-44 border border-dashed border-border/70 rounded-2xl p-6 bg-background/20">
                            <div className="w-full max-w-xs">
                                <div className="relative">
                                    <LinkIcon size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
                                    <input 
                                        type="text" 
                                        placeholder={t('rag.paste_url')} 
                                        className="w-full bg-secondary/30 border border-border/50 rounded-xl pl-10 pr-10 py-2.5 text-sm focus:ring-1 focus:ring-accent outline-none transition-shadow"
                                        onKeyDown={(e) => { if(e.key==='Enter') handleUrlSubmit(e.currentTarget.value) }}
                                    />
                                    <button 
                                        className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground p-1.5 hover:bg-muted/50 rounded-lg transition-colors"
                                        onClick={(e) => {
                                            const input = e.currentTarget.parentElement?.querySelector('input');
                                            if (input) handleUrlSubmit(input.value);
                                        }}
                                    >
                                        <ArrowRight size={14} />
                                    </button>
                                </div>
                                <p className="text-xs text-center text-muted-foreground mt-3">{t('rag.import_web')}</p>
                            </div>
                         </div>
                    </motion.div>
                )}

                {state === 'checking' && (
                    <motion.div key="checking" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center">
                        <div className="relative">
                            <div className="absolute inset-0 bg-accent/20 blur-xl rounded-full" />
                            <div className="flex items-center gap-3 bg-secondary/30 px-6 py-3 rounded-full border border-border/50">
                                <Loader2 className="w-5 h-5 animate-spin text-accent" />
                                <span className="text-sm font-medium text-foreground">{t('rag.verifying')}</span>
                            </div>
                        </div>
                    </motion.div>
                )}

                {state === 'confirming' && (
                    <motion.div key="confirming" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="text-center w-full max-w-md">
                        <div className="bg-secondary/20 border border-border/50 rounded-2xl p-6 backdrop-blur-sm">
                            <div className="flex items-center gap-4 mb-6">
                                <div className="p-3 bg-accent/10 rounded-xl">
                                    <FileText className="w-8 h-8 text-accent" />
                                </div>
                                <div className="text-left flex-1 min-w-0">
                                    <h3 className="font-medium text-foreground truncate" title={filename}>{filename}</h3>
                                    <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1">
                                        <span className="flex items-center gap-1">
                                            <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span> 
                                            {fileStats?.size}
                                        </span>
                                        <span className="flex items-center gap-1">
                                             <span className="w-1.5 h-1.5 rounded-full bg-purple-500"></span>
                                             {fileStats?.pages} Pages
                                        </span>
                                    </div>
                                </div>
                            </div>
                            
                            {fileStats?.exists && (
                                <div className="mb-6 flex items-center gap-2 text-amber-500 bg-amber-500/10 px-3 py-2 rounded-lg text-sm">
                                    <AlertCircle size={16} />
                                    <span>{t('rag.file_exists')}</span>
                                </div>
                            )}

                            <div className="flex gap-3">
                                <button onClick={reset} className="flex-1 py-2.5 rounded-xl text-sm font-medium hover:bg-secondary border border-transparent hover:border-border transition-all">
                                    {t('rag.cancel')}
                                </button>
                                <button 
                                    onClick={() => startPipeline(fileStats?.exists || false)} 
                                    className="flex-1 py-2.5 bg-accent text-accent-foreground rounded-xl text-sm font-medium hover:brightness-110 shadow-lg shadow-accent/20 flex items-center justify-center gap-2"
                                >
                                    {fileStats?.exists ? t('rag.overwrite') : t('rag.start_processing')} <ArrowRight size={14} />
                                </button>
                            </div>
                        </div>
                    </motion.div>
                )}

                {state === 'processing' && (
                    <motion.div key="processing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="w-full max-w-md">
                         <div className="flex items-center gap-3 mb-8 border-b border-border/50 pb-4">
                            <FileText className="w-4 h-4 text-accent" />
                            <span className="text-sm font-medium truncate text-foreground/90">{filename}</span>
                         </div>
                         <div className="space-y-6 relative pl-3">
                            <div className="absolute left-[21px] top-2 bottom-4 w-[1px] bg-border/50" />
                            <StepIndicator step={1} currentStep={logs?.step || 1} label={t('rag.step_1')} />
                            <StepIndicator step={2} currentStep={logs?.step || 1} label={t('rag.step_2')} />
                            <StepIndicator step={3} currentStep={logs?.step || 1} label={t('rag.step_3')} />
                         </div>
                         <div className="mt-8 p-3 bg-secondary/30 rounded-lg border border-border/30 h-10 flex items-center overflow-hidden">
                            <p className="text-xs font-mono text-muted-foreground/80 truncate w-full">
                                &gt; {logs?.message || t('rag.initializing')}
                            </p>
                         </div>
                    </motion.div>
                )}

                {state === 'error' && (
                    <motion.div key="error" initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="flex flex-col items-center text-center max-w-lg">
                        <div className="w-20 h-20 bg-red-500/10 text-red-500 rounded-full flex items-center justify-center mb-6 border border-red-500/20 shadow-[0_0_30px_-5px_rgba(239,68,68,0.3)]">
                            <AlertCircle size={40} />
                        </div>
                        <h3 className="text-2xl font-medium mb-2 text-foreground">{t('rag.error_title')}</h3>
                        <div className="bg-red-500/5 border border-red-500/10 rounded-xl p-4 mb-8 w-full">
                            <p className="text-sm text-red-400 break-words font-mono">
                                {logs?.message || t('rag.unknown_error')}
                            </p>
                        </div>
                        <button onClick={reset} className="px-8 py-3 rounded-full bg-secondary hover:bg-secondary/80 text-foreground text-sm font-medium transition-colors border border-border">
                            {t('rag.try_again')}
                        </button>
                    </motion.div>
                )}

                {state === 'completed' && (
                    <motion.div key="completed" initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="flex flex-col items-center text-center">
                        <div className="w-20 h-20 bg-green-500/10 text-green-500 rounded-full flex items-center justify-center mb-6 border border-green-500/20 shadow-[0_0_30px_-5px_rgba(34,197,94,0.3)]">
                            <Check size={40} />
                        </div>
                        <h3 className="text-2xl font-medium mb-2 text-foreground">{t('rag.ingestion_complete')}</h3>
                        <p className="text-sm text-muted-foreground mb-8 max-w-xs">
                            {t('rag.ingestion_desc')}
                        </p>
                        <button onClick={reset} className="px-8 py-3 rounded-full bg-secondary hover:bg-secondary/80 text-foreground text-sm font-medium transition-colors border border-border">
                            {t('rag.process_another')}
                        </button>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
}
