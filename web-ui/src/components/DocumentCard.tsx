import React from 'react';
import { FileText, CheckCircle2, Sparkles, Loader2, Trash2, FileType, Clock } from 'lucide-react';
import { FileDropzone } from './FileDropzone';
import { useSettings } from '@/context/SettingsContext';

interface DocumentCardProps {
  data: any;
  onFileLoaded: (data: any) => void;
  onAnalyze?: () => void;
  onDelete?: () => void;
  status?: string;
  isAnalyzing?: boolean;
}

export function DocumentCard({ data, onFileLoaded, onAnalyze, onDelete, status, isAnalyzing }: DocumentCardProps) {
  const { t } = useSettings();

  if (!data) {
    return (
      <div className="mb-6">
        <FileDropzone onFileLoaded={onFileLoaded} />
      </div>
    );
  }

  // Data is now a File object
  const fileName = data.name || "Document";
  const fileSize = data.size ? `${(data.size / 1024 / 1024).toFixed(2)} MB` : "";
  const lastModified = data.lastModified ? new Date(data.lastModified).toLocaleDateString() : new Date().toLocaleDateString();

  return (
    <div className="bg-[#1e1e1e] rounded-xl p-6 mb-6 animate-in fade-in slide-in-from-top-4 border border-white/5 shadow-xl">
      <div className="flex items-start justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 bg-red-500/10 text-red-500 rounded-2xl flex items-center justify-center border border-red-500/20 shadow-sm">
            <FileText size={28} />
          </div>
          <div>
            <h3 className="font-semibold text-lg text-foreground mb-1">{fileName}</h3>
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <span className="flex items-center gap-1 bg-white/5 px-2 py-0.5 rounded-md">
                <FileType size={10} /> PDF
              </span>
              <span>•</span>
              <span>{fileSize}</span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <Clock size={10} /> {lastModified}
              </span>
            </div>
          </div>
        </div>
        
        <div className="flex flex-col items-end gap-2">
           {status === t('ready') && (
             <span className="px-3 py-1 bg-emerald-500/10 text-emerald-400 text-xs font-medium rounded-full border border-emerald-500/20 flex items-center gap-1.5 shadow-sm">
               <CheckCircle2 size={12} />
               {t('ready')}
             </span>
           )}
        </div>
      </div>

      {/* Uploading/Processing Animation */}
      {isAnalyzing && (
        <div className="mb-6 space-y-2">
          <div className="flex justify-between text-xs text-muted-foreground">
             <span className="flex items-center gap-1.5">
                <Loader2 size={12} className="animate-spin text-blue-400" />
                Processing document...
             </span>
             <span className="animate-pulse">Running RAG Pipeline...</span>
          </div>
          <div className="h-1.5 w-full bg-secondary/50 rounded-full overflow-hidden">
             <div className="h-full bg-gradient-to-r from-blue-500 via-purple-500 to-blue-500 w-full animate-progress-indeterminate rounded-full" />
          </div>
        </div>
      )}

      {onAnalyze && !status && !isAnalyzing && (
        <div className="flex justify-end mt-2 gap-3">
          {onDelete && (
            <button
              onClick={onDelete}
              className="flex items-center justify-center w-10 h-10 bg-[#2a2a2a] hover:bg-[#3a3a3a] text-muted-foreground hover:text-red-400 rounded-full transition-all duration-200 hover:scale-105"
              title={t('delete')}
            >
              <Trash2 size={18} />
            </button>
          )}
          <button
            onClick={onAnalyze}
            className="flex items-center gap-2 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white px-6 py-2.5 rounded-full text-sm font-medium transition-all duration-200 shadow-lg hover:shadow-blue-500/20 hover:scale-[1.02]"
          >
            <Sparkles size={16} />
            {t('analyze_button')}
          </button>
        </div>
      )}
    </div>
  );
}
