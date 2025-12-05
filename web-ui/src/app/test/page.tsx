"use client";
import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { UploadCloud, AlertCircle, Check, Loader2, FileText, ArrowRight, Sparkles, LayoutGrid, BarChart3, PieChart, Database, AlignLeft, GripVertical, Clock, Zap, Search, Play, Code2, Settings2, Monitor, ChevronDown, ZoomIn, ZoomOut, Link as LinkIcon } from 'lucide-react';

type PipelineState = 'idle' | 'checking' | 'confirming' | 'processing' | 'completed';


interface Book {
    id: string;
    title: string;
    author: string;
    year: string;
    keywords: string[];
    stats?: {
        qdrantPoints: number;
        avgChunkLength: number;
    }
}

// Mock Data moved up or accessible
const INITIAL_BOOKS: Book[] = [
    {
        id: '1',
        title: "Pathophysiology of Disease: An Introduction to Clinical Medicine",
        author: "Gary D. Hammer",
        year: "2019",
        keywords: ["Disease", "Symptom"],
        stats: { qdrantPoints: 12450, avgChunkLength: 850 }
    },
    {
        id: '2',
        title: "Harrison's Principles of Internal Medicine",
        author: "J. Larry Jameson",
        year: "2022",
        keywords: ["Disease", "Treatment", "Symptom"],
        stats: { qdrantPoints: 28900, avgChunkLength: 920 }
    },
    {
        id: '3',
        title: "Medical Physiology",
        author: "Walter F. Boron",
        year: "2016",
        keywords: ["Lab-Test", "Imaging"],
        stats: { qdrantPoints: 15600, avgChunkLength: 780 }
    },
    {
        id: '4',
        title: "Robbins & Cotran Pathologic Basis of Disease",
        author: "Vinay Kumar",
        year: "2020",
        keywords: ["Disease", "Lab-Test"],
        stats: { qdrantPoints: 18230, avgChunkLength: 810 }
    },
    {
        id: '5',
        title: "Guyton and Hall Textbook of Medical Physiology",
        author: "John E. Hall",
        year: "2021",
        keywords: ["Imaging", "Lab-Test"],
        stats: { qdrantPoints: 14500, avgChunkLength: 760 }
    },
    {
        id: '6',
        title: "Basic and Clinical Pharmacology",
        author: "Bertram G. Katzung",
        year: "2018",
        keywords: ["Drug", "Treatment"],
        stats: { qdrantPoints: 11200, avgChunkLength: 890 }
    },
    {
        id: '7',
        title: "Current Medical Diagnosis and Treatment",
        author: "Maxine A. Papadakis",
        year: "2024",
        keywords: ["Disease", "Treatment"],
        stats: { qdrantPoints: 9800, avgChunkLength: 840 }
    },
    {
        id: '8',
        title: "Nelson Textbook of Pediatrics",
        author: "Robert M. Kliegman",
        year: "2019",
        keywords: ["Disease", "Symptom", "Drug"],
        stats: { qdrantPoints: 21000, avgChunkLength: 880 }
    }
];

