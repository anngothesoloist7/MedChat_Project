import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles } from 'lucide-react';

export const StartupLoader = ({ onComplete }: { onComplete: () => void }) => {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    // Minimum display time for the loader (e.g., 2.5 seconds)
    const timer = setTimeout(() => {
      setIsVisible(false);
    }, 2500);

    return () => clearTimeout(timer);
  }, []);

  return (
    <AnimatePresence 
        onExitComplete={onComplete}
    >
      {isVisible && (
        <motion.div
          initial={{ opacity: 1 }}
          exit={{ opacity: 0, filter: "blur(10px)" }}
          transition={{ duration: 0.8, ease: "easeInOut" }}
          className="fixed inset-0 z-[9999] flex flex-col items-center justify-center bg-background p-4"
        >
          <div className="flex flex-col items-center gap-8 relative">
             
            {/* Ambient Background Glow */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-blue-500/20 rounded-full blur-[100px] animate-pulse" />

            {/* Icon Animation */}
            <motion.div
              initial={{ scale: 0.8, opacity: 0, rotate: -20 }}
              animate={{ scale: 1, opacity: 1, rotate: 0 }}
              transition={{ duration: 1, ease: "easeOut" }}
              className="relative z-10 p-6 rounded-2xl bg-secondary/30 border border-white/5 backdrop-blur-md shadow-2xl"
            >
               <Sparkles className="w-16 h-16 text-[#4285f4]" strokeWidth={1.5} />
               <motion.div 
                 initial={{ opacity: 0 }}
                 animate={{ opacity: 1 }}
                 transition={{ delay: 0.5, duration: 1 }}
                 className="absolute inset-0 bg-gradient-to-tr from-blue-500/20 to-transparent rounded-2xl" 
               />
            </motion.div>

            {/* Brand Text */}
            <div className="flex flex-col items-center z-10 gap-2">
                <motion.h1
                    initial={{ y: 20, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: 0.3, duration: 0.8 }}
                    className="text-4xl md:text-5xl font-semibold tracking-tight text-foreground"
                >
                    MedChat<span className="text-[#4285f4]">.AI</span>
                </motion.h1>
                
                <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.7, duration: 0.8 }}
                    className="text-sm md:text-base text-muted-foreground tracking-wide uppercase"
                >
                    Your Advanced Medical Assistant
                </motion.p>
            </div>

            {/* Progress Bar */}
            <motion.div 
                className="h-1 bg-secondary w-48 rounded-full overflow-hidden mt-4 z-10"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1 }}
            >
                <motion.div 
                    className="h-full bg-gradient-to-r from-blue-500 via-purple-500 to-[#4285f4]"
                    initial={{ width: "0%" }}
                    animate={{ width: "100%" }}
                    transition={{ delay: 0.2, duration: 2.3, ease: "easeInOut" }}
                />
            </motion.div>

          </div>
          
          {/* Footer / Credits (Optional) */}
          <motion.div 
            initial={{ opacity: 0 }} 
            animate={{ opacity: 0.5 }} 
            transition={{ delay: 1.5 }}
            className="absolute bottom-8 text-xs text-muted-foreground"
          >
            Initializing Secure Environment...
          </motion.div>

        </motion.div>
      )}
    </AnimatePresence>
  );
};
