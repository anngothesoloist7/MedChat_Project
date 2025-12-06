import React from 'react';
import { motion } from 'framer-motion';
import { Check, Loader2 } from 'lucide-react';
import { clsx } from 'clsx';
interface StepIndicatorProps {
    step: number;
    currentStep: number;
    label: string;
}

export const StepIndicator: React.FC<StepIndicatorProps> = ({ step, currentStep, label }) => {
    const isActive = currentStep === step;
    const isDone = currentStep > step;
    
    return (
        <div className="relative flex items-center gap-4">
            {isActive && (
                <motion.div
                    layoutId="active-step-glow"
                    className="absolute left-[-4px] w-7 h-7 bg-accent/20 rounded-full blur-[2px]"
                    initial={{ scale: 0.8, opacity: 0.5 }}
                    animate={{ scale: [1, 1.2, 1], opacity: [0.5, 0.2, 0.5] }}
                    transition={{ duration: 2, repeat: Infinity }}
                />
            )}
            <motion.div 
                className={clsx(
                    "w-5 h-5 rounded-full border flex items-center justify-center z-10 transition-colors duration-300",
                    isActive ? "border-accent-foreground bg-accent text-accent-foreground" : 
                    isDone ? "border-primary/50 bg-background text-primary" : "border-border bg-background"
                )}
                animate={{ scale: isActive ? 1.1 : 1 }}
            >
                {isDone ? <Check size={10} /> : isActive ? <Loader2 size={10} className="animate-spin" /> : null}
            </motion.div>
            <div className={clsx("transition-opacity flex flex-col", isActive ? "opacity-100" : isDone ? "opacity-60" : "opacity-30")}>
                <div className="flex items-center gap-2">
                    <p className="text-[10px] font-bold uppercase tracking-widest mb-0.5">Phase 0{step}</p>
                    {isActive && (
                        <span className="flex h-1.5 w-1.5 relative">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-foreground opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-accent-foreground"></span>
                        </span>
                    )}
                </div>
                <p className="text-sm font-medium">{label}</p>
            </div>
        </div>
    );
};
