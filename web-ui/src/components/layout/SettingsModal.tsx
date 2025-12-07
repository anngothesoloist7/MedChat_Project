'use client';

import React from 'react';
import { X, Moon, Sun, Globe } from 'lucide-react';
import { clsx } from 'clsx';
import { createPortal } from 'react-dom';
import { useSettings } from '@/context/SettingsContext';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const { language, setLanguage, theme, setTheme, t } = useSettings();
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
    return () => setMounted(false);
  }, []);

  if (!isOpen || !mounted) return null;

  const portalRoot = typeof document !== 'undefined' ? document.body : null;
  if (!portalRoot) return null;

  return createPortal(
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4" onClick={(e) => e.stopPropagation()}>
      <div className="bg-secondary text-secondary-foreground rounded-2xl w-full max-w-[400px] p-6 shadow-2xl border border-border">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-normal text-foreground">{t('settings.title')}</h2>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-muted rounded-full transition-colors text-muted-foreground hover:text-foreground"
          >
            <X size={20} />
          </button>
        </div>

        <div className="space-y-6">
          {/* Language Setting */}
          <div className="space-y-3">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <Globe size={14} />
              {t('settings.language')}
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => {
                    console.log('Switching to English');
                    setLanguage('en');
                }}
                className={clsx(
                  "px-4 py-2.5 rounded-lg text-sm font-medium transition-all border",
                  language === 'en'
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-transparent text-muted-foreground border-border hover:bg-muted"
                )}
              >
                {t('settings.english')}
              </button>
              <button
                onClick={() => {
                    console.log('Switching to Vietnamese');
                    setLanguage('vi');
                }}
                className={clsx(
                  "px-4 py-2.5 rounded-lg text-sm font-medium transition-all border",
                  language === 'vi'
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-transparent text-muted-foreground border-border hover:bg-muted"
                )}
              >
                {t('settings.vietnamese')}
              </button>
            </div>
          </div>

          {/* Theme Setting */}
          <div className="space-y-3">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <Moon size={14} />
              {t('settings.theme')}
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => setTheme('light')}
                className={clsx(
                  "px-4 py-2.5 rounded-lg text-sm font-medium transition-all border flex items-center justify-center gap-2",
                  theme === 'light'
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-transparent text-muted-foreground border-border hover:bg-muted"
                )}
              >
                <Sun size={16} />
                {t('settings.light')}
              </button>
              <button
                onClick={() => setTheme('dark')}
                className={clsx(
                  "px-4 py-2.5 rounded-lg text-sm font-medium transition-all border flex items-center justify-center gap-2",
                  theme === 'dark'
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-transparent text-muted-foreground border-border hover:bg-muted"
                )}
              >
                <Moon size={16} />
                {t('settings.dark')}
              </button>
            </div>
          </div>
        </div>

        <div className="mt-8 flex justify-end">
                <button
                onClick={() => onClose()} 
                className="px-6 py-2 bg-muted text-muted-foreground hover:bg-muted/80 rounded-full text-sm font-medium transition-colors"
                >
                {t('settings.close')}
              </button>
        </div>
      </div>
    </div>,
    portalRoot
  );
}
