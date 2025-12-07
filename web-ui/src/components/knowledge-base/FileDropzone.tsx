import React, { useCallback, useState } from 'react';
import { Upload, FileJson, X, CheckCircle } from 'lucide-react';
import { clsx } from 'clsx';
import { useTranslation } from 'react-i18next';

interface FileDropzoneProps {
  onFileLoaded: (data: any) => void;
  disabled?: boolean;
}

export function FileDropzone({ onFileLoaded, disabled }: FileDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { t } = useTranslation('common');

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) setIsDragging(true);
  }, [disabled]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const processFile = useCallback((file: File) => {
    if (file.type !== 'application/pdf' && !file.name.endsWith('.pdf')) {
      setError(t('knowledgeBase.upload_error_type'));
      return;
    }

    // For PDF, we just pass the file object up, we don't read it as text
    setFileName(file.name);
    setError(null);
    onFileLoaded(file); // Pass the File object directly
  }, [onFileLoaded, t]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (disabled) return;

    const file = e.dataTransfer.files[0];
    if (file) processFile(file);
  }, [disabled, processFile]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  }, [processFile]);

  if (fileName) {
    return (
      <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4 flex items-center justify-between animate-in fade-in slide-in-from-top-2">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-emerald-500/20 text-emerald-500 rounded-full flex items-center justify-center">
            <FileJson size={20} />
          </div>
          <div>
            <div className="font-medium text-sm text-emerald-500">{t('knowledgeBase.file_loaded')}</div>
            <div className="text-xs text-muted-foreground">{fileName}</div>
          </div>
        </div>
        <button 
          onClick={() => { setFileName(null); onFileLoaded(null); }}
          className="p-2 hover:bg-emerald-500/20 rounded-full text-emerald-500 transition-colors"
        >
          <X size={16} />
        </button>
      </div>
    );
  }

  return (
    <div className="w-full">
      <label
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={clsx(
          "relative flex flex-col items-center justify-center w-full h-48 border-2 border-dashed rounded-xl cursor-pointer transition-all duration-200",
          isDragging 
            ? "border-primary bg-primary/5 scale-[1.02]" 
            : "border-border bg-secondary/30 hover:bg-secondary/50 hover:border-primary/50",
          disabled && "opacity-50 cursor-not-allowed"
        )}
      >
        <div className="flex flex-col items-center justify-center pt-5 pb-6 text-center px-4">
          <div className={clsx(
            "w-12 h-12 rounded-full flex items-center justify-center mb-3 transition-colors",
            isDragging ? "bg-primary/20 text-primary" : "bg-secondary text-muted-foreground"
          )}>
            <Upload size={24} />
          </div>
          <p className="mb-1 text-sm font-medium text-foreground">
            <span className="font-semibold text-primary">{t('knowledgeBase.click_upload')}</span> {t('knowledgeBase.drag_drop')}
          </p>
          <p className="text-xs text-muted-foreground">
            {t('knowledgeBase.json_hint')}
          </p>
        </div>
        <input 
          type="file" 
          className="hidden" 
          accept=".pdf"
          onChange={handleFileInput}
          disabled={disabled}
        />
      </label>
      {error && (
        <div className="mt-2 text-xs text-destructive flex items-center gap-1">
          <X size={12} /> {error}
        </div>
      )}
    </div>
  );
}
