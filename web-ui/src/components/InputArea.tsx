import React, { useState, useRef, useEffect, forwardRef, useImperativeHandle } from 'react';
import { Send, Plus, Mic, Image as ImageIcon } from 'lucide-react';
import { clsx } from 'clsx';
import { useSettings } from '@/context/SettingsContext';

export interface InputAreaRef {
  focus: () => void;
}

interface InputAreaProps {
  onSend: (text: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export const InputArea = forwardRef<InputAreaRef, InputAreaProps>(({ onSend, disabled, placeholder }, ref) => {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { t } = useSettings();

  useImperativeHandle(ref, () => ({
    focus: () => {
      textareaRef.current?.focus();
    }
  }));

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = () => {
    if (input.trim() && !disabled) {
      onSend(input);
      setInput('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto px-4">
      <div className={clsx(
        "relative flex items-end gap-2 p-3 rounded-[28px] transition-colors border border-transparent",
        "bg-secondary hover:bg-muted focus-within:bg-secondary"
      )}>
        


        <div className="flex-1 relative flex items-center">
           <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder || t('enter_prompt')}
            disabled={disabled}
            rows={1}
            className="w-full bg-transparent text-foreground placeholder-muted-foreground resize-none focus:outline-none py-2 max-h-[200px] border-none focus:ring-0 pl-2"
            style={{ minHeight: '24px' }}
          />
        </div>

        <div className="flex items-center gap-1 flex-shrink-0 mb-0.5">
           <button className="p-2 text-muted-foreground hover:text-foreground hover:bg-background rounded-full transition-colors">
             <ImageIcon size={20} />
           </button>
           <button className="p-2 text-muted-foreground hover:text-foreground hover:bg-background rounded-full transition-colors">
             <Mic size={20} />
           </button>
           {input.trim() && (
              <button 
                onClick={handleSend}
                disabled={disabled}
                className="p-2 bg-foreground text-background rounded-full hover:opacity-90 transition-opacity"
              >
                <Send size={18} />
              </button>
           )}
        </div>
      </div>
      <div className="text-center mt-2 text-[11px] text-muted-foreground">
        {t('disclaimer')}
      </div>
    </div>
  );
});

InputArea.displayName = 'InputArea';
