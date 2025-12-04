'use client';

import React from 'react';
import { X, Moon, Sun, Globe } from 'lucide-react';
import { useSettings } from '@/context/SettingsContext';
import { clsx } from 'clsx';

import { createPortal } from 'react-dom';

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
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-[#1e1f20] text-white rounded-2xl w-full max-w-[400px] p-6 shadow-2xl border border-[#3c4043]">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-normal">Settings</h2>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-[#3c4043] rounded-full transition-colors text-gray-400 hover:text-white"
          >
            <X size={20} />
          </button>
        </div>

        <div className="space-y-6">
          {/* Language Setting */}
          <div className="space-y-3">
            <label className="text-xs font-medium text-gray-400 uppercase tracking-wider flex items-center gap-2">
              <Globe size={14} />
              LANGUAGE
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => setLanguage('en')}
                className={clsx(
                  "px-4 py-2.5 rounded-lg text-sm font-medium transition-all border",
                  language === 'en'
                    ? "bg-[#1a73e8] text-white border-[#1a73e8]"
                    : "bg-transparent text-gray-300 border-[#5f6368] hover:bg-[#3c4043]"
                )}
              >
                English
              </button>
              <button
                onClick={() => setLanguage('vi')}
                className={clsx(
                  "px-4 py-2.5 rounded-lg text-sm font-medium transition-all border",
                  language === 'vi'
                    ? "bg-[#1a73e8] text-white border-[#1a73e8]"
                    : "bg-transparent text-gray-300 border-[#5f6368] hover:bg-[#3c4043]"
                )}
              >
                Vietnamese
              </button>
            </div>
          </div>

          {/* Theme Setting */}
          <div className="space-y-3">
            <label className="text-xs font-medium text-gray-400 uppercase tracking-wider flex items-center gap-2">
              <Moon size={14} />
              THEME
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => setTheme('light')}
                className={clsx(
                  "px-4 py-2.5 rounded-lg text-sm font-medium transition-all border flex items-center justify-center gap-2",
                  theme === 'light'
                    ? "bg-[#1a73e8] text-white border-[#1a73e8]"
                    : "bg-transparent text-gray-300 border-[#5f6368] hover:bg-[#3c4043]"
                )}
              >
                <Sun size={16} />
                Light
              </button>
              <button
                onClick={() => setTheme('dark')}
                className={clsx(
                  "px-4 py-2.5 rounded-lg text-sm font-medium transition-all border flex items-center justify-center gap-2",
                  theme === 'dark'
                    ? "bg-[#1a73e8] text-white border-[#1a73e8]"
                    : "bg-transparent text-gray-300 border-[#5f6368] hover:bg-[#3c4043]"
                )}
              >
                <Moon size={16} />
                Dark
              </button>
            </div>
          </div>
        </div>

        <div className="mt-8 flex justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2 bg-[#e8eaed] hover:bg-[#d2e3fc] text-[#1f1f1f] rounded-full text-sm font-medium transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>,
    portalRoot
  );
}
