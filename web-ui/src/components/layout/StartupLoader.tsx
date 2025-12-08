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
          className="fixed inset-0 z-[9999] flex flex-col items-center justify-center bg-[#121212] text-white p-4"
        >
          <div className="flex flex-col items-center gap-8 relative">
             
            {/* Ambient Background Glow */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-blue-500/10 rounded-full blur-[120px] animate-pulse" />

            {/* Logo Container */}
            <motion.div
              initial={{ scale: 0.8, opacity: 0, y: 10 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }} // iOS ease
              className="relative z-10 w-24 h-24 flex items-center justify-center rounded-2xl bg-[#1C1C1C] border border-white/5 shadow-2xl shadow-black/50 overflow-hidden"
            >
               {/* Inner Glow */}
               <div className="absolute inset-0 bg-gradient-to-tr from-blue-500/10 to-transparent pointer-events-none" />
               
               <Sparkles className="w-10 h-10 text-[#4285f4]" strokeWidth={1.5} />
            </motion.div>

            {/* Brand Text */}
            <div className="flex flex-col items-center z-10 gap-1 mt-2">
                <motion.h1
                    initial={{ y: 20, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: 0.2, duration: 0.8, ease: "easeOut" }}
                    className="text-4xl md:text-5xl font-medium tracking-tight text-white"
                >
                    MedChat<span className="text-[#4285f4]">.AI</span>
                </motion.h1>
                
                <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.5, duration: 0.8 }}
                    className="text-xs md:text-sm text-gray-500 tracking-[0.2em] uppercase font-medium"
                >
                    Your Advanced Medical Assistant
                </motion.p>
            </div>

            {/* Progress Bar */}
            <div className="relative mt-6">
                <motion.div 
                    className="h-[2px] w-48 bg-[#2A2A2A] rounded-full overflow-hidden z-10"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.8 }}
                >
                    <motion.div 
                        className="h-full bg-gradient-to-r from-[#4285f4] via-blue-400 to-purple-500 shadow-[0_0_10px_rgba(66,133,244,0.5)]"
                        initial={{ width: "0%", x: "-100%" }}
                        animate={{ width: "100%", x: "0%" }}
                        transition={{ delay: 0.4, duration: 2.1, ease: "easeInOut" }}
                    />
                </motion.div>
            </div>

          </div>
          
          {/* Footer status */}
          <motion.div 
            initial={{ opacity: 0 }} 
            animate={{ opacity: 1 }} 
            transition={{ delay: 1.5 }}
            className="absolute bottom-12 text-[10px] text-gray-600 font-mono"
          >
            SECURE CONNECTION ESTABLISHED
          </motion.div>

        </motion.div>
      )}
    </AnimatePresence>
  );
};

