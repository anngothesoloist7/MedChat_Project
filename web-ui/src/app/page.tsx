'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Sidebar } from '@/components/Sidebar';
import { MessageBubble, Message } from '@/components/MessageBubble';
import { InputArea, InputAreaRef } from '@/components/InputArea';
import { PatientCard } from '@/components/PatientCard';
import { Loader2, Gem, ChevronDown, Menu } from 'lucide-react';
import axios from 'axios';
import { v4 as uuidv4 } from 'uuid';
import { clsx } from 'clsx';
import { createClient } from '@/utils/supabase/client';
import { useSettings } from '@/context/SettingsContext';
import { getDeviceId } from '@/utils/device';

import { DeepResearchIndicator, ResearchStage } from '@/components/DeepResearchIndicator';

type EhrPhase = 'idle' | 'submitting' | 'polling' | 'refining' | 'summary' | 'chatting';

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
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [activeTab, setActiveTab] = useState<'chat' | 'ehr'>('chat');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [patientData, setPatientData] = useState<any>(null);
  const [ehrPhase, setEhrPhase] = useState<EhrPhase>('idle');
  const [sessionId, setSessionId] = useState(uuidv4()); 
  const [pollIntervalId, setPollIntervalId] = useState<NodeJS.Timeout | null>(null);
  const [chatTitle, setChatTitle] = useState("New Chat");
  const [isSessionLoading, setIsSessionLoading] = useState(false);
  const supabase = createClient();
  const { t } = useSettings();

  useEffect(() => {
    if (window.innerWidth < 768) {
      setIsSidebarOpen(false);
    }
  }, []);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputAreaRef = useRef<InputAreaRef>(null);

  useEffect(() => {
    if (!isLoading) {
      // Small timeout to ensure DOM is ready and animation might be finishing
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

  useEffect(() => {
    return () => {
      if (pollIntervalId) clearInterval(pollIntervalId);
    };
  }, [pollIntervalId]);

  // --- Session Locking Heartbeat ---
  useEffect(() => {
    if (!sessionId) return;

    const deviceId = getDeviceId();
    
    // Heartbeat every 30 seconds
    const heartbeat = setInterval(async () => {
      try {
        await supabase.rpc('refresh_session_lock', {
          p_session_id: sessionId,
          p_device_id: deviceId
        });
      } catch (e) {
        // Ignore lock errors
      }
    }, 30000);

    // Initial lock acquisition/refresh (just in case)
    supabase.rpc('refresh_session_lock', {
      p_session_id: sessionId,
      p_device_id: deviceId
    }).then(({ error }) => {
      if (error) console.warn("Session lock init failed (ignoring)");
    });

    return () => {
      clearInterval(heartbeat);
      // Release lock on unmount or session change
      // Note: This might not fire on tab close reliably, but the 1-min timeout handles that.
      supabase.rpc('release_session_lock', {
        p_session_id: sessionId,
        p_device_id: deviceId
      });
    };
  }, [sessionId]);

  const addMessage = (role: 'user' | 'assistant', content: string, thinkingTime?: number, shouldAnimate: boolean = false) => {
    setMessages(prev => [...prev, {
      id: uuidv4(),
      role,
      content,
      timestamp: new Date(),
      thinkingTime,
      shouldAnimate
    }]);
  };

  // Helper to strip markdown
  const stripMarkdown = (text: string) => {
    return text
      .replace(/(\*\*|__)(.*?)\1/g, '$2') // Bold
      .replace(/(\*|_)(.*?)\1/g, '$2')   // Italic
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // Links
      .replace(/#{1,6}\s?/g, '') // Headers
      .replace(/`{3}[\s\S]*?`{3}/g, '') // Code blocks
      .replace(/`(.+?)`/g, '$1') // Inline code
      .replace(/^\s*>\s?/gm, '') // Blockquotes
      .trim();
  };

  // --- History Loading ---
  const handleLoadSession = async (id: string, type: 'chat' | 'ehr' = 'chat') => {
    if (pollIntervalId) {
      clearInterval(pollIntervalId);
      setPollIntervalId(null);
    }
    setSessionId(id);
    setActiveTab(type); // Switch tab based on session type
    setPatientData(null); // Clear any EHR data
    setEhrPhase('chatting'); // Assume we are ready to chat when loading history
    setMessages([]); // Clear current view
    setIsSessionLoading(true);
    setChatTitle("Loading...");
    
    try {
      const tableName = type === 'ehr' ? 'ehr_analyzer_memory' : 'quick_chat_memory';
      const { data, error } = await supabase
        .from(tableName)
        .select('*')
        .eq('session_id', id)
        .order('created_at', { ascending: true });

      if (error) throw error;

      if (data && data.length > 0) {
        const loadedMessages: Message[] = [];
        
        data.forEach((row: any) => {
           let msg = row.message;

           
           // Helper to safely extract string content
           const safeContent = (c: any) => {
             if (typeof c === 'string') return c;
             if (typeof c === 'object') return JSON.stringify(c);
             return String(c || "");
           };

           // Try to parse string message as JSON if it looks like one
           if (typeof msg === 'string' && (msg.startsWith('{') || msg.startsWith('['))) {
             try {
               const parsed = JSON.parse(msg);
               if (typeof parsed === 'object' && parsed !== null) {
                 msg = parsed;
               }
             } catch (e) {
               // Keep as string
             }
           }

           // Special handling for EHR patient data
           if (type === 'ehr' && msg && typeof msg === 'object' && msg.demographics) {
             setPatientData(msg);
             return; // Skip adding this to messages list
           }

           let role: 'user' | 'assistant' = 'user';
           let content = '';
           let thinkingTime = undefined;

           if (typeof msg === 'string') {
             content = msg;
             // Heuristic: if it's a short string, assume user? Or just default to user.
             role = 'user'; 
           } else if (typeof msg === 'object' && msg !== null) {
             // Extract Role
             if (msg.role) role = msg.role;
             else if (msg.type === 'human' || msg.type === 'user') role = 'user';
             else if (msg.type === 'ai' || msg.type === 'assistant') role = 'assistant';

             // Extract Content
             if (msg.content) content = safeContent(msg.content);
             else if (msg.chatInput) { content = safeContent(msg.chatInput); role = 'user'; }
             else if (msg.output) { content = safeContent(msg.output); role = 'assistant'; }
             else if (msg.text) content = safeContent(msg.text);
             else if (msg.response) { content = safeContent(msg.response); role = 'assistant'; }
             else if (msg.answer) { content = safeContent(msg.answer); role = 'assistant'; }
             else if (msg.question) { content = safeContent(msg.question); role = 'user'; }
             else {
               // Fallback: dump the whole object so we see something
               content = JSON.stringify(msg);
             }
             
             // Extract thinking time
             if (msg.thinkingTime) thinkingTime = msg.thinkingTime;
           }

           if (content) {
              loadedMessages.push({
                id: row.id.toString(),
                role,
                content,
                timestamp: new Date(row.created_at),
                thinkingTime
              });
           }
        });
        
        console.log("Loaded messages:", loadedMessages);
        setMessages(loadedMessages);
        
        // Set title from first user message
        const firstUserMsg = loadedMessages.find(m => m.role === 'user');
        if (firstUserMsg) {
           const cleanTitle = stripMarkdown(firstUserMsg.content);
           setChatTitle(cleanTitle.length > 40 ? cleanTitle.substring(0, 40) + '...' : cleanTitle);
        } else {
           setChatTitle("Conversation");
        }
      } else {
        // No data found for this session
        setMessages([]);
        setChatTitle("New Chat");
      }
    } catch (err) {
      console.error("Failed to load session:", err);
      addMessage('assistant', "⚠️ Failed to load conversation history.");
      setChatTitle("Error Loading Chat");
    } finally {
      setIsSessionLoading(false);
    }
  };

  // --- EHR Workflow Steps ---
  const handleFileLoaded = (data: any) => {
    setPatientData(data);
    setChatTitle("Knowledge Base");
  };

  const handleAnalyze = async () => {
    if (!patientData) return;

    setEhrPhase('submitting');
    setIsLoading(true);

    try {
      const formData = new FormData();
      // patientData is the File object from FileDropzone
      formData.append('file', patientData);

      addMessage('assistant', t('analysis_started'));

      const response = await axios.post('/api/rag/process', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (response.data.success) {
        addMessage('assistant', t('upload_success'));
        if (response.data.logs) {
           console.log("RAG Logs:", response.data.logs);
        }
        setEhrPhase('chatting');
      } else {
        throw new Error(response.data.error || 'Unknown error');
      }

    } catch (error) {
      console.error(error);
      addMessage('assistant', t('upload_fail'));
      setEhrPhase('idle');
    } finally {
      setIsLoading(false);
    }
  };

  // Polling and summary functions removed as they are not needed for the synchronous RAG pipeline
  const startPolling = () => {}; 
  const getSummary = async () => {};

  const handleSendMessage = async (text: string) => {
    if (messages.length === 0) {
       const cleanTitle = stripMarkdown(text);
       setChatTitle(cleanTitle.length > 40 ? cleanTitle.substring(0, 40) + '...' : cleanTitle);
    }
    
    addMessage('user', text);
    setIsLoading(true);
    const startTime = Date.now();

    try {
      let payload: any = {
        sessionId: sessionId,
        checkJob: false,
        deviceId: getDeviceId()
      };

      if (activeTab === 'ehr') {
        payload.recordInfo = text;
      } else {
        payload.chatInput = text;
      }

      const response = await axios.post('/api/chat', payload);
      const aiText = extractTextFromResponse(response.data);
      const duration = Number(((Date.now() - startTime) / 1000).toFixed(1));
      
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
    
    // Optimistically update UI: Remove this message and all subsequent ones
    setMessages(prev => prev.slice(0, msgIndex));

    // Delete from Supabase
    try {
      const tableName = activeTab === 'ehr' ? 'ehr_analyzer_memory' : 'quick_chat_memory';
      let idsToDelete: number[] = [];

      // Check if ID is numeric (from DB)
      if (!isNaN(Number(messageId))) {
        idsToDelete.push(Number(messageId));
        // Try to find the next message (assistant response) in the current list
        // Note: The next message in the list (index + 1) is the one that followed.
        const nextMsg = messages[msgIndex + 1];
        if (nextMsg && !isNaN(Number(nextMsg.id))) {
           idsToDelete.push(Number(nextMsg.id));
        }
      } 
      
      // If we didn't get IDs (or only got some), try to find by content
      if (idsToDelete.length === 0) {
         const { data: recentMsgs } = await supabase
            .from(tableName)
            .select('id, message')
            .eq('session_id', sessionId)
            .order('created_at', { ascending: false })
            .limit(20);

         if (recentMsgs) {
            const targetMsg = recentMsgs.find((row: any) => {
               const m = row.message;
               // Check various content fields
               const content = typeof m === 'string' ? m : (m.content || m.chatInput || m.text || m.question);
               return content === msg.content;
            });

            if (targetMsg) {
               idsToDelete.push(targetMsg.id);
               // The response is likely the one immediately preceding it in the descending list (newer)
               const targetIndex = recentMsgs.indexOf(targetMsg);
               if (targetIndex > 0) {
                  idsToDelete.push(recentMsgs[targetIndex - 1].id);
               }
            }
         }
      }

      if (idsToDelete.length > 0) {
        await supabase
          .from(tableName)
          .delete()
          .in('id', idsToDelete);
      }
    } catch (err) {
      console.error("Failed to delete old messages:", err);
    }

    // Send the new message
    handleSendMessage(newContent);
  };

  const extractTextFromResponse = (data: any): string => {
    if (!data) return "No response received.";
    if (typeof data === 'string') return data;
    if (data.output) return typeof data.output === 'string' ? data.output : JSON.stringify(data.output);
    if (data.text) return data.text;
    if (data.message) return data.message;
    if (data.content) return data.content;
    const keys = Object.keys(data);
    for (const key of keys) {
      if (typeof data[key] === 'string' && data[key].length > 0) {
         return data[key];
      }
    }
    return JSON.stringify(data, null, 2);
  };

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden font-sans transition-colors duration-300">
      <Sidebar 
        isOpen={isSidebarOpen} 
        onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
        activeTab={activeTab}
        onTabChange={(tab) => {
          setActiveTab(tab);
          setMessages([]);
          setEhrPhase('idle');
          setPatientData(null);
          setSessionId(uuidv4()); // New session on tab switch
          setChatTitle(tab === 'ehr' ? "Knowledge Base" : "New Chat");
          if (pollIntervalId) {
             clearInterval(pollIntervalId);
             setPollIntervalId(null);
          }
          setIsLoading(false);
        }}
        onLoadSession={handleLoadSession}
        currentSessionId={sessionId}
      />

      <div className={clsx(
        "flex-1 flex flex-col h-full relative transition-all duration-300 ease-in-out",
        isSidebarOpen ? "md:ml-72" : "md:ml-16"
      )}>
        
        {/* Chat Header */}
        <header className="sticky top-0 z-10 w-full bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
           <div className="w-full px-4 h-16 flex items-center justify-between relative">
               <div className="flex items-center gap-3 text-muted-foreground hover:text-foreground transition-colors">
                  <button 
                    onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                    className="md:hidden p-1 hover:bg-muted rounded-full"
                  >
                    <Menu size={24} />
                  </button>
                  <span className="text-lg font-medium cursor-pointer">MedChat</span>
               </div>
              
              <div className="absolute left-1/2 transform -translate-x-1/2 text-sm font-medium text-foreground/80 truncate max-w-[200px] hidden md:block">
                  {chatTitle.charAt(0).toUpperCase() + chatTitle.slice(1)}
              </div>

              <div className="flex items-center gap-3">
                 <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-blue-500 to-red-500 p-[2px]">
                    <img 
                      src="https://api.dicebear.com/7.x/avataaars/svg?seed=Felix" 
                      className="rounded-full w-full h-full bg-background object-cover" 
                      alt="User" 
                    />
                 </div>
              </div>
              
              {/* Horizontal Loading Bar */}
              {isSessionLoading && (
                <div className="absolute bottom-0 left-0 w-full h-[2px] bg-muted overflow-hidden">
                  <div className="h-full bg-primary animate-progress-indeterminate origin-left"></div>
                </div>
              )}
           </div>
        </header>

        <main className="flex-1 overflow-y-auto scroll-smooth">
          <div className="max-w-3xl mx-auto w-full px-4 py-6 md:py-10">
            
            {/* Gem Header for EHR Mode */}
            {activeTab === 'ehr' && messages.length === 0 && !patientData && (
               <div className="flex flex-col items-center justify-center mb-10 animate-in fade-in slide-in-from-bottom-4">
                  <div className="w-16 h-16 bg-gradient-to-br from-emerald-400 to-cyan-600 rounded-2xl flex items-center justify-center shadow-lg mb-4">
                     <Gem size={32} className="text-white" />
                  </div>
                  <h1 className="text-3xl font-medium text-foreground">{t('ehr_analysis')}</h1>
                  <p className="text-muted-foreground mt-2 text-center max-w-md">
                     {t('virtual_doctor')}
                  </p>
               </div>
            )}

              {activeTab === 'ehr' && (patientData || messages.length === 0) && (
                <PatientCard 
                  data={patientData} 
                  onFileLoaded={handleFileLoaded} 
                  onAnalyze={handleAnalyze}
                  onDelete={() => {
                    setPatientData(null);
                    setChatTitle("Knowledge Base");
                    setEhrPhase('idle');
                  }}
                  isAnalyzing={ehrPhase !== 'idle' && ehrPhase !== 'chatting'}
                  status={ehrPhase === 'chatting' ? t('ready') : undefined}
                />
              )}

              {/* Deep Research Indicator */}
              {activeTab === 'ehr' && (ehrPhase === 'submitting' || ehrPhase === 'polling' || ehrPhase === 'refining') && (
                 <DeepResearchIndicator stage={ehrPhase === 'submitting' ? 'uploading' : ehrPhase === 'polling' ? 'analyzing' : 'refining'} />
              )}

            {messages.length === 0 && !patientData && activeTab === 'chat' && !isSessionLoading && (
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

            <div className="space-y-2 pb-40">
              {messages.map((msg, index) => {
                // Find the last user message to only show edit button there
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
              
              {isLoading && activeTab !== 'ehr' && (
                <div className="flex items-start gap-4 mb-6 w-full max-w-3xl mx-auto animate-in fade-in slide-in-from-bottom-2 duration-300">
                   <div className="flex items-center gap-3">
                     <div className="text-sm text-muted-foreground animate-pulse">
                       {t('thinking')}
                     </div>
                     <div className="loader3">
                       <div className="circle1"></div>
                       <div className="circle1"></div>
                       <div className="circle1"></div>
                       <div className="circle1"></div>
                       <div className="circle1"></div>
                     </div>
                   </div>
                </div>
              )}
              
              {/* Show thinking for EHR chat only after initial analysis is done */}
              {isLoading && activeTab === 'ehr' && ehrPhase === 'chatting' && (
                 <div className="flex items-start gap-4 mb-6 w-full max-w-3xl mx-auto animate-in fade-in slide-in-from-bottom-2 duration-300">
                    <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 bg-gradient-to-tr from-blue-500 to-red-500 animate-pulse">
                       <Gem size={16} className="text-white" />
                    </div>
                    <div className="flex flex-col gap-2 pt-1.5">
                       <ThinkingText />
                    </div>
                 </div>
              )}
              <div ref={messagesEndRef} />
            </div>

          </div>
        </main>

        <div className={clsx(
          "transition-all duration-500 ease-in-out w-full max-w-3xl mx-auto px-4",
          (messages.length === 0 && !patientData && activeTab === 'chat') 
            ? "absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" 
            : "absolute bottom-0 left-1/2 -translate-x-1/2 bg-background pb-2 pt-2"
        )}>
          {/* Only show input area if NOT in EHR/Knowledge Base mode */}
          {activeTab !== 'ehr' && (
            <InputArea 
              ref={inputAreaRef}
              onSend={handleSendMessage} 
              disabled={isLoading} 
              placeholder={t('enter_prompt')}
            />
          )}
        </div>

      </div>
    </div>
  );
}
