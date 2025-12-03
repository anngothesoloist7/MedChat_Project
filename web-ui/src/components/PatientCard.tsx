import React from 'react';
import { User, Activity, Calendar, FileJson, CheckCircle2, Sparkles, Loader2, Trash2 } from 'lucide-react';
import { FileDropzone } from './FileDropzone';
import { useSettings } from '@/context/SettingsContext';

interface PatientCardProps {
  data: any;
  onFileLoaded: (data: any) => void;
  onAnalyze?: () => void;
  onDelete?: () => void;
  status?: string;
  isAnalyzing?: boolean;
}

export function PatientCard({ data, onFileLoaded, onAnalyze, onDelete, status, isAnalyzing }: PatientCardProps) {
  const { t } = useSettings();

  if (!data) {
    return (
      <div className="mb-6">
        <FileDropzone onFileLoaded={onFileLoaded} />
      </div>
    );
  }

  // Data is now a File object or similar
  const fileName = data.name || "Document";
  const fileSize = data.size ? `${(data.size / 1024 / 1024).toFixed(2)} MB` : "";

  return (
    <div className="bg-[#1e1e1e] rounded-xl p-5 mb-6 animate-in fade-in slide-in-from-top-4">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-500/20 text-blue-400 rounded-full flex items-center justify-center">
            <FileJson size={20} />
          </div>
          <div>
            <h3 className="font-semibold text-foreground">{fileName}</h3>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span>{fileSize}</span>
              {status && (
                <>
                  <span>•</span>
                  <span className="uppercase tracking-wider font-semibold text-emerald-400">{status}</span>
                </>
              )}
            </div>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          {status === t('ready') ? (
             <span className="px-2 py-1 bg-emerald-500/10 text-emerald-400 text-xs font-medium rounded-full border border-emerald-500/20 flex items-center gap-1">
               <CheckCircle2 size={10} />
               {t('ready')}
             </span>
          ) : (
             <span className="px-2 py-1 bg-blue-500/10 text-blue-400 text-xs font-medium rounded-full border border-blue-500/20 flex items-center gap-1">
               <Activity size={10} />
               {t('file_loaded')}
             </span>
          )}
        </div>
      </div>

      {onAnalyze && !status && (
        <div className="flex justify-end mt-4 gap-2">
          {onDelete && (
            <button
              onClick={onDelete}
              className="flex items-center justify-center w-9 h-9 bg-[#2a2a2a] hover:bg-[#3a3a3a] text-muted-foreground hover:text-red-400 rounded-full transition-colors"
              title={t('delete')}
            >
              <Trash2 size={16} />
            </button>
          )}
          <button
            onClick={onAnalyze}
            disabled={isAnalyzing}
            className="flex items-center gap-2 bg-[#2a2a2a] hover:bg-[#3a3a3a] text-white px-4 py-2 rounded-full text-sm font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isAnalyzing ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Sparkles size={16} />
            )}
            {isAnalyzing ? t('analyzing') : t('analyze_button')}
          </button>
        </div>
      )}
    </div>
  );
}
