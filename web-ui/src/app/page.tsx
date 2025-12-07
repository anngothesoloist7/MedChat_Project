'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Sidebar } from '@/components/layout/Sidebar';
import { MessageBubble, Message } from '@/components/chat/MessageBubble';
import { InputArea, InputAreaRef } from '@/components/chat/InputArea';
import { Menu, Sparkles, User } from 'lucide-react'; 
import axios from 'axios';
import { v4 as uuidv4 } from 'uuid';
import { clsx } from 'clsx';
import { createClient } from '@/utils/supabase/client';
import { useSettings } from '@/context/SettingsContext';
import { getDeviceId } from '@/utils/device';
import { motion, AnimatePresence } from 'framer-motion';

// Import New RAG Components
import { RagIngestion } from '@/components/knowledge-base/rag/RagIngestion';
import { RagLibrary } from '@/components/knowledge-base/rag/RagLibrary';
import { Book } from '@/components/knowledge-base/rag/types';
import { StartupLoader } from '@/components/layout/StartupLoader';

// Mock Data for Library (In real app, fetch from key-value store or DB)
// Mock Data removed. Using real API.

type EhrPhase = 'idle' | 'chatting'; 

function ThinkingText() {
  const { t } = useSettings();
  const [step, setStep] = useState(0);
  const steps = ['reasoning_1', 'reasoning_2', 'reasoning_3', 'reasoning_4'];

  useEffect(() => {
    const interval = setInterval(() => {
      setStep((prev) => (prev + 1) % steps.length);
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="text-sm font-medium bg-gradient-to-r from-blue-500 via-purple-500 to-red-500 text-transparent bg-clip-text animate-pulse transition-all duration-500">
      {t(steps[step])}
    </div>
  );
}

export default function Home() {
  const [showStartupLoader, setShowStartupLoader] = useState(true);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [activeTab, setActiveTab] = useState<'chat' | 'ehr'>('chat');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [ehrPhase, setEhrPhase] = useState<EhrPhase>('idle');
  const [sessionId, setSessionId] = useState(uuidv4()); 
  const [chatTitle, setChatTitle] = useState("New Chat");
  const [isSessionLoading, setIsSessionLoading] = useState(false);
  
  // Library State
  const [books, setBooks] = useState<Book[]>([]);
  const [libraryStats, setLibraryStats] = useState<any>(null);
  const [isLibraryLoading, setIsLibraryLoading] = useState(false);

  const supabase = createClient();
  const { t } = useSettings();

  const fetchLibrary = async () => {
     setIsLibraryLoading(true);
     const controller = new AbortController();
     const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 min timeout

     try {
         const res = await fetch('https://rag.botnow.online/library', { signal: controller.signal });
         const data = await res.json();
         if (data.books) {
             setBooks(data.books);
         }
         if (data.stats) {
             setLibraryStats(data.stats);
         }
     } catch (e: any) {
         if (e.name === 'AbortError') {
            console.warn("Library fetch timed out - Server might be busy processing large index.");
         } else if (e.message && e.message.includes('Failed to fetch')) {
             console.error("Could not connect to backend server. Is it running?");
         } else {
            console.error("Failed to fetch library", e);
         }
     } finally {
         clearTimeout(timeoutId);
         setIsLibraryLoading(false);
     }
  };

  useEffect(() => {
    if (activeTab === 'ehr') {
        fetchLibrary();
    }
  }, [activeTab]);

  useEffect(() => {
    if (window.innerWidth < 768) {
      setIsSidebarOpen(false);
    }
  }, []);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputAreaRef = useRef<InputAreaRef>(null);

  useEffect(() => {
    if (!isLoading) {
      setTimeout(() => {
        inputAreaRef.current?.focus();
      }, 100);
    }
  }, [isLoading]);

  const scrollToBottom = (behavior: ScrollBehavior = "smooth") => {
    messagesEndRef.current?.scrollIntoView({ behavior });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // --- Session Locking Heartbeat ---
  useEffect(() => {
    if (!sessionId) return;
    const deviceId = getDeviceId();
    const heartbeat = setInterval(async () => {
      try {
        await supabase.rpc('refresh_session_lock', { p_session_id: sessionId, p_device_id: deviceId });
      } catch (e) { /* Ignore */ }
    }, 30000);

    supabase.rpc('refresh_session_lock', { p_session_id: sessionId, p_device_id: deviceId }).then(({ error }) => {
      if (error) console.warn("Session lock init failed (ignoring)");
    });

    return () => {
      clearInterval(heartbeat);
      supabase.rpc('release_session_lock', { p_session_id: sessionId, p_device_id: deviceId });
    };
  }, [sessionId]);

  const addMessage = (role: 'user' | 'assistant', content: string, thinkingTime?: number, shouldAnimate: boolean = false) => {
    setMessages(prev => [...prev, {
      id: uuidv4(), role, content, timestamp: new Date(), thinkingTime, shouldAnimate
    }]);
  };

  const stripMarkdown = (text: string) => {
    return text.replace(/(\*\*|__)(.*?)\1/g, '$2').replace(/(\*|_)(.*?)\1/g, '$2').replace(/\[([^\]]+)\]\([^)]+\)/g, '$1').replace(/#{1,6}\s?/g, '').replace(/`{3}[\s\S]*?`{3}/g, '').replace(/`(.+?)`/g, '$1').replace(/^\s*>\s?/gm, '').trim();
  };

  // --- History Loading ---
  const handleLoadSession = async (id: string, type: 'chat' | 'ehr' = 'chat') => {
    setSessionId(id);
    setActiveTab(type); 
    setEhrPhase('chatting'); // Assume ready if loading history
    setMessages([]); 
    setIsSessionLoading(true);
    setChatTitle("Loading...");
    
    try {
      // Unified table
      const { data, error } = await supabase.from('chat_history').select('*').eq('session_id', id).order('created_at', { ascending: true });

      if (error) throw error;

      if (data && data.length > 0) {
        const loadedMessages: Message[] = data.map((row: any) => ({
            id: row.id.toString(),
            role: row.role as 'user' | 'assistant',
            content: row.content,
            timestamp: new Date(row.created_at),
            thinkingTime: row.thinking_time
        }));
        
        setMessages(loadedMessages);
        
        const firstUserMsg = loadedMessages.find(m => m.role === 'user');
        setChatTitle(firstUserMsg ? (stripMarkdown(firstUserMsg.content).substring(0, 40) + '...') : "Conversation");
      } else {
        setMessages([]);
        setChatTitle("New Chat");
      }
    } catch (err) {
      console.error("Failed to load session:", err);
      // addMessage('assistant', "⚠️ Failed to load conversation history."); 
      // Silent fail is better than showing error message on empty new sessions if the ID just doesn't exist
      setMessages([]);
      setChatTitle("New Chat");
    } finally {
      setIsSessionLoading(false);
    }
  };

  // --- RAG Callback ---
  const handleRagComplete = (filename: string) => {
      // Refresh library to show new book
      fetchLibrary();
  };

  // --- Chat ---
  const handleSendMessage = async (text: string) => {
    if (messages.length === 0) {
       const cleanTitle = stripMarkdown(text);
       setChatTitle(cleanTitle.length > 40 ? cleanTitle.substring(0, 40) + '...' : cleanTitle);
    }
    
    // Auto-switch to chatting phase if in EHR mode and sending a message
    if (activeTab === 'ehr' && ehrPhase !== 'chatting') {
        setEhrPhase('chatting');
    }

    addMessage('user', text);
    setIsLoading(true);
    const startTime = Date.now();

    try {
      let payload: any = { sessionId, checkJob: false, deviceId: getDeviceId() };
      
      // In new RAG flow, we assume context is retrieved from Qdrant by the backend based on 'text'
      // We don't need to send explicit 'recordInfo' unless we are doing direct analysis of a text blob not in Qdrant.
      // For consistency with old code, we use 'chatInput'
      payload.chatInput = text;

      const response = await axios.post('/api/chat', payload);
      const aiText = extractTextFromResponse(response.data);
      // Use API's thinking_time if available, otherwise calculate from request duration
      const duration = response.data.thinking_time ?? Number(((Date.now() - startTime) / 1000).toFixed(1));
      
      addMessage('assistant', aiText, duration, true);
    } catch (error) {
      addMessage('assistant', t('connection_error'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleEditMessage = async (messageId: string, newContent: string) => {
    const msgIndex = messages.findIndex(m => m.id === messageId);
    if (msgIndex === -1) return;
    const msg = messages[msgIndex];
    setMessages(prev => prev.slice(0, msgIndex)); // Optimistic UI

    try {
      let idsToDelete: number[] = [];
      if (!isNaN(Number(messageId))) idsToDelete.push(Number(messageId));
      
      if (idsToDelete.length === 0) {
         // Fallback logic to find message by content if ID is ephemeral UUID
         const { data: recentMsgs } = await supabase.from('chat_history').select('id, content').eq('session_id', sessionId).order('created_at', { ascending: false }).limit(20);
         if (recentMsgs) {
            const targetMsg = recentMsgs.find((row : any) => row.content === msg.content);
            if (targetMsg) idsToDelete.push(targetMsg.id);
         }
      }

      if (idsToDelete.length > 0) await supabase.from('chat_history').delete().in('id', idsToDelete);
    } catch (err) { console.error("Failed to delete old messages:", err); }

    handleSendMessage(newContent);
  };

  const extractTextFromResponse = (data: any): string => {
    if (!data) return "No response received.";
    if (typeof data === 'string') return data;
    if (data.answer) return data.answer; // agentsmedchat API response
    if (data.output) return typeof data.output === 'string' ? data.output : JSON.stringify(data.output);
    if (data.text) return data.text;
    if (data.message) return data.message;
    if (data.content) return data.content;
    const keys = Object.keys(data);
    for (const key of keys) {
      if (typeof data[key] === 'string' && data[key].length > 0) return data[key];
    }
    return JSON.stringify(data, null, 2);
  };

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden font-sans transition-colors duration-300">
      <AnimatePresence>
        {showStartupLoader && (
           <StartupLoader onComplete={() => setShowStartupLoader(false)} />
        )}
      </AnimatePresence>
      <Sidebar 
        isOpen={isSidebarOpen} 
        onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
        activeTab={activeTab}
        onTabChange={(tab) => {
          setActiveTab(tab);
          setMessages([]);
          setEhrPhase('idle');
          setSessionId(uuidv4());
          setChatTitle(tab === 'ehr' ? "Knowledge Base" : "New Chat");
          setIsLoading(false);
        }}
        onLoadSession={handleLoadSession}
        currentSessionId={sessionId}
      />

      <div className={clsx("flex-1 flex flex-col h-full relative transition-all duration-300 ease-in-out", isSidebarOpen ? "md:ml-72" : "md:ml-16")}>
        
        {/* Chat Header */}
        <header className="sticky top-0 z-10 w-full bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
           <div className="w-full px-4 h-16 flex items-center justify-between relative">
               <div className="flex items-center gap-3 text-muted-foreground hover:text-foreground transition-colors">
                  <button onClick={() => setIsSidebarOpen(!isSidebarOpen)} className="md:hidden p-1 hover:bg-muted rounded-full">
                    <Menu size={24} />
                  </button>
                  <span className="text-lg font-medium cursor-pointer">MedChat</span>
               </div>
              
              <div className="absolute left-1/2 transform -translate-x-1/2 text-sm font-medium text-foreground/80 truncate max-w-[200px] hidden md:block">
                  {chatTitle.charAt(0).toUpperCase() + chatTitle.slice(1)}
              </div>

              <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-[#3ECF8E]/10 flex items-center justify-center border border-[#3ECF8E]/20 shadow-sm">
                    <User className="w-5 h-5 text-[#3ECF8E]" />
                  </div>
              </div>
              
              {isSessionLoading && (
                <div className="absolute bottom-0 left-0 w-full h-[2px] bg-muted overflow-hidden">
                  <div className="h-full bg-primary animate-progress-indeterminate origin-left"></div>
                </div>
              )}
           </div>
        </header>

        <main className="flex-1 overflow-y-auto scroll-smooth">
          <div className={clsx("mx-auto w-full px-4 py-6 md:py-10 transition-all duration-500", activeTab === 'ehr' ? "max-w-5xl" : "max-w-3xl")}>
            
            {/* --- RAG / EHR MODE UI --- */}
            {activeTab === 'ehr' && messages.length === 0 && (
                <div className="flex flex-col w-full animate-in fade-in slide-in-from-bottom-4 duration-700">
                    <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col items-center justify-center mb-8">
                        <div className="inline-flex items-center gap-2 mb-3 px-3 py-1 rounded-full bg-secondary/50 border border-border/50 backdrop-blur-sm">
                            <Sparkles className="w-3 h-3 text-[#3ECF8E]" />
                            <span className="text-[10px] uppercase tracking-widest text-muted-foreground font-medium">{t('rag.processor')}</span>
                        </div>
                        <h1 className="text-3xl font-medium text-foreground text-center">{t('rag.title')}</h1>
                    </motion.div>

                    <RagIngestion onComplete={handleRagComplete} />

<RagLibrary books={books} stats={libraryStats} isLoading={isLibraryLoading} onRefresh={fetchLibrary} />
                </div>
            )}

            {/* --- NEW CHAT HERO (Regular Chat) --- */}
            {messages.length === 0 && activeTab === 'chat' && !isSessionLoading && (
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-full -mt-24 w-full max-w-3xl px-8 flex flex-col items-start space-y-2">
                <div className="space-y-2 text-left">
                  <h1 className="text-5xl font-medium bg-gradient-to-r from-[#4285f4] via-[#9b72cb] to-[#d96570] text-transparent bg-clip-text pb-2">
                    {t('hello')}
                  </h1>
                  <h2 className="text-4xl font-medium text-muted-foreground">
                    {t('how_help')}
                  </h2>
                </div>
              </div>
            )}

            {/* --- CHAT MESSAGES --- */}
            <div className="space-y-2 pb-40">
              {messages.map((msg, index) => {
                const lastUserMessageId = [...messages].reverse().find(m => m.role === 'user')?.id;
                return (
                  <MessageBubble 
                    key={msg.id} 
                    message={msg} 
                    onStreamUpdate={() => scrollToBottom("auto")}
                    onEdit={handleEditMessage}
                    isLastUserMessage={msg.id === lastUserMessageId}
                  />
                );
              })}
              
              {isLoading && (
                <div className="flex items-start gap-4 mb-6 w-full max-w-3xl mx-auto animate-in fade-in slide-in-from-bottom-2 duration-300">
                   {activeTab === 'ehr' ? (
                       <div className="flex flex-col gap-2">
                          <div className="flex items-center gap-2">
                              <Sparkles size={16} className="text-accent animate-pulse" />
                              <ThinkingText />
                          </div>
                      </div>
                   ) : (
                       <div className="flex items-center gap-3">
                         <div className="text-sm text-muted-foreground animate-pulse">{t('rag.thinking')}</div>
                         <div className="loader3">
                           <div className="circle1"></div><div className="circle1"></div><div className="circle1"></div><div className="circle1"></div><div className="circle1"></div>
                         </div>
                       </div>
                   )}
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

          </div>
        </main>

        <div className={clsx(
          "transition-all duration-500 ease-in-out w-full max-w-3xl mx-auto px-4",
          (messages.length === 0 && activeTab === 'chat') 
            ? "absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" 
            : "absolute bottom-0 left-1/2 -translate-x-1/2 bg-background pb-2 pt-2",
          // Hide input area in EHR mode if we haven't started chatting yet
          (activeTab === 'ehr' && messages.length === 0) && "translate-y-[200%] opacity-0 pointer-events-none"
        )}>
          {/* Show input if we are chatting OR if we are in regular chat. 
              We hide it initially in EHR mode since we use the Ingestion UI.
           */}
          <InputArea 
              ref={inputAreaRef}
              onSend={handleSendMessage} 
              disabled={isLoading} 
              placeholder={activeTab === 'ehr' ? t('rag.ask_placeholder') : t('enter_prompt')}
            />
        </div>

      </div>
    </div>
  );
}
