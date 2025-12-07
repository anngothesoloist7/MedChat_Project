import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import rehypeRaw from "rehype-raw";
import "katex/dist/katex.min.css";
import {
  Copy,
  Check,
  Volume2,
  ThumbsUp,
  ThumbsDown,
  RefreshCw,
  MoreVertical,
  Sparkles,
  X,
  Send,
  Pencil,
} from "lucide-react";
import { motion } from "framer-motion";
import { clsx } from "clsx";
import { useTranslation } from 'react-i18next';

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  thinkingTime?: number;
  shouldAnimate?: boolean;
}

interface MessageBubbleProps {
  message: Message;
  onStreamUpdate?: () => void;
  onEdit?: (messageId: string, newContent: string) => void;
  isLastUserMessage?: boolean;
}

export function MessageBubble({
  message,
  onStreamUpdate,
  onEdit,
  isLastUserMessage,
}: MessageBubbleProps) {
  const isUser = message.role === "user";
  const [copied, setCopied] = useState(false);
  const { t } = useTranslation('common');
  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState(message.content);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [isThoughtOpen, setIsThoughtOpen] = useState(false);

  // Parse Thought Block and Main Content
  const { thought, mainContent } = React.useMemo(() => {
    if (isUser) return { thought: null, mainContent: message.content };

    // Pattern 1: "Thought for X s\n..."
    const thoughtRegex = /^Thought for ([\d\.]+)s\s*\n([\s\S]*?)(\n\n|$)/;
    const match = message.content.match(thoughtRegex);
    if (match) {
      return {
        thought: { duration: parseFloat(match[1]).toFixed(1), text: match[2].trim() },
        mainContent: message.content.substring(match[0].length).trim()
      };
    }

    // Pattern 2: <thought> tags
    const tagMatch = message.content.match(/<thought>([\s\S]*?)<\/thought>/);
    if (tagMatch) {
      return {
        thought: { duration: null, text: tagMatch[1].trim() },
        mainContent: message.content.replace(tagMatch[0], "").trim()
      };
    }

    return { thought: null, mainContent: message.content };
  }, [message.content, isUser]);

  const preprocessContent = (text: string) => {
    // 1. Unescape HTML tags (e.g. \<sup\> -> <sup>)
    let cleanText = text.replace(/\\<(\/?\w+)\\>/g, "<$1>");

    // 2. Fix Google Search links to be internal anchors
    // Pattern: [1](https://www.google.com/search?q=%23ref1) -> [1](#ref1)
    cleanText = cleanText.replace(
      /\(https:\/\/www\.google\.com\/search\?q=%23(ref[\w-]+)\)/g,
      "(#$1)"
    );

    // 3. Wrap references in a container for highlighting AND fix markdown inside it
    // Because wrapping in <div> disables markdown parsing for that block, we manually convert basic markdown to HTML
    cleanText = cleanText.replace(
      /(<a id="(ref[\w-]+)">\d+\.<\/a>[\s\S]*?)(?=(?:<a id="ref)|$)/g,
      (match, content, refId) => {
        let htmlContent = content;
        // Bold
        htmlContent = htmlContent.replace(
          /\*\*([^*]+)\*\*/g,
          "<strong>$1</strong>"
        );
        // Italic
        htmlContent = htmlContent.replace(
          /(?<!\*)\*([^*]+)\*(?!\*)/g,
          "<em>$1</em>"
        );

        // Ensure the container wraps the entire content including the anchor
        return `<div id="container-${refId}" class="p-1 rounded transition-colors duration-500 block w-full">${htmlContent}</div>`;
      }
    );

    return cleanText;
  };

  // Extract citations map: { ref1: "Content...", ref2: "Content..." }
  const citations = React.useMemo(() => {
    const map: Record<string, string> = {};
    // Regex to find <a id="refX">X.</a> Content...
    // We assume the content ends at the next tag or double newline
    const regex =
      /<a id="(ref[\w-]+)">\d+\.<\/a>\s*([\s\S]*?)(?=(?:<a id="ref)|$)/g;

    let match;
    // We update to parse mainContent to avoid picking up stuff from thought block if any
    while ((match = regex.exec(mainContent)) !== null) {
      const id = match[1];
      let text = match[2].trim();
      // Cleanup any trailing HTML tags if they were captured (like <br> or </div>)
      text = text.replace(/<[^>]*>$/, "").trim();
      map[id] = text;
    }
    return map;
  }, [mainContent]);

  const [displayedContent, setDisplayedContent] = useState(
    message.shouldAnimate && !isUser ? "" : preprocessContent(mainContent)
  );

  useEffect(() => {
    // If we're not streaming or it's user, show full content immediately
    if (!message.shouldAnimate || isUser) {
      setDisplayedContent(preprocessContent(mainContent));
      return;
    }

    let index = 0;
    const text = preprocessContent(mainContent);

    // If text is already fully displayed (e.g. re-render), don't restart
    if (displayedContent === text) return;

    const intervalId = setInterval(() => {
      if (index < text.length) {
        // Consistent smooth streaming: ~300 chars/sec
        const chunkSize = 3;
        const nextIndex = Math.min(index + chunkSize, text.length);
        setDisplayedContent(text.slice(0, nextIndex));
        index = nextIndex;
        if (onStreamUpdate) onStreamUpdate();
      } else {
        clearInterval(intervalId);
      }
    }, 10); // 10ms interval

    return () => clearInterval(intervalId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mainContent, message.shouldAnimate, isUser]);

  useEffect(() => {
    if (isEditing && textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
      textareaRef.current.focus();
    }
  }, [isEditing, editText]);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleUpdate = () => {
    if (editText.trim() !== message.content) {
      onEdit?.(message.id, editText);
    }
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleUpdate();
    }
    if (e.key === "Escape") {
      setIsEditing(false);
      setEditText(message.content);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={clsx(
        "flex w-full max-w-3xl mx-auto mb-6",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      <div
        className={clsx(
          "flex flex-col",
          isUser && !isEditing ? "max-w-[85%] items-end" : "w-full items-start"
        )}
      >
        {/* Thinking Block */}
        {!isUser && thought && (
          <div className="mb-3">
             <button 
                onClick={() => setIsThoughtOpen(!isThoughtOpen)}
                className="flex items-center gap-2 text-muted-foreground hover:text-foreground text-sm pl-0 group transition-colors focus:outline-none"
                title={isThoughtOpen ? "Hide reasoning" : "Show reasoning"}
             >
                <Sparkles size={16} className={clsx("text-blue-400 fill-blue-400/20 transition-all duration-300", isThoughtOpen ? "scale-110" : "scale-100")} />
                <span className="font-medium bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                  {t("thought_for") || "Thought for"} {thought.duration ? `${thought.duration}s` : "..."}
                </span>
             </button>
             
             {isThoughtOpen && (
                 <motion.div 
                    initial={{ opacity: 0, height: 0 }} 
                    animate={{ opacity: 1, height: "auto" }}
                    className="mt-2 pl-4 border-l-2 border-primary/20 overflow-hidden"
                 >
                     <div className="py-2 text-sm text-muted-foreground/90 italic whitespace-pre-wrap font-serif leading-relaxed bg-muted/30 p-3 rounded-r-lg">
                         {thought.text}
                     </div>
                 </motion.div>
             )}
          </div>
        )}
        
        {/* Fallback for simple 'Thinking Time' if no detailed thought provided in text but exists in metadata */}
        {!isUser && !thought && message.thinkingTime && (
            <div className="flex items-center gap-2 mb-2 text-muted-foreground text-sm pl-0">
                <Sparkles size={16} className="text-blue-400 fill-blue-400/20" />
                <span>
                    {t("thought_for") || "Thought for"} {message.thinkingTime}s
                </span>
            </div>
        )}

        {/* Message Content */}
        {isEditing ? (
          <div className="w-full bg-secondary rounded-[20px] p-2">
            <textarea
              ref={textareaRef}
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              onKeyDown={handleKeyDown}
              className="w-full bg-transparent text-foreground p-3 resize-none focus:outline-none text-[15px] leading-relaxed"
              rows={1}
            />
            <div className="flex justify-end gap-2 mt-2 px-2 pb-1">
              <button
                onClick={() => {
                  setIsEditing(false);
                  setEditText(message.content);
                }}
                className="px-3 py-1.5 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-background/50 rounded-full transition-colors"
              >
                {t('cancel')}
              </button>
              <button
                onClick={handleUpdate}
                className="px-3 py-1.5 text-sm font-medium bg-foreground text-background rounded-full hover:opacity-90 transition-opacity"
              >
                {editText.trim() === message.content ? t('retry') : t('update')}
              </button>
            </div>
          </div>
        ) : (
          <div className="relative group/message">
            <div
              className={clsx(
                "text-[15px] leading-relaxed",
                isUser
                  ? "px-5 py-3.5 bg-primary text-primary-foreground rounded-[20px]"
                  : "text-foreground pl-0 w-full"
              )}
            >
              <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkMath]}
                rehypePlugins={[rehypeKatex, rehypeRaw]}
                components={{
                  p: ({ node, ...props }) => (
                    <p
                      className="mb-3 last:mb-0 leading-7 text-foreground/90"
                      {...props}
                    />
                  ),
                  ul: ({ node, ...props }) => (
                    <ul
                      className="list-disc pl-6 mb-4 space-y-1 text-foreground/90"
                      {...props}
                    />
                  ),
                  ol: ({ node, ...props }) => (
                    <ol
                      className="list-decimal pl-6 mb-4 space-y-1 text-foreground/90"
                      {...props}
                    />
                  ),
                  li: ({ node, ...props }) => (
                    <li
                      className="pl-1 marker:text-muted-foreground"
                      {...props}
                    />
                  ),
                  strong: ({ node, ...props }) => (
                    <strong
                      className="font-semibold text-foreground"
                      {...props}
                    />
                  ),
                  h1: ({ node, ...props }) => (
                    <h1
                      className="text-2xl font-bold mb-4 mt-6 text-foreground border-b border-border pb-2"
                      {...props}
                    />
                  ),
                  h2: ({ node, ...props }) => (
                    <h2
                      className="text-xl font-bold mb-3 mt-5 text-foreground"
                      {...props}
                    />
                  ),
                  h3: ({ node, ...props }) => (
                    <h3
                      className="text-lg font-semibold mb-2 mt-4 text-foreground"
                      {...props}
                    />
                  ),
                  h4: ({ node, ...props }) => (
                    <h4
                      className="text-base font-semibold mb-2 mt-4 text-foreground"
                      {...props}
                    />
                  ),
                  code: ({ node, ...props }) => {
                    const { className, children } = props;
                    const match = /language-(\w+)/.exec(className || "");
                    const isInline = !match && !String(children).includes("\n");
                    return isInline ? (
                      <code
                        className="bg-muted px-1.5 py-0.5 rounded text-sm font-mono text-primary"
                        {...props}
                      />
                    ) : (
                      <div className="my-4 rounded-lg overflow-hidden border border-border bg-muted/50">
                        <div className="bg-muted px-4 py-2 text-xs text-muted-foreground border-b border-border flex justify-between items-center">
                          <span>{match?.[1] || "text"}</span>
                        </div>
                        <code
                          className="block p-4 text-sm font-mono overflow-x-auto text-foreground bg-transparent"
                          {...props}
                        />
                      </div>
                    );
                  },
                  pre: ({ node, ...props }) => (
                    <pre className="bg-transparent p-0 m-0" {...props} />
                  ),
                  blockquote: ({ node, ...props }) => (
                    <blockquote
                      className="border-l-4 border-primary/40 pl-4 italic my-4 text-muted-foreground bg-muted/20 py-2 pr-2 rounded-r"
                      {...props}
                    />
                  ),
                  a: ({ node, ...props }) => {
                    const href = props.href || "";
                    const elementId = props.id || "";

                    // Handle Citation Link: [1] -> #ref1
                    if (href.startsWith("#ref")) {
                      const refId = href.substring(1);
                      const citationText = citations[refId];

                      if (citationText) {
                        return (
                          <span className="relative inline-block group">
                            <a
                              href={href}
                              onClick={(e) => {
                                e.preventDefault();
                                // Try to find the container first, fallback to the anchor itself
                                const element =
                                  document.getElementById(
                                    `container-${refId}`
                                  ) || document.getElementById(refId);
                                if (element) {
                                  element.scrollIntoView({
                                    behavior: "smooth",
                                    block: "center",
                                  });
                                  // Highlight effect
                                  element.classList.add(
                                    "bg-blue-500/20",
                                    "transition-colors",
                                    "duration-500"
                                  );
                                  setTimeout(() => {
                                    element.classList.remove(
                                      "bg-blue-500/20"
                                    );
                                  }, 2000);
                                }
                              }}
                              className="text-blue-600 hover:text-blue-700 hover:underline font-bold cursor-pointer"
                              {...props}
                            />
                            {/* Hover Card */}
                            <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-3 bg-zinc-800 text-zinc-100 text-xs rounded-lg shadow-xl border border-zinc-700 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 block">
                              <span className="font-semibold mb-1 block">
                                Citation {props.children}
                              </span>
                              <span className="line-clamp-4 text-zinc-300 block">
                                <ReactMarkdown
                                  components={{
                                    p: ({ node, ...props }) => (
                                      <span {...props} />
                                    ),
                                  }}
                                >
                                  {citationText}
                                </ReactMarkdown>
                              </span>
                              {/* Arrow */}
                              <span className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-zinc-800 block"></span>
                            </span>
                          </span>
                        );
                      }
                    }

                    // Handle Reference Anchor: <a id="ref1">
                    if (elementId.startsWith("ref") && !href) {
                      return (
                        <a
                          className="text-foreground no-underline cursor-default"
                          {...props}
                        />
                      );
                    }

                    return (
                      <a
                        className="text-primary hover:underline font-medium"
                        target="_blank"
                        rel="noopener noreferrer"
                        {...props}
                      />
                    );
                  },
                  table: ({ node, ...props }) => (
                    <div className="overflow-x-auto my-4 rounded-lg border border-border">
                      <table
                        className="min-w-full divide-y divide-border"
                        {...props}
                      />
                    </div>
                  ),
                  th: ({ node, ...props }) => (
                    <th
                      className="px-4 py-3 bg-muted text-left text-xs font-medium text-muted-foreground uppercase tracking-wider"
                      {...props}
                    />
                  ),
                  td: ({ node, ...props }) => (
                    <td
                      className="px-4 py-3 text-sm text-foreground border-t border-border align-top"
                      {...props}
                    />
                  ),
                }}
              >
                {displayedContent}
              </ReactMarkdown>
            </div>

            {/* User Action Bar (Copy/Edit) */}
            {isUser && !isEditing && (
              <div
                className={clsx(
                  "absolute top-1/2 -translate-y-1/2 opacity-0 group-hover/message:opacity-100 transition-opacity flex gap-1",
                  isLastUserMessage ? "-left-20" : "-left-10"
                )}
              >
                <button
                  onClick={handleCopy}
                  className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded-full transition-colors"
                  title="Copy"
                >
                  {copied ? <Check size={14} /> : <Copy size={14} />}
                </button>
                {isLastUserMessage && (
                  <button
                    onClick={() => setIsEditing(true)}
                    className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded-full transition-colors"
                    title="Edit"
                  >
                    <Pencil size={14} />
                  </button>
                )}
              </div>
            )}
          </div>
        )}

        {/* AI Action Bar */}
        {!isUser && (
          <div className="flex items-center gap-1 mt-1 pl-0">
            <button
              onClick={handleCopy}
              className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded-full transition-colors"
              title="Copy"
            >
              {copied ? <Check size={16} /> : <Copy size={16} />}
            </button>
            <button className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded-full transition-colors">
              <ThumbsUp size={16} />
            </button>
            <button className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded-full transition-colors">
              <ThumbsDown size={16} />
            </button>
            <button className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded-full transition-colors">
              <MoreVertical size={16} />
            </button>
          </div>
        )}
      </div>
    </motion.div>
  );
}
