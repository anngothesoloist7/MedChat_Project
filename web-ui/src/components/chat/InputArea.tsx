import React, { useState, useRef, useEffect, forwardRef, useImperativeHandle } from 'react';
import { Send, Plus, Mic, Image as ImageIcon, ArrowUpIcon } from 'lucide-react';
import { clsx } from 'clsx';
import { useTranslation } from 'react-i18next';
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
  InputGroupTextarea, // Using our new component
} from "@/components/ui/input-group"

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
  const { t } = useTranslation('common');

  useImperativeHandle(ref, () => ({
    focus: () => {
      textareaRef.current?.focus();
    }
  }));

  useEffect(() => {
    if (textareaRef.current) {
        // Auto-resize logic remains
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
        {/* Modern v4 InputGroup Style */}
        <InputGroup className="bg-secondary rounded-[28px] pl-4 pr-1 py-1 h-auto items-end shadow-sm border-transparent hover:border-input focus-within:border-ring transition-all">
            <InputGroupTextarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={placeholder || t('chat.placeholder')}
                disabled={disabled}
                rows={1}
                className="min-h-[44px] max-h-[200px] py-3 text-base"
                style={{ height: '44px' }} // Initial height
            />
            
            <InputGroupAddon align="inline-end" className="pb-1.5 h-full items-end">
                {/* Additional Actions */}
                 <InputGroupButton size="icon-sm" className="rounded-full text-muted-foreground hover:bg-background/50 hover:text-foreground">
                    <ImageIcon size={18} />
                 </InputGroupButton>
                 <InputGroupButton size="icon-sm" className="rounded-full text-muted-foreground hover:bg-background/50 hover:text-foreground">
                     <Mic size={18} />
                 </InputGroupButton>

                {input.trim() && (
                    <InputGroupButton
                        onClick={handleSend}
                        disabled={disabled}
                        size="icon-sm"
                        className="rounded-full bg-foreground text-background hover:bg-foreground/90 transition-colors ml-1"
                    >
                        <ArrowUpIcon size={18} />
                    </InputGroupButton>
                )}
            </InputGroupAddon>
        </InputGroup>

      <div className="text-center mt-2 text-[11px] text-muted-foreground">
        {t('chat.disclaimer', "AI can make mistakes. Please verify important information.")}
      </div>
    </div>
  );
});

InputArea.displayName = 'InputArea';

