import React from 'react';
import { motion } from 'framer-motion';
import { LucideIcon } from 'lucide-react';

interface StatCardProps {
    icon: LucideIcon;
    label: string;
    value: string | number;
    change: string;
    delay: number;
}

export const StatCard: React.FC<StatCardProps> = ({ icon: Icon, label, value, change, delay }) => (
  <motion.div
    initial={{ opacity: 0, scale: 0.95 }}
    animate={{ opacity: 1, scale: 1 }}
    transition={{ delay }}
    className="bg-secondary/30 border border-border/50 rounded-xl p-4 flex flex-col gap-2 hover:bg-secondary/50 transition-colors"
  >
    <div className="flex items-center justify-between">
      <div className="p-2 bg-background/50 rounded-lg text-accent-foreground">
        <Icon size={16} />
      </div>
      <div className="text-[10px] px-2 py-0.5 rounded-full bg-green-500/10 text-green-500 font-medium">
        {change}
      </div>
    </div>
    <div>
      <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">{label}</p>
      <p className="text-xl font-semibold text-foreground mt-0.5">{value}</p>
    </div>
  </motion.div>
);
