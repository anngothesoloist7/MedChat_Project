'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'next-themes';
import '@/lib/i18n'; // Ensure i18n is initialized

type Language = 'en' | 'vi';
type Theme = 'light' | 'dark';

interface SettingsContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  theme: Theme;
  setTheme: (theme: Theme) => void;
  t: (key: string) => string;
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const { t, i18n } = useTranslation('common');
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const setLanguage = (lang: Language) => {
    i18n.changeLanguage(lang);
    localStorage.setItem('medchat_lang', lang);
  };

  // Sync initial language from localStorage or default
  useEffect(() => {
    const savedLang = localStorage.getItem('medchat_lang') as Language;
    if (savedLang && i18n.language !== savedLang) {
       i18n.changeLanguage(savedLang);
    }
  }, [i18n]);

  const currentTheme = (mounted ? (theme === 'system' ? resolvedTheme : theme) : 'dark') as Theme;

  // Wrapper for setTheme to strip 'system' if needed or just pass through
  const handleSetTheme = (newTheme: Theme) => {
    setTheme(newTheme);
  };

  return (
    <SettingsContext.Provider 
        value={{ 
            language: (i18n.language as Language) || 'en', 
            setLanguage, 
            theme: currentTheme || 'dark', 
            setTheme: handleSetTheme, 
            t 
        }}
    >
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  const context = useContext(SettingsContext);
  if (context === undefined) {
    throw new Error('useSettings must be used within a SettingsProvider');
  }
  return context;
}
