'use client';

import React, { useEffect, useState } from 'react';
import { Plus, MessageSquare, Settings, HelpCircle, History, Menu, Gem, Sparkles, MoreVertical, Trash2, Edit2, Check, X, Loader2, FileText } from 'lucide-react';
import { clsx } from 'clsx';
import { createPortal } from 'react-dom';
import { createClient } from '@/utils/supabase/client';
import { useSettings } from '@/context/SettingsContext';
import { SettingsModal } from './SettingsModal';
import { getDeviceId } from '@/utils/device';

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  activeTab: 'chat' | 'ehr';
  onTabChange: (tab: 'chat' | 'ehr') => void;
  onLoadSession: (sessionId: string, type: 'chat' | 'ehr') => void;
  currentSessionId?: string;
}

interface ChatSession {
  session_id: string;
  title: string;
  updated_at: string;
  type: 'chat' | 'ehr';
}

export function Sidebar({ isOpen, onToggle, activeTab, onTabChange, onLoadSession, currentSessionId }: SidebarProps) {
  const [recentSessions, setRecentSessions] = useState<ChatSession[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(0);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [activeMenuId, setActiveMenuId] = useState<string | null>(null);
  const [menuPosition, setMenuPosition] = useState<{ top: number; left: number }>({ top: 0, left: 0 });
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const supabase = createClient();
  const { t } = useSettings();
  const SESSIONS_PER_PAGE = 50;

  useEffect(() => {
    fetchHistory(0);
    
    // Close menu when scrolling (but not on outside click - that's handled by overlay)
    const handleScroll = () => setActiveMenuId(null);
    
    window.addEventListener('scroll', handleScroll, true);
    
    return () => {
      window.removeEventListener('scroll', handleScroll, true);
    };
  }, []);

  const fetchHistory = async (pageNum: number) => {
    try {
      if (pageNum === 0) setIsLoading(true);
      else setIsLoadingMore(true);

      // Fetch from new unified chat_history table
      const { data, error } = await supabase
          .from('chat_history')
          .select('session_id, role, content, created_at, metadata')
          .order('created_at', { ascending: true });

      if (error) {
        console.error("Supabase fetch error details:", JSON.stringify(error, null, 2));
        if (error.code === '42P01') {
             console.error("Table 'chat_history' does not exist. Please run the setup SQL.");
        }
        // Don't throw, handling gracefully
        setRecentSessions([]);
        return;
      }
      
      console.log('Raw History Data:', data);

      const allData = (data || []).map((d: any) => ({
        ...d,
        // Adapt string columns 'role'/'content' to the object structure expected by logic
        message: { role: d.role, content: d.content }, 
        type: d.metadata?.type || 'chat'
      }));

      if (allData.length === 0) {
         setHasMore(false);
         if (pageNum === 0) setRecentSessions([]);
         return;
      }

      const sessionMap = new Map<string, ChatSession>();
      const sessionFirstMessage = new Map<string, any>();
      
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

      // Helper to capitalize first letter
      const capitalizeFirst = (text: string) => {
        if (!text) return text;
        return text.charAt(0).toUpperCase() + text.slice(1);
      };

      // Find first user message for each session
      allData.forEach((row: any) => {
        if (!sessionFirstMessage.has(row.session_id)) {
          const msg = row.message;
          let isUserMessage = false;
          
          // Check if this is a user message
          if (typeof msg === 'object' && msg !== null) {
            if (msg.role === 'user' || msg.type === 'human' || msg.type === 'user') {
              isUserMessage = true;
            }
          }
          
          // For EHR, we accept any message if we haven't found one yet
          if (isUserMessage || typeof msg === 'string' || row.type === 'ehr') {
            sessionFirstMessage.set(row.session_id, row);
          }
        }
      });

      // Build session list from unique sessions
      const uniqueSessionIds = Array.from(new Set(allData.map((row: any) => row.session_id)));
      
      // Get the sessions with their metadata (last updated time)
      const sessionMetadata = new Map<string, { updated_at: string, type: 'chat' | 'ehr' }>();
      allData.forEach((row: any) => {
        const existing = sessionMetadata.get(row.session_id);
        if (!existing || new Date(row.created_at) > new Date(existing.updated_at)) {
          sessionMetadata.set(row.session_id, { updated_at: row.created_at, type: row.type });
        }
      });

      uniqueSessionIds.forEach((sessionId) => {
        // Try to get title from localStorage first
        const savedTitles = JSON.parse(localStorage.getItem('chat_titles') || '{}');
        let title = savedTitles[sessionId];

        if (!title) {
          title = "Untitled Chat";
          const firstMsg = sessionFirstMessage.get(sessionId);
          
          if (firstMsg) {
            if (firstMsg.type === 'ehr') {
               title = "Knowledge Base"; // Default for EHR
            }
            
            try {
              const msg = firstMsg.message;
              if (typeof msg === 'string') {
                title = msg;
              } else if (msg?.content) {
                title = msg.content;
              } else if (msg?.chatInput) {
                title = msg.chatInput;
              } else if (msg?.text) {
                title = msg.text;
              }
              
              // If we found a specific title in the message, use it, otherwise keep default
              if (title === "Untitled Chat" && firstMsg.type === 'ehr') {
                 title = "Knowledge Base";
              }
            } catch (e) {
              console.error('Error parsing message:', e);
            }
          }
        }

        const cleanTitle = stripMarkdown(title);
        const capitalizedTitle = capitalizeFirst(cleanTitle);

        const metadata = sessionMetadata.get(sessionId);
        
        sessionMap.set(sessionId, {
          session_id: sessionId,
          title: capitalizedTitle.substring(0, 40) + (capitalizedTitle.length > 40 ? '...' : ''),
          updated_at: metadata?.updated_at || new Date().toISOString(),
          type: metadata?.type || 'chat'
        });
      });

      // Sort by updated_at descending
      const allSessions = Array.from(sessionMap.values()).sort((a, b) => 
        new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      );

      // Apply pagination
      const from = pageNum * SESSIONS_PER_PAGE;
      const to = from + SESSIONS_PER_PAGE;
      const paginatedSessions = allSessions.slice(from, to);

      if (paginatedSessions.length < SESSIONS_PER_PAGE || to >= allSessions.length) {
        setHasMore(false);
      }

      if (pageNum === 0) {
         setRecentSessions(paginatedSessions);
      } else {
         setRecentSessions(prev => {
            // Merge and deduplicate
            const existingIds = new Set(prev.map(s => s.session_id));
            const uniqueNew = paginatedSessions.filter(s => !existingIds.has(s.session_id));
            return [...prev, ...uniqueNew];
         });
      }
      
      setPage(pageNum);

    } catch (err) {
      console.error("Error fetching history:", err);
    } finally {
      setIsLoading(false);
      setIsLoadingMore(false);
    }
  };

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
    
    // Load more when scrolled to bottom (with 20px buffer)
    if (scrollHeight - scrollTop <= clientHeight + 20 && hasMore && !isLoadingMore && !isLoading) {
      fetchHistory(page + 1);
    }
  };

  const confirmDelete = async (sessionId: string) => {
    try {
      // Use unified table
      const { error } = await supabase
        .from('chat_history')
        .delete()
        .eq('session_id', sessionId);

      if (error) throw error;

      setRecentSessions(prev => prev.filter(s => s.session_id !== sessionId));
      
      // Also remove from local storage titles
      const savedTitles = JSON.parse(localStorage.getItem('chat_titles') || '{}');
      delete savedTitles[sessionId];
      localStorage.setItem('chat_titles', JSON.stringify(savedTitles));

      if (currentSessionId === sessionId) {
         onTabChange('chat');
      }
      
      setDeleteConfirmId(null);
    } catch (err) {
      console.error("Error deleting session:", err);
    }
  };

  const startRename = (session: ChatSession, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingSessionId(session.session_id);
    setEditTitle(session.title);
    setActiveMenuId(null);
  };

  const saveRename = (sessionId: string, e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!editTitle.trim()) return;

    const savedTitles = JSON.parse(localStorage.getItem('chat_titles') || '{}');
    savedTitles[sessionId] = editTitle.trim();
    localStorage.setItem('chat_titles', JSON.stringify(savedTitles));

    setRecentSessions(prev => prev.map(s => 
      s.session_id === sessionId ? { ...s, title: editTitle.trim() } : s
    ));
    setEditingSessionId(null);
  };

  const cancelRename = () => {
    setEditingSessionId(null);
    setEditTitle("");
  };

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={onToggle}
        />
      )}

      <div
        className={clsx(
          "fixed inset-y-0 left-0 z-50 flex flex-col bg-secondary transition-all duration-300 ease-in-out border-r border-transparent overflow-hidden",
          isOpen ? "w-72 translate-x-0" : "w-0 -translate-x-full md:w-16 md:translate-x-0"
        )}
      >
        {/* Header / Menu Toggle */}
        <div className={clsx("flex items-center", isOpen ? "px-4 py-4 justify-between" : "justify-center py-4")}>
          <button 
            onClick={onToggle}
            className="w-10 h-10 flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted rounded-full transition-colors"
          >
            <Menu size={20} />
          </button>
        </div>

        {/* New Chat Button */}
        <div className={clsx("mb-4", isOpen ? "px-4" : "px-2")}>
          <button 
            onClick={() => {
               onTabChange('chat');
               if (window.innerWidth < 768) {
                 onToggle();
               }
            }}
            className={clsx(
              "flex items-center gap-3 bg-input hover:bg-muted text-foreground rounded-full transition-colors border border-border",
              isOpen ? "px-4 py-3 w-full" : "w-10 h-10 justify-center mx-auto p-0"
            )}
          >
            <Plus size={20} className="text-muted-foreground" />
            {isOpen && <span className="font-medium text-sm">{t('new_chat')}</span>}
          </button>
        </div>

        {/* Navigation / Gems */}
        <div 
          className={clsx("flex-1 overflow-y-auto custom-scrollbar", isOpen ? "px-4" : "px-2")}
          onScroll={handleScroll}
        >
          
          {/* Gems Section */}
          {isOpen && <div className="mb-2 px-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">{t('gems')}</div>}
          
          <div className={clsx("space-y-1", isOpen ? "mb-6" : "mb-4")}>
             {/* MedChat Gem (EHR) */}
             <button
              onClick={() => {
                onTabChange('ehr');
                if (window.innerWidth < 768) {
                  onToggle();
                }
              }}
              className={clsx(
                "flex items-center gap-3 transition-colors group",
                isOpen ? "w-full px-3 py-2 rounded-full text-sm" : "w-10 h-10 justify-center mx-auto rounded-full",
                activeTab === 'ehr' ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:bg-muted"
              )}
            >
               <div className={clsx(
                 "flex items-center justify-center transition-all duration-200",
                 isOpen ? "w-8 h-8 rounded-full" : "w-full h-full rounded-full",
                 "bg-transparent group-hover:bg-emerald-500/20",
                 activeTab === 'ehr' ? "text-emerald-500" : "text-emerald-600 dark:text-emerald-400"
              )}>
                 <Gem size={20} />
              </div>
              {isOpen && (
                 <div className="flex flex-col items-start">
                    <span className="font-medium">{t('ehr_analysis')}</span>
                 </div>
              )}
            </button>
          </div>

          {/* Recent History - Only show when sidebar is open */}
          {isOpen && (
            <>
              <div className="mb-2 px-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">{t('recent')}</div>
              
              <div className="space-y-1">
                {isLoading ? (
                   <div className="flex justify-center py-4">
                     <Loader2 className="animate-spin text-muted-foreground" size={20} />
                   </div>
                ) : (
                  <>
                    {recentSessions.map((session) => {
                      const isActive = session.session_id === currentSessionId;
                      const isEditing = editingSessionId === session.session_id;
                      const isMenuOpen = activeMenuId === session.session_id;

                      return (
                        <div key={session.session_id} className="relative group">
                          {isEditing ? (
                            <div className="w-full flex items-center gap-2 px-3 py-2 rounded-full bg-muted">
                              <input
                                type="text"
                                value={editTitle}
                                onChange={(e) => setEditTitle(e.target.value)}
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') saveRename(session.session_id);
                                  if (e.key === 'Escape') cancelRename();
                                }}
                                className="flex-1 bg-transparent border-none outline-none text-sm min-w-0"
                                autoFocus
                                onClick={(e) => e.stopPropagation()}
                              />
                              <button onClick={() => saveRename(session.session_id)} className="text-green-500 hover:text-green-600">
                                <Check size={14} />
                              </button>
                              <button onClick={cancelRename} className="text-red-500 hover:text-red-600">
                                <X size={14} />
                              </button>
                            </div>
                          ) : (
                            <div
                              className={clsx(
                                "w-full flex items-center gap-2 px-3 py-2 rounded-full text-sm transition-colors relative group/item",
                                isActive 
                                  ? "bg-accent text-accent-foreground font-medium" 
                                  : "text-muted-foreground hover:bg-muted"
                              )}
                            >
                                <button
                                onClick={() => {
                                  onLoadSession(session.session_id, session.type);
                                  if (window.innerWidth < 768) {
                                    onToggle(); // Close sidebar on mobile
                                  }
                                }}
                                className="flex-1 flex items-center gap-3 min-w-0 text-left outline-none"
                              >
                                {session.type === 'ehr' ? (
                                  <FileText size={18} className={clsx("shrink-0", isActive ? "text-accent-foreground" : "text-muted-foreground")} />
                                ) : (
                                  <MessageSquare size={18} className={clsx("shrink-0", isActive ? "text-accent-foreground" : "text-muted-foreground")} />
                                )}
                                <span className="truncate">{session.title || "Conversation"}</span>
                              </button>
                              
                              <button 
                                className={clsx(
                                  "p-1 rounded-full hover:bg-background/50 transition-all shrink-0",
                                  (isActive || isMenuOpen) ? "opacity-100" : "opacity-0 group-hover/item:opacity-100"
                                )}
                                onClick={(e) => {
                                  console.log('3-dots clicked!', session.session_id);
                                  e.stopPropagation();
                                  e.preventDefault();
                                  const rect = e.currentTarget.getBoundingClientRect();
                                  const newPosition = { 
                                    top: rect.bottom + 5, 
                                    left: rect.right + 5  // Position to the right
                                  };
                                  console.log('Menu position:', newPosition);
                                  setMenuPosition(newPosition);
                                  const newMenuId = isMenuOpen ? null : session.session_id;
                                  console.log('Setting activeMenuId to:', newMenuId);
                                  setActiveMenuId(newMenuId);
                                }}
                              >
                                <MoreVertical size={14} />
                              </button>
                            </div>
                          )}
                        </div>
                      );
                    })}
                    
                    {recentSessions.length === 0 && (
                       <div className="px-4 py-2 text-xs text-muted-foreground italic">{t('no_history')}</div>
                    )}
                    
                    {isLoadingMore && (
                      <div className="flex justify-center py-2">
                        <Loader2 className="animate-spin text-muted-foreground" size={16} />
                      </div>
                    )}
                  </>
                )}
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-2 mt-auto space-y-1">

          
          {isOpen && (
            <button 
              onClick={() => setIsSettingsOpen(true)}
              className="w-full flex items-center gap-3 px-4 py-2 rounded-full text-sm text-muted-foreground hover:bg-muted transition-colors"
            >
              <Settings size={20} />
              <span>{t('settings')}</span>
            </button>
          )}
        </div>
      </div>

      {/* Popup Menu - Gemini Style */}
      {activeMenuId && (
        <div 
          className="fixed inset-0 z-[100]"
          onClick={() => {
            console.log('Overlay clicked, closing menu');
            setActiveMenuId(null);
          }}
        >
          <div 
            className="absolute bg-[#2a2b2c] text-white rounded-lg shadow-2xl py-1.5 px-1 min-w-[160px]"
            style={{ 
              top: `${menuPosition.top}px`, 
              left: `${menuPosition.left}px`,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={(e) => {
                console.log('Rename clicked');
                const session = recentSessions.find(s => s.session_id === activeMenuId);
                if (session) {
                  startRename(session, e);
                  setActiveMenuId(null);
                }
              }}
              className="w-full flex items-center gap-2.5 px-3 py-2 text-xs hover:bg-[#3a3b3c] transition-colors text-left rounded-md"
            >
              <Edit2 size={14} />
              <span>{t('rename')}</span>
            </button>
            <button
              onClick={(e) => {
                console.log('Delete clicked');
                e.stopPropagation();
                setDeleteConfirmId(activeMenuId);
                setActiveMenuId(null);
              }}
              className="w-full flex items-center gap-2.5 px-3 py-2 text-xs hover:bg-[#3a3b3c] transition-colors text-left rounded-md"
            >
              <Trash2 size={14} />
              <span>{t('delete')}</span>
            </button>
          </div>
        </div>
      )}
      
      {/* Delete Confirmation Modal - Gemini Style */}
      {deleteConfirmId && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="bg-[#2d2e30] rounded-2xl w-[500px] p-6 shadow-2xl">
            <h3 className="text-xl font-normal text-white mb-4">
              {t('delete_chat_title')}
            </h3>
            <p className="text-sm text-gray-300 mb-6 leading-relaxed">
              {t('delete_chat_confirm')}
            </p>

            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setDeleteConfirmId(null)}
                className="px-6 py-2 text-sm font-medium text-gray-200 hover:bg-white/10 rounded-full transition-colors"
              >
                {t('cancel')}
              </button>
              <button
                onClick={() => confirmDelete(deleteConfirmId)}
                className="px-6 py-2 text-sm font-medium text-white hover:bg-white/10 rounded-full transition-colors"
              >
                {t('delete')}
              </button>
            </div>
          </div>
        </div>
      )}
      
      <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
    </>
  );
}
