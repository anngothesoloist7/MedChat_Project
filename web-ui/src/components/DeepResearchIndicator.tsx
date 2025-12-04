import React, { useEffect, useState } from 'react';
import { Loader2, FileText, Search, Sparkles, CheckCircle2 } from 'lucide-react';
import { useSettings } from '@/context/SettingsContext';
import { clsx } from 'clsx';

export type ResearchStage = 'uploading' | 'analyzing' | 'refining' | 'complete';

interface DeepResearchIndicatorProps {
  stage: ResearchStage;
}

export function DeepResearchIndicator({ stage }: DeepResearchIndicatorProps) {
  const { t } = useSettings();
  const [activeStageIndex, setActiveStageIndex] = useState(0);

  useEffect(() => {
    switch (stage) {
      case 'uploading':
        setActiveStageIndex(0);
        break;
      case 'analyzing':
        setActiveStageIndex(1);
        break;
      case 'refining':
        setActiveStageIndex(2);
        break;
      case 'complete':
        setActiveStageIndex(3);
        break;
    }
  }, [stage]);

  const steps = [
    { id: 'uploading', icon: FileText, label: t('uploading_case') },
    { id: 'analyzing', icon: Search, label: t('analyzing_case') },
    { id: 'refining', icon: Sparkles, label: t('refining_analysis') },
  ];

  return (
    <div className="w-full max-w-2xl mx-auto my-6 p-5 bg-[#1e1e1e] rounded-xl animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center gap-3 mb-4">
        <div className="relative">
          <div className="w-6 h-6 rounded-full bg-blue-500/20 flex items-center justify-center animate-pulse">
             <Sparkles size={14} className="text-blue-400" />
          </div>
          <div className="absolute inset-0 rounded-full border-2 border-blue-500/20 animate-ping" />
        </div>
        <span className="font-medium text-xs text-blue-400 uppercase tracking-wider">
          MedChat Deep Analysis
        </span>
      </div>

      <div className="space-y-4 relative">
        {/* Connecting Line */}
        <div className="absolute left-[15px] top-2 bottom-2 w-[2px] bg-[#333] -z-10" />

        {steps.map((step, index) => {
          const isActive = index === activeStageIndex;
          const isCompleted = index < activeStageIndex;
          const isPending = index > activeStageIndex;

          return (
            <div 
              key={step.id}
              className={clsx(
                "flex items-center gap-3 transition-all duration-500",
                isActive ? "opacity-100 scale-100" : isCompleted ? "opacity-60" : "opacity-40"
              )}
            >
              <div className={clsx(
                "w-8 h-8 rounded-full flex items-center justify-center border-2 transition-all duration-300 bg-[#1e1e1e] z-10",
                isActive ? "border-blue-500 text-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.3)]" : 
                isCompleted ? "border-emerald-500/50 text-emerald-500 bg-emerald-500/10" : 
                "border-[#333] text-muted-foreground"
              )}>
                {isCompleted ? (
                  <CheckCircle2 size={16} />
                ) : isActive ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <step.icon size={16} />
                )}
              </div>
              
              <div className="flex flex-col">
                <span className={clsx(
                  "font-medium transition-colors duration-300 text-sm",
                  isActive ? "text-foreground" : "text-muted-foreground"
                )}>
                  {step.label}
                </span>
                {isActive && (
                  <span className="text-[10px] text-blue-400 animate-pulse mt-0.5">
                    {t('thinking')}...
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
