import React from 'react';
import { motion } from 'framer-motion';
import { Check, Loader2 } from 'lucide-react';
import { clsx } from 'clsx';

interface StepIndicatorProps {
    step: number;
    currentStep: number;
    label: string;
    isLast?: boolean;
}

export const StepIndicator: React.FC<StepIndicatorProps> = ({ step, currentStep, label, isLast }) => {
    const isActive = currentStep === step;
    const isDone = currentStep > step;
    
    return (
        <div className="relative flex items-start gap-4 z-10">
             {/* Connecting Line */}
            {!isLast && (
                <div className="absolute left-[9px] top-[20px] bottom-[-30px] w-[2px] bg-[#3ECF8E]/30 -z-10">
                    {isDone && (
                         <motion.div 
                            initial={{ height: 0 }}
                            animate={{ height: "100%" }}
                            className="bg-[#3ECF8E] w-full"
                         />
                    )}
                </div>
            )}

            {isActive && (
                <motion.div
                    layoutId="active-step-glow"
                    className="absolute left-[-4px] top-[-4px] w-7 h-7 bg-[#3ECF8E]/20 rounded-full blur-[2px]"
                    initial={{ scale: 0.8, opacity: 0.5 }}
                    animate={{ scale: [1, 1.2, 1], opacity: [0.5, 0.2, 0.5] }}
                    transition={{ duration: 2, repeat: Infinity }}
                />
            )}
            {/* Solid mask to hide the line behind the node */}
            <div className="absolute left-0 top-0 w-5 h-5 rounded-full bg-background z-0" />
            
            <motion.div 
                className={clsx(
                    "w-5 h-5 shrink-0 rounded-full border flex items-center justify-center z-10 transition-colors duration-300 relative mt-[2px]",
                    isActive ? "border-[#3ECF8E] bg-[#3ECF8E]/10 text-[#3ECF8E]" : 
                    isDone ? "border-[#3ECF8E]/50 bg-background text-[#3ECF8E]" : "border-border bg-background"
                )}
                animate={{ scale: isActive ? 1.1 : 1 }}
            >
                {isDone ? <Check size={10} /> : isActive ? <Loader2 size={10} className="animate-spin" /> : null}
            </motion.div>
            <div className={clsx("transition-opacity flex flex-col pt-0.5", isActive ? "opacity-100" : isDone ? "opacity-60" : "opacity-30")}>
                <div className="flex items-center gap-2 mb-0.5">
                    <p className="text-[10px] font-bold uppercase tracking-widest leading-none">Phase 0{step}</p>
                    {isActive && (
                        <span className="flex h-1.5 w-1.5 relative">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#3ECF8E] opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-[#3ECF8E]"></span>
                        </span>
                    )}
                </div>
                <p className="text-sm font-medium">{label}</p>
            </div>
        </div>
    );
};

