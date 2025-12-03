'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';

type Language = 'en' | 'vi';
type Theme = 'light' | 'dark';

interface SettingsContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  theme: Theme;
  setTheme: (theme: Theme) => void;
  t: (key: string) => string;
}

const translations = {
  en: {
    'new_chat': 'New chat',
    'ehr_analysis': 'Knowledge Base',
    'virtual_doctor': 'RAG Processor',
    'medchat_chat': 'MedChat Chat',
    'recent': 'Recent',
    'settings': 'Settings',
    'no_history': 'No recent history',
    'hello': 'Hello, My friend',
    'how_help': 'How can I help you today?',
    'suggestion_1': 'Summarize this patient record',
    'suggestion_2': 'Draft a referral letter',
    'suggestion_3': 'Check drug interactions',
    'suggestion_4': 'Explain latest guidelines',
    'enter_prompt': 'Enter a question here',
    'waiting_analysis': 'Waiting for analysis...',
    'analyzing': 'Analyzing',
    'ready': 'Ready',
    'thinking': 'Thinking',
    'upload_success': '📄 **Document Uploaded**\n\nI am processing the document into the Knowledge Base...',
    'analysis_started': '⏳ **Processing Started**\n\nI am running the RAG pipeline (Split -> OCR -> Embedding)...',
    'upload_fail': '⚠️ Failed to upload document. Please try again.',
    'connection_error': '⚠️ Connection error. Please try again.',
    'disclaimer': 'MedChat may display inaccurate info, including about people, so double-check its responses.',
    'settings_title': 'Settings',
    'language': 'Language',
    'theme': 'Theme',
    'close': 'Close',
    'english': 'English',
    'vietnamese': 'Vietnamese',
    'dark': 'Dark',
    'light': 'Light',
    'gems': 'GEMS',
    'unknown_patient': 'Unknown Patient',
    'active_record': 'Active Record',
    'age': 'Age',
    'status': 'Status',
    'stable': 'Stable',
    'source': 'Source',
    'reasoning_1': 'Analyzing your request...',
    'reasoning_2': 'Consulting medical knowledge...',
    'reasoning_3': 'Reviewing clinical context...',
    'reasoning_4': 'Formulating response...',
    'analyze_button': 'Process to Knowledge Base',
    'uploading_case': 'Uploading document...',
    'analyzing_case': 'Running RAG pipeline...',
    'refining_analysis': 'Finalizing embeddings...',
    'update': 'Update',
    'retry': 'Retry'
  },
  vi: {
    'new_chat': 'Cuộc trò chuyện mới',
    'ehr_analysis': 'Cơ sở tri thức',
    'virtual_doctor': 'Bộ xử lý RAG',
    'medchat_chat': 'Trò chuyện MedChat',
    'recent': 'Gần đây',
    'settings': 'Cài đặt',
    'no_history': 'Không có lịch sử gần đây',
    'hello': 'Xin chào, Bạn của tôi',
    'how_help': 'MedChat có thể giúp gì cho bạn hôm nay?',
    'suggestion_1': 'Tóm tắt hồ sơ bệnh nhân này',
    'suggestion_2': 'Soạn thảo thư giới thiệu',
    'suggestion_3': 'Kiểm tra tương tác thuốc',
    'suggestion_4': 'Giải thích các hướng dẫn mới nhất',
    'enter_prompt': 'Nhập câu hỏi tại đây',
    'waiting_analysis': 'Đang chờ phân tích...',
    'analyzing': 'Đang phân tích',
    'ready': 'Sẵn sàng',
    'thinking': 'Đang suy nghĩ',
    'upload_success': '📄 **Tài liệu đã được tải lên**\n\nTôi đang xử lý tài liệu vào Cơ sở tri thức...',
    'analysis_started': '⏳ **Đã bắt đầu xử lý**\n\nTôi đang chạy quy trình RAG (Tách -> OCR -> Nhúng)...',
    'upload_fail': '⚠️ Tải lên tài liệu thất bại. Vui lòng thử lại.',
    'connection_error': '⚠️ Lỗi kết nối. Vui lòng thử lại.',
    'disclaimer': 'MedChat có thể hiển thị thông tin không chính xác, bao gồm cả về người, vì vậy hãy kiểm tra lại các phản hồi.',
    'settings_title': 'Cài đặt',
    'language': 'Ngôn ngữ',
    'theme': 'Giao diện',
    'close': 'Đóng',
    'english': 'Tiếng Anh',
    'vietnamese': 'Tiếng Việt',
    'dark': 'Tối',
    'light': 'Sáng',
    'gems': 'GEMS',
    'unknown_patient': 'Bệnh nhân chưa rõ',
    'active_record': 'Hồ sơ đang hoạt động',
    'age': 'Tuổi',
    'status': 'Trạng thái',
    'stable': 'Ổn định',
    'source': 'Nguồn',
    'json_upload': 'Tải lên tài liệu',
    'upload_error_type': 'Vui lòng tải lên tệp PDF hợp lệ.',
    'upload_error_format': 'Định dạng tệp không hợp lệ.',
    'file_loaded': 'Tệp đã tải',
    'click_upload': 'Nhấn để tải lên',
    'drag_drop': 'hoặc kéo và thả',
    'json_hint': 'Tài liệu PDF (tối đa 10MB)',
    'thought_for': 'Đã suy nghĩ trong',
    'rename': 'Đổi tên',
    'delete': 'Xóa',
    'delete_chat_title': 'Bạn muốn xóa cuộc trò chuyện?',
    'delete_chat_confirm': 'Thao tác này sẽ xóa các câu lệnh, câu trả lời và ý kiến phản hồi khỏi Hoạt động của bạn trên MedChat, cũng như mọi nội dung bạn đã tạo.',
    'cancel': 'Huỷ',
    'reasoning_1': 'Đang phân tích yêu cầu...',
    'reasoning_2': 'Đang tra cứu kiến thức y khoa...',
    'reasoning_3': 'Đang xem xét ngữ cảnh lâm sàng...',
    'reasoning_4': 'Đang tổng hợp câu trả lời...',
    'analyze_button': 'Xử lý vào Knowledge Base',
    'uploading_case': 'Đang tải lên tài liệu...',
    'analyzing_case': 'Đang chạy quy trình RAG...',
    'refining_analysis': 'Đang hoàn tất...',
    'update': 'Cập nhật',
    'retry': 'Thử lại'
  }
};

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguage] = useState<Language>('en');
  const [theme, setTheme] = useState<Theme>('dark');

  useEffect(() => {
    // Load from local storage
    const savedLang = localStorage.getItem('medchat_lang') as Language;
    const savedTheme = localStorage.getItem('medchat_theme') as Theme;
    if (savedLang) setLanguage(savedLang);
    if (savedTheme) setTheme(savedTheme);
    else {
        // Default to dark if no preference
        setTheme('dark');
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('medchat_lang', language);
  }, [language]);

  useEffect(() => {
    localStorage.setItem('medchat_theme', theme);
    const root = window.document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(theme);
  }, [theme]);

  const t = (key: string) => {
    return translations[language][key as keyof typeof translations['en']] || key;
  };

  return (
    <SettingsContext.Provider value={{ language, setLanguage, theme, setTheme, t }}>
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