export default function GeminiPipeline() {
  const [state, setState] = useState<PipelineState>('idle');
  const [filename, setFilename] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedUrl, setSelectedUrl] = useState<string | null>(null);
  const [logs, setLogs] = useState<{ step: number, message: string } | null>(null);
  const [viewMode, setViewMode] = useState<'list' | 'chart'>('list');
  const [expandedBook, setExpandedBook] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [books, setBooks] = useState<Book[]>(INITIAL_BOOKS);
  const [vizFilter, setVizFilter] = useState('Disease');
  const [zoomLevel, setZoomLevel] = useState(1);
  const [selectedAlgo, setSelectedAlgo] = useState('PCA');
  const [selectedPoint, setSelectedPoint] = useState<{ id: number, x: number, y: number } | null>(null);

  const [vizLimit, setVizLimit] = useState(100);

  // Generate stable random points
  const randomPoints = React.useMemo(() => {
    return Array.from({ length: vizLimit }).map((_, i) => ({
      id: i,
      x: Math.random() * 90 + 5, // Slightly wider spread
      y: Math.random() * 90 + 5
    }));
  }, [vizLimit]);

  const uniqueKeywords = Array.from(new Set(books.flatMap(b => b.keywords)));
  
  // WebSocket ref
  const socketRef = useRef<WebSocket | null>(null);

  const connectWebSocket = () => {
    if (socketRef.current) socketRef.current.close();
    // Assuming port 8000 for backend based on previous context
    const socket = new WebSocket("ws://localhost:8000/ws/pipeline");
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setLogs(data);
      if (data.status === 'completed') {
        setState('completed');
        // Add new book to list
        const newBook: Book = {
            id: Date.now().toString(),
            title: filename.replace('.pdf', ''),
            author: "Uploaded User",
            year: new Date().getFullYear().toString(),
            keywords: ["New", "Processing"],
            stats: {
                qdrantPoints: Math.floor(Math.random() * 5000) + 1000,
                avgChunkLength: Math.floor(Math.random() * 500) + 500
            }
        };
        setBooks(prev => [newBook, ...prev]);
      }
    };
    socketRef.current = socket;
  };

  // 1. Upload & Check (FILE)
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setState('checking');
    setFilename(file.name);
    setSelectedFile(file);
    setSelectedUrl(null); // Clear URL if file selected

    const formData = new FormData();
    formData.append('file', file);
    formData.append('check_only', 'true');

    try {
      // Use real /process endpoint for checking
      const res = await fetch('http://localhost:8000/process', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      
      // Data format: { status: "checked", results: [{ filename, exists, ... }] }
      if (data.results && data.results.length > 0) {
          const result = data.results[0];
          // Update filename if backend normalized it differently (optional for files)
          
          if (result.exists) {
            setState('confirming');
          } else {
            startPipeline(file.name, false, file);
          }
      }
    } catch (err) {
      console.error(err);
      setState('idle');
    }
  };

  // 2. Start Pipeline
  const startPipeline = async (name: string, overwrite: boolean, fileObject?: File, urlString?: string) => {
    setState('processing');
    connectWebSocket();
    
    // Resolve source
    const fileToUpload = fileObject || selectedFile;
    const urlToProcess = urlString || selectedUrl;

    if (fileToUpload || urlToProcess) {
        const formData = new FormData();
        if (fileToUpload) formData.append('file', fileToUpload);
        if (urlToProcess) formData.append('url', urlToProcess);
        
        formData.append('overwrite', overwrite.toString());
        formData.append('p1', 'true');
        formData.append('p2', 'true');
        formData.append('p3', 'true');

        const res = await fetch('http://localhost:8000/process', {
            method: 'POST',
            body: formData,
        });

        if (res.ok) {
            const data = await res.json();
            if (data.files && data.files.length > 0) {
                setFilename(data.files[0]);
            }
        }
    } else {
        // Fallback or Error
        console.error("No file or URL to process");
    }
  };

  const handleUrlSubmit = async (url: string) => {
      if (!url.trim()) return;
      
      setState('checking');
      setFilename('Resolving Document...'); // Show checking state
      setSelectedUrl(url);
      setSelectedFile(null); // Clear file if URL selected

      const formData = new FormData();
      formData.append('url', url);
      formData.append('check_only', 'true');

      try {
        const res = await fetch('http://localhost:8000/process', {
            method: 'POST',
            body: formData,
        });
        const data = await res.json();
        
        if (data.results && data.results.length > 0) {
            const result = data.results[0];
            setFilename(result.filename); // Set Real Name from Backend
            
            if (result.exists) {
                setState('confirming');
            } else {
                startPipeline(result.filename, false, undefined, url);
            }
        }
      } catch (err) {
        console.error("URL Check Failed", err);
        setFilename(url); // Revert to URL if check failed
        startPipeline(url, false, undefined, url); // Try processing anyway?
      }
  };

  return (
    <div className="min-h-screen flex flex-col items-center pt-20 pb-20 bg-background text-foreground font-sans selection:bg-accent selection:text-accent-foreground">
      <div className="w-full max-w-3xl p-8 relative">
        
        {/* Top Right Toggle */}
        <div className="absolute top-8 right-8 flex bg-secondary/50 p-1 rounded-lg border border-border/50 backdrop-blur-sm z-10">
            <button 
                onClick={() => setViewMode('list')}
                className={`p-2 rounded-md transition-all ${viewMode === 'list' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground'}`}
                title="List View"
            >
                <LayoutGrid size={16} />
            </button>
            <button 
                onClick={() => setViewMode('chart')}
                className={`p-2 rounded-md transition-all ${viewMode === 'chart' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground'}`}
                title="Insight Chart"
            >
                <BarChart3 size={16} />
            </button>
        </div>
        
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

        <div className="relative min-h-[220px] flex flex-col items-center justify-center bg-secondary/30 border border-border rounded-2xl p-4 backdrop-blur-sm">
          <AnimatePresence mode='wait'>
            
            {/* STATE: IDLE */}
            {state === 'idle' && (
              <motion.div
                key="idle"
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.98 }}
                className="w-full grid grid-cols-1 md:grid-cols-2 gap-4"
              >
                <label className="flex flex-col items-center justify-center w-full h-60 border border-dashed border-muted-foreground/30 rounded-xl cursor-pointer hover:bg-secondary/50 transition-all duration-300 group bg-background/50">
                  <div className="flex flex-col items-center justify-center">
                    <div className="p-4 rounded-full bg-secondary mb-4 group-hover:scale-110 transition-transform duration-300 shadow-sm">
                        <UploadCloud className="w-6 h-6 text-accent-foreground" strokeWidth={1.5} />
                    </div>
                    <p className="text-sm text-foreground/80 font-medium">Upload Document</p>
                    <p className="text-xs text-muted-foreground mt-1">PDF files supported</p>
                  </div>
                  <input type="file" accept=".pdf" className="hidden" onChange={handleFileUpload} />
                </label>

                 <div className="flex flex-col items-center justify-center w-full h-60 border border-dashed border-muted-foreground/30 rounded-xl p-6 bg-secondary/5 hover:bg-secondary/20 transition-all duration-300">
                    <div className="flex flex-col items-center justify-center w-full space-y-4">
                        <div className="p-3 rounded-full bg-secondary shadow-sm">
                            <LinkIcon className="w-5 h-5 text-accent-foreground" />
                        </div>
                        <div className="w-full relative">
                            <input 
                                type="text" 
                                placeholder="Paste PDF URL..." 
                                className="w-full bg-background border border-border rounded-lg pl-3 pr-8 py-2 text-sm focus:ring-1 focus:ring-accent outline-none transition-shadow"
                                onKeyDown={(e) => { 
                                    if (e.key === 'Enter') {
                                        handleUrlSubmit(e.currentTarget.value);
                                        e.currentTarget.value = '';
                                    }
                                }}
                            />
                            <button className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-muted-foreground hover:text-foreground transition-colors">
                                <ArrowRight size={14} />
                            </button>
                        </div>
                        <p className="text-[10px] text-muted-foreground text-center px-4">
                            Import directly from a public URL or Google Drive link
                        </p>
                    </div>
                </div>
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
                    <div className="absolute left-[17.5px] top-2 bottom-2 w-[1px] bg-border/50" />
                    
                    {[1, 2, 3].map((stepIdx) => {
                        const currentStep = logs?.step || 0;
                        const isActive = currentStep === stepIdx;
                        const isDone = currentStep > stepIdx;
                        
                        return (
                            <div key={stepIdx} className="relative flex items-center gap-4">
                                {isActive && (
                                    <motion.div
                                        layoutId="active-step-glow"
                                        className="absolute left-[-4px] w-7 h-7 bg-accent/20 rounded-full blur-[2px]"
                                        initial={{ scale: 0.8, opacity: 0.5 }}
                                        animate={{ scale: [1, 1.2, 1], opacity: [0.5, 0.2, 0.5] }}
                                        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                                    />
                                )}
                                <motion.div 
                                    className={`w-5 h-5 rounded-full border flex items-center justify-center z-10 
                                        ${isActive ? 'border-accent-foreground bg-accent text-accent-foreground' : 
                                          isDone ? 'border-primary/50 bg-background text-primary' : 'border-border bg-background'}`}
                                    animate={{ scale: isActive ? 1.1 : 1 }}
                                    transition={{ type: "spring", stiffness: 300, damping: 20 }}
                                >
                                    {isDone && <Check size={10} />}
                                    {isActive && <Loader2 size={10} className="animate-spin" />}
                                </motion.div>
                                <div className={`${isActive ? 'opacity-100' : isDone ? 'opacity-60' : 'opacity-30'} transition-opacity flex flex-col`}>
                                    <div className="flex items-center gap-2">
                                        <p className="text-[10px] font-bold uppercase tracking-widest mb-0.5">Phase 0{stepIdx}</p>
                                        {isActive && (
                                            <span className="flex h-1.5 w-1.5 relative">
                                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-foreground opacity-75"></span>
                                                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-accent-foreground"></span>
                                            </span>
                                        )}
                                    </div>
                                    <p className="text-sm font-medium">
                                        {stepIdx === 1 ? 'Smart Splitting' : 
                                         stepIdx === 2 ? 'OCR & Chunking' : 
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
                    className="flex flex-col items-center text-center py-4 w-full"
                >
                    <div className="w-14 h-14 bg-green-500/10 text-green-400 rounded-full flex items-center justify-center mb-5 border border-green-500/20 shadow-[0_0_30px_-10px_rgba(74,222,128,0.3)]">
                        <Check size={28} />
                    </div>
                    <h3 className="text-lg font-medium text-foreground">Ingestion Complete</h3>
                    <p className="text-sm text-muted-foreground mt-2 mb-8 max-w-[200px]">
                        The document has been securely indexed.
                    </p>

                    {/* Ingestion Stats */}
                    <div className="grid grid-cols-2 gap-3 w-full max-w-sm mb-8">
                        <div className="bg-secondary/20 border border-border/50 rounded-xl p-4 flex flex-col items-start gap-1">
                            <div className="flex items-center gap-2 mb-1 text-muted-foreground">
                                <LayoutGrid size={14} />
                                <span className="text-[10px] uppercase font-bold tracking-wider">Total Chunks</span>
                            </div>
                            <span className="text-xl font-bold text-foreground">142</span>
                        </div>
                        <div className="bg-secondary/20 border border-border/50 rounded-xl p-4 flex flex-col items-start gap-1">
                            <div className="flex items-center gap-2 mb-1 text-muted-foreground">
                                <Database size={14} />
                                <span className="text-[10px] uppercase font-bold tracking-wider">Vectors Index</span>
                            </div>
                            <span className="text-xl font-bold text-foreground">142</span>
                        </div>
                         <div className="bg-secondary/20 border border-border/50 rounded-xl p-4 flex flex-col items-start gap-1">
                            <div className="flex items-center gap-2 mb-1 text-muted-foreground">
                                <Clock size={14} />
                                <span className="text-[10px] uppercase font-bold tracking-wider">Processing Time</span>
                            </div>
                            <span className="text-xl font-bold text-foreground">4.2s</span>
                        </div>
                        <div className="bg-secondary/20 border border-border/50 rounded-xl p-4 flex flex-col items-start gap-1">
                            <div className="flex items-center gap-2 mb-1 text-muted-foreground">
                                <Zap size={14} />
                                <span className="text-[10px] uppercase font-bold tracking-wider">AI Confidence</span>
                            </div>
                            <span className="text-xl font-bold text-foreground">98.5%</span>
                        </div>
                    </div>

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
        <div className="mt-8 mb-12 text-center">
            <p className="text-[10px] text-muted-foreground/50 font-mono">POWERED BY MEDCHAT RAG ENGINE</p>
        </div>

        {/* Existing Books List */}
        {viewMode === 'list' ? (
            <div className="w-full">
                <div className="flex flex-col gap-6 mb-6">
                    {/* Search Bar */}
                    <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <Search className="h-4 w-4 text-muted-foreground" />
                        </div>
                        <input
                            type="text"
                            placeholder="Search library..."
                            className="w-full pl-10 pr-4 py-2 rounded-xl bg-secondary/30 border border-border/50 focus:border-accent focus:ring-1 focus:ring-accent text-sm text-foreground outline-none transition-all placeholder:text-muted-foreground/70"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>

                    <div className="flex items-center gap-2 px-1">
                        <div className="h-4 w-1 bg-accent rounded-full" />
                        <h2 className="text-sm font-semibold text-foreground tracking-tight">Indexed Library</h2>
                    </div>
                </div>
                
                <div className="grid gap-4">
                    {books.filter(book => 
                        book.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
                        book.author.toLowerCase().includes(searchQuery.toLowerCase()) ||
                        book.keywords.some(k => k.toLowerCase().includes(searchQuery.toLowerCase()))
                    ).map((book, i) => (
                        <motion.div 
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.1 }}
                            key={book.id}
                            onClick={() => setExpandedBook(expandedBook === book.id ? null : book.id)}
                            className={`group relative bg-secondary/20 border border-border/50 rounded-xl p-5 transition-all duration-300 cursor-pointer overflow-hidden
                                ${expandedBook === book.id ? 'bg-secondary/40 ring-1 ring-accent/50' : 'hover:bg-secondary/40 hover:border-accent/30'}
                            `}
                        >
                            <div className="flex justify-between items-start gap-4">
                                <div>
                                    <h3 className="text-base font-medium text-foreground/90 group-hover:text-accent-foreground transition-colors mb-1">
                                        {book.title}
                                    </h3>
                                    <div className="text-xs text-muted-foreground flex items-center gap-2 mb-3">
                                        <span>{book.author}</span>
                                        <span className="w-1 h-1 bg-border rounded-full" />
                                        <span>{book.year}</span>
                                    </div>
                                </div>
                                <div className={`p-2 rounded-full transition-colors border border-border/50 ${expandedBook === book.id ? 'bg-accent text-accent-foreground' : 'bg-background/50 text-muted-foreground group-hover:text-accent-foreground'}`}>
                                    {expandedBook === book.id ? <Database size={16} /> : <FileText size={16} />}
                                </div>
                            </div>
                            
                            <div className="flex flex-wrap gap-2 mt-2">
                                {book.keywords.map(tag => (
                                    <span key={tag} className="text-[10px] px-2 py-1 rounded-md bg-background/50 border border-border/50 text-muted-foreground font-medium">
                                        #{tag}
                                    </span>
                                ))}
                            </div>

                            {/* Expanded Details */}
                            <AnimatePresence>
                                {expandedBook === book.id && (
                                    <motion.div
                                        initial={{ height: 0, opacity: 0, marginTop: 0 }}
                                        animate={{ height: 'auto', opacity: 1, marginTop: 16 }}
                                        exit={{ height: 0, opacity: 0, marginTop: 0 }}
                                        className="border-t border-border/30 pt-4"
                                    >
                                        <div className="grid grid-cols-2 gap-4">
                                            <div className="bg-background/40 rounded-lg p-3 flex flex-col gap-1 border border-border/30">
                                                <div className="flex items-center gap-2 text-muted-foreground">
                                                    <LayoutGrid size={12} />
                                                    <span className="text-[10px] uppercase tracking-wider font-semibold">Qdrant Points</span>
                                                </div>
                                                <span className="text-lg font-mono text-foreground">{book.stats?.qdrantPoints.toLocaleString()}</span>
                                            </div>
                                            <div className="bg-background/40 rounded-lg p-3 flex flex-col gap-1 border border-border/30">
                                                <div className="flex items-center gap-2 text-muted-foreground">
                                                    <AlignLeft size={12} />
                                                    <span className="text-[10px] uppercase tracking-wider font-semibold">Avg. Chunk Size</span>
                                                </div>
                                                <div className="flex items-baseline gap-1">
                                                    <span className="text-lg font-mono text-foreground">{book.stats?.avgChunkLength}</span>
                                                    <span className="text-[10px] text-muted-foreground">chars</span>
                                                </div>
                                            </div>
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </motion.div>
                    ))}
                </div>
            </div>
        ) : (
            <div className="w-full">
                 <div className="flex items-center gap-2 mb-6 px-1">
                    <div className="h-4 w-1 bg-accent rounded-full" />
                    <h2 className="text-sm font-semibold text-foreground tracking-tight">Collection Insights</h2>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                    {[
                        { label: 'Total Documents', value: '1,248', change: '+12%', icon: FileText },
                        { label: 'Vector Points', value: '8.4M', change: '+5.2%', icon: Sparkles },
                        { label: 'Storage Used', value: '4.2 GB', change: 'Stable', icon: PieChart },
                    ].map((stat, i) => (
                        <motion.div
                            key={stat.label}
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ delay: i * 0.1 }}
                            className="bg-secondary/20 border border-border/50 rounded-xl p-5 flex flex-col items-start gap-3"
                        >
                             <div className="p-2 bg-background/50 rounded-lg text-accent-foreground mb-1">
                                <stat.icon size={18} />
                             </div>
                             <div>
                                <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">{stat.label}</p>
                                <p className="text-2xl font-semibold text-foreground mt-1">{stat.value}</p>
                             </div>
                             <div className="text-[10px] px-2 py-0.5 rounded-full bg-accent/10 text-accent-foreground font-medium">
                                {stat.change}
                             </div>
                        </motion.div>
                    ))}
                </div>

                {/* Mock Visual Chart */}
                <motion.div 
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    className="p-6 bg-secondary/10 border border-border/50 rounded-2xl"
                 >
                     <div className="flex items-center justify-between mb-8">
                        <div>
                            <h3 className="text-base font-medium text-foreground">Topic Distribution</h3>
                            <p className="text-xs text-muted-foreground">Categorization of indexed medical knowledge</p>
                        </div>
                     </div>
                     
                     <div className="flex items-end gap-4 h-64 w-full px-2 pb-2">
                        {[
                            { label: 'Disease', value: 78, color: 'bg-rose-500' },
                            { label: 'Symptom', value: 62, color: 'bg-amber-500' },
                            { label: 'Treatment', value: 85, color: 'bg-emerald-500' },
                            { label: 'Drug', value: 45, color: 'bg-blue-500' },
                            { label: 'Lab-Test', value: 30, color: 'bg-purple-500' },
                            { label: 'Imaging', value: 55, color: 'bg-cyan-500' },
                        ].map((item, i) => (
                            <div key={item.label} className="flex-1 flex flex-col justify-end group h-full">
                                <div className="relative flex-1 flex items-end justify-center w-full bg-secondary/20 rounded-t-lg overflow-hidden">
                                     {/* Bar */}
                                    <motion.div 
                                        initial={{ height: 0 }}
                                        animate={{ height: `${item.value}%` }}
                                        transition={{ duration: 0.8, delay: i * 0.1, ease: "easeOut" }}
                                        className={`w-full opacity-80 group-hover:opacity-100 transition-opacity ${item.color}`}
                                    />
                                    
                                     {/* Tooltip value */}
                                    <div className="absolute bottom-2 font-bold text-white text-xs z-10 opacity-0 group-hover:opacity-100 transition-all duration-300 transform translate-y-2 group-hover:translate-y-0">
                                        {item.value}%
                                    </div>
                                </div>
                                <div className="h-8 flex items-center justify-center border-t border-border/30 mt-2">
                                     <span className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider text-center leading-tight">
                                        {item.label}
                                     </span>
                                </div>
                            </div>
                        ))}
                     </div>
                 </motion.div>

                {/* Language Distribution Chart */}
                <motion.div 
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4 }}
                    className="mt-6 p-6 bg-secondary/10 border border-border/50 rounded-2xl"
                >
                    <div className="mb-6">
                        <h3 className="text-base font-medium text-foreground">Language Distribution</h3>
                        <p className="text-xs text-muted-foreground">Source language of indexed documents</p>
                    </div>

                    <div className="relative h-12 w-full bg-secondary/30 rounded-full overflow-hidden flex">
                        <motion.div 
                            initial={{ width: 0 }}
                            animate={{ width: "85%" }}
                            transition={{ duration: 1, delay: 0.5, ease: "circOut" }}
                            className="h-full bg-blue-500/80 flex items-center justify-center relative group"
                        >
                            <span className="text-[10px] font-bold text-white opacity-0 group-hover:opacity-100 transition-opacity">85%</span>
                        </motion.div>
                        <motion.div 
                            initial={{ width: 0 }}
                            animate={{ width: "15%" }}
                            transition={{ duration: 1, delay: 0.5, ease: "circOut" }}
                            className="h-full bg-red-500/80 flex items-center justify-center relative group"
                        >
                             <span className="text-[10px] font-bold text-white opacity-0 group-hover:opacity-100 transition-opacity">15%</span>
                        </motion.div>
                    </div>

                    <div className="flex justify-between mt-3 px-1">
                        <div className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded-full bg-blue-500/80" />
                            <span className="text-xs text-foreground font-medium">English</span>
                            <span className="text-[10px] text-muted-foreground">(1,060 docs)</span>
                        </div>
                        <div className="flex items-center gap-2">
                             <span className="text-[10px] text-muted-foreground">(188 docs)</span>
                            <span className="text-xs text-foreground font-medium">Vietnamese</span>
                            <div className="w-3 h-3 rounded-full bg-red-500/80" />
                        </div>
                    </div>
                </motion.div>

                {/* Vector Space Visualization (Qdrant Style) */}
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5 }}
                    className="mt-6 border border-border/50 rounded-xl overflow-hidden bg-background/50 backdrop-blur-md shadow-sm"
                >
                    {/* Toolbar */}
                    <div className="flex border-b border-border/30 bg-secondary/10">
                         <div className="px-4 py-3 border-r border-border/30 bg-secondary/30 flex items-center gap-2 text-foreground">
                            <Monitor size={14} className="text-accent-foreground" />
                            <span className="text-xs font-semibold">Visual Mode</span>
                         </div>
                         <div className="px-4 py-3 flex items-center gap-2 cursor-pointer hover:bg-secondary/20 transition-colors text-muted-foreground border-r border-border/30">
                            <Code2 size={14} />
                            <span className="text-xs">Filter Mode</span>
                         </div>
                         <div className="ml-auto px-4 py-3 flex items-center gap-3">
                             <div className="flex items-center gap-1.5 px-3 py-1.5 bg-green-500/10 text-green-500 rounded-md border border-green-500/20 cursor-pointer hover:bg-green-500/20 transition-colors shadow-[0_0_10px_-3px_rgba(34,197,94,0.3)]">
                                <Play size={10} fill="currentColor" />
                                <span className="text-[10px] font-bold uppercase tracking-wide">Run</span>
                             </div>
                             <div className="p-1.5 hover:bg-secondary/30 rounded-md text-muted-foreground cursor-pointer">
                                <Settings2 size={14} />
                             </div>
                         </div>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-3 h-[450px]">
                        {/* Visualizer Canvas (Mock) */}
                        <div className="lg:col-span-2 relative bg-[#09090b] overflow-hidden group flex items-center justify-center">
                            {/* Zoom Controls */}
                            <div className="absolute top-4 right-4 z-20 flex flex-col gap-2">
                                <button 
                                    onClick={() => setZoomLevel(prev => Math.min(prev + 0.2, 3))}
                                    className="p-2 bg-secondary/20 hover:bg-secondary/40 text-foreground rounded-lg backdrop-blur-sm border border-border/20 transition-colors"
                                >
                                    <ZoomIn size={16} />
                                </button>
                                <button 
                                    onClick={() => setZoomLevel(prev => Math.max(prev - 0.2, 0.5))}
                                    className="p-2 bg-secondary/20 hover:bg-secondary/40 text-foreground rounded-lg backdrop-blur-sm border border-border/20 transition-colors"
                                >
                                    <ZoomOut size={16} />
                                </button>
                            </div>

                            {/* Scale Container for Grid & Points */}
                            <motion.div 
                                className="w-full h-full relative"
                                animate={{ scale: zoomLevel }}
                                transition={{ type: "spring", stiffness: 300, damping: 30 }}
                            >
                                 {/* Infinite Grid Simulation */}
                                <div 
                                    className="absolute inset-[-100%] opacity-[0.07]"
                                    style={{ 
                                        backgroundImage: 'linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)',
                                        backgroundSize: '40px 40px'
                                    }} 
                                />
                                
                                {/* Points Container */}
                                <div className="absolute inset-0">
                                    {randomPoints.map((point) => (
                                        <div
                                            key={point.id}
                                            onMouseEnter={() => setSelectedPoint(point)}
                                            onMouseLeave={() => setSelectedPoint(null)}
                                            className="absolute rounded-full cursor-pointer hover:scale-150 transition-transform hover:z-30"
                                            style={{
                                                left: `${point.x}%`,
                                                top: `${point.y}%`,
                                                width: '4px', // Invisible hit area is actually larger due to visual trickery or just use small points
                                                height: '4px',
                                                backgroundColor: '#3b82f6',
                                                opacity: 0.8,
                                                padding: '2px', // Increase hit area slightly
                                                backgroundClip: 'content-box' 
                                            }}
                                        />
                                    ))}
                                    
                                     {/* Dynamic Highlighted Point (On Hover) */}
                                     {selectedPoint && (
                                         <motion.div 
                                            layoutId="highlighted-vector"
                                            initial={{ scale: 0.5, opacity: 0 }}
                                            animate={{ 
                                                scale: [1, 1.5, 1],
                                                opacity: 1,
                                                boxShadow: [
                                                    "0 0 0 0px rgba(96, 165, 250, 0)",
                                                    "0 0 0 4px rgba(96, 165, 250, 0.4)",
                                                    "0 0 0 8px rgba(96, 165, 250, 0)"
                                                ]
                                            }}
                                            transition={{ 
                                                duration: 1.5, 
                                                repeat: Infinity,
                                                ease: "easeInOut"
                                            }}
                                            className="absolute z-20 pointer-events-none"
                                            style={{
                                                left: `${selectedPoint.x}%`,
                                                top: `${selectedPoint.y}%`,
                                                width: '6px', 
                                                height: '6px',
                                                backgroundColor: '#3b82f6',
                                                borderRadius: '9999px',
                                                border: '1px solid rgba(255,255,255,0.8)',
                                                transform: 'translate(-1px, -1px)' // Center align visual adjustment since point is 4px and this is 6px
                                            }}
                                         />
                                     )}
                                </div>
                            </motion.div>
                            
                            <div className="absolute bottom-4 left-4 flex gap-4 text-[10px] font-mono">
                                <span className="text-[#3b82f6]">All Vectors</span>
                            </div>
                             <div className="absolute bottom-4 right-4 text-[10px] text-muted-foreground font-mono opacity-50">
                                Points: 1,248 | Algorithm: {selectedAlgo} | Zoom: {Math.round(zoomLevel * 100)}%
                            </div>
                        </div>

                        {/* Filter Panel (UI Mode) */}
                        <div className="border-l border-border/30 bg-secondary/5 flex flex-col">
                            <div className="px-4 py-3 border-b border-border/10 flex items-center justify-between">
                                <span className="text-xs font-semibold text-foreground">Visualization Settings</span>
                                <Settings2 size={12} className="text-muted-foreground" />
                            </div>
                            
                            <div className="p-5 flex flex-col gap-6">
                                <div className="space-y-3">
                                    <label className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
                                        Filter by Keyword
                                    </label>
                                    <div className="relative">
                                        <select 
                                            value={vizFilter}
                                            onChange={(e) => setVizFilter(e.target.value)}
                                            className="w-full bg-secondary/20 border border-border rounded-lg px-3 py-2 text-sm text-foreground appearance-none cursor-pointer hover:bg-secondary/30 transition-colors focus:ring-1 focus:ring-accent outline-none"
                                        >
                                            {uniqueKeywords.map(k => (
                                                <option key={k} value={k} style={{ backgroundColor: '#1a1a1a', color: '#e5e5e5' }}>{k}</option>
                                            ))}
                                        </select>
                                        <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
                                    </div>
                                    <p className="text-[10px] text-muted-foreground">
                                        Only vectors containing this keyword will be highlighted.
                                    </p>
                                </div>

                                <div className="space-y-3">
                                    <div className="flex justify-between items-center">
                                        <label className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
                                            Limit
                                        </label>
                                        <span className="text-xs font-mono text-accent">{vizLimit} Points</span>
                                    </div>
                                    <div className="w-full">
                                        <input 
                                            type="range" 
                                            min="1" 
                                            max="1000" 
                                            value={vizLimit} 
                                            onChange={(e) => setVizLimit(parseInt(e.target.value))}
                                            className="w-full h-1.5 bg-secondary/30 rounded-lg appearance-none cursor-pointer accent-accent"
                                        />
                                    </div>
                                </div>

                                <div className="space-y-3">
                                     <label className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
                                        Algorithm
                                    </label>
                                    <div className="grid grid-cols-3 gap-2">
                                        {['PCA', 't-SNE', 'UMAP'].map(algo => (
                                            <div 
                                                key={algo} 
                                                onClick={() => setSelectedAlgo(algo)}
                                                className={`text-center py-1.5 rounded-md text-[10px] font-medium border cursor-pointer transition-all ${selectedAlgo === algo ? 'bg-accent/10 border-accent text-accent' : 'bg-transparent border-border text-muted-foreground hover:bg-secondary/20'}`}
                                            >
                                                {algo}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </motion.div>
            </div>
        )}

      </div>
    </div>
  );
}




