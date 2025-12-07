import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  LayoutGrid, BarChart3, Search, FileText, Database, Ruler, Globe, Loader2, ChevronDown, User, Calendar, Maximize2, Minimize2, HardDrive, Trash2, RefreshCw
} from 'lucide-react';
import { clsx } from 'clsx';
import { useSettings } from '@/context/SettingsContext';
import { Book } from './types';
import { StatCard } from './StatCard';
import { LabelDistributionChart, LanguageDistributionChart, TrendLineChart } from './ChartComponents';
import VectorDashboard from './VectorDashboard';

// Match colors from ChartComponents.tsx
const LABEL_COLORS = ['#4ade80', '#60a5fa', '#c084fc', '#fbbf24', '#2dd4bf', '#fb923c'];

const getKeywordColor = (keyword: string) => {
    const categories = ['disease', 'symptom', 'treatment', 'drug', 'imaging', 'lab-test'];
    const index = categories.indexOf(keyword.toLowerCase());
    if (index !== -1) return LABEL_COLORS[index];
    // Hash fallback for unknown keywords
    let hash = 0;
    for (let i = 0; i < keyword.length; i++) hash = keyword.charCodeAt(i) + ((hash << 5) - hash);
    const c = (hash & 0x00FFFFFF).toString(16).toUpperCase();
    return '#' + "00000".substring(0, 6 - c.length) + c;
};

interface LibraryStats {
    keyword_distribution: Record<string, number>;
    language_distribution: Record<string, number>;
    avg_chunk_length: number;
    total_size_bytes?: number;
}

// Expandable Book Card Component (Controlled)
const BookCard: React.FC<{ 
    book: Book; 
    index: number; 
    isExpanded: boolean; 
    onToggle: () => void;
    onDelete: (id: string, pdfId?: string) => void;
    isDeleting: boolean;
}> = ({ book, index, isExpanded, onToggle, onDelete, isDeleting }) => {
    const { t } = useSettings();
    
    return (
        <motion.div 
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.03 }}
            className={clsx(
                "border border-border/50 rounded-xl overflow-hidden transition-all duration-200",
                isExpanded ? "bg-secondary/20 border-accent/30" : "bg-secondary/10 hover:bg-secondary/15"
            )}
        >
            {/* Compact View - Always Visible */}
            <div 
                className="p-3 flex items-center justify-between gap-4 cursor-pointer group"
                onClick={onToggle}
            >
                <div className="flex items-center gap-3 min-w-0 flex-1">
                    <div className={clsx(
                        "p-2 rounded-lg shrink-0 border transition-colors",
                        isExpanded 
                            ? "bg-[#3ECF8E]/10 text-[#3ECF8E] border-[#3ECF8E]/30" 
                            : "bg-background text-muted-foreground border-border/30 group-hover:text-[#3ECF8E] group-hover:bg-[#3ECF8E]/10 group-hover:border-[#3ECF8E]/20"
                    )}>
                        <FileText size={16} />
                    </div>
                    <h3 className={clsx(
                        "text-sm font-medium text-foreground transition-colors group-hover:text-[#3ECF8E]",
                        !isExpanded && "truncate"
                    )}>
                        {book.title}
                    </h3>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                    {/* Hide keywords when expanded */}
                    {!isExpanded && (
                        <div className="flex gap-1">
                            {book.keywords.slice(0, 3).map(k => {
                                const color = getKeywordColor(k);
                                return (
                                    <span 
                                        key={k} 
                                        className="text-sm px-2.5 py-1 rounded-md border capitalize whitespace-nowrap"
                                        style={{
                                            backgroundColor: `${color}15`, // ~8% opacity
                                            color: color,
                                            borderColor: `${color}30` // ~20% opacity
                                        }}
                                    >
                                        {k}
                                    </span>
                                );
                            })}
                        </div>
                    )}
                    <ChevronDown 
                        size={14} 
                        className={clsx("text-muted-foreground transition-transform duration-200", isExpanded && "rotate-180 text-accent")} 
                    />
                </div>
            </div>
            
            {/* Expanded Details */}
            <AnimatePresence>
                {isExpanded && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.25, ease: "easeOut" }}
                        className="overflow-hidden"
                    >
                        <div className="px-3 pb-4 pt-3 border-t border-border/30">
                            {/* Stats Grid */}
                            <div className="grid grid-cols-3 gap-3">
                                {/* Author */}
                                <div className="bg-background/50 rounded-lg p-2.5 border border-border/30">
                                    <div className="flex items-center gap-1.5 text-muted-foreground mb-1">
                                        <User size={11} />
                                        <span className="text-[10px] uppercase tracking-wide">{t('rag.author')}</span>
                                    </div>
                                    <p className="text-xs font-medium text-foreground leading-snug">{book.author}</p>
                                </div>
                                
                                {/* Year */}
                                <div className="bg-background/50 rounded-lg p-2.5 border border-border/30">
                                    <div className="flex items-center gap-1.5 text-muted-foreground mb-1">
                                        <Calendar size={11} />
                                        <span className="text-[10px] uppercase tracking-wide">{t('rag.published')}</span>
                                    </div>
                                    <p className="text-xs font-medium text-foreground">{book.year}</p>
                                </div>
                                
                                {/* Chunks */}
                                <div className="bg-background/50 rounded-lg p-2.5 border border-border/30">
                                    <div className="flex items-center gap-1.5 text-muted-foreground mb-1">
                                        <Database size={11} />
                                        <span className="text-[10px] uppercase tracking-wide">{t('rag.indexed')}</span>
                                    </div>
                                    <p className="text-xs font-medium text-foreground font-mono">{book.stats?.qdrantPoints.toLocaleString()} {t('rag.chunks')}</p>
                                </div>
                            </div>
                            
                            {/* Keywords Full List */}
                            {book.keywords.length > 0 && (
                                <div className="mt-3 flex items-center gap-2">
                                    <span className="text-[10px] uppercase tracking-wide text-muted-foreground shrink-0">{t('rag.keywords')}</span>
                                    <div className="flex flex-wrap gap-1.5">
                                        {book.keywords.map(k => {
                                             const color = getKeywordColor(k);
                                             return (
                                                <span 
                                                    key={k} 
                                                    className="text-sm px-2.5 py-1 rounded-md border capitalize whitespace-nowrap"
                                                    style={{
                                                        backgroundColor: `${color}15`,
                                                        color: color,
                                                        borderColor: `${color}30`
                                                    }}
                                                >
                                                    {k}
                                                </span>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}

                            {/* Actions */}
                            <div className="mt-4 pt-3 border-t border-border/30 flex justify-end">
                                <button
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        onDelete(book.id, book.pdf_id);
                                    }}
                                    disabled={isDeleting}
                                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-500 text-xs font-medium transition-colors disabled:opacity-50"
                                >
                                    {isDeleting ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
                                    {isDeleting ? t('rag.deleting') : t('rag.delete_index')}
                                </button>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
};

interface RagLibraryProps {
    books: Book[];
    stats?: LibraryStats;
    isLoading?: boolean;
    onRefresh?: () => void;
}

export const RagLibrary: React.FC<RagLibraryProps> = ({ books, stats, isLoading = false, onRefresh }) => {
    const { t } = useSettings();
    const [viewMode, setViewMode] = useState<'list' | 'chart'>('list');
    const [searchQuery, setSearchQuery] = useState('');
    const [expandedBookId, setExpandedBookId] = useState<string | null>(null);
    const [isDark, setIsDark] = useState(true);
    const [fullWidth, setFullWidth] = useState(false);
    const [deletingBookId, setDeletingBookId] = useState<string | null>(null);
    
    // Theme detection
    useEffect(() => {
        const checkTheme = () => {
            const isDarkMode = document.documentElement.classList.contains('dark');
            setIsDark(isDarkMode);
        };
        checkTheme();
        // Re-check on class changes
        const observer = new MutationObserver(checkTheme);
        observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
        return () => observer.disconnect();
    }, []);
    
    const totalPoints = books.reduce((acc, b) => acc + (b.stats?.qdrantPoints || 0), 0);

    const handleToggleExpand = (bookId: string) => {
        setExpandedBookId(prev => prev === bookId ? null : bookId);
    };

    const deleteBook = async (id: string, pdfId?: string) => {
        const targetId = pdfId || id; // Fallback to id if pdfId missing (though api expects pdf_id usually)
        if (!targetId) return;
        
        if (!confirm(t('rag.delete_confirm'))) return;

        setDeletingBookId(id);
        try {
            const res = await fetch(`https://rag.botnow.online/library/${encodeURIComponent(targetId)}`, {
                method: 'DELETE',
            });
            if (res.ok) {
                if (onRefresh) onRefresh();
            } else {
                console.error("Failed to delete book");
                alert("Failed to delete book. Check console for details.");
            }
        } catch (e) {
            console.error(e);
            alert("Error deleting book");
        } finally {
            setDeletingBookId(null);
        }
    };

    // Keyword labels for chart
    const keywordLabels = ['disease', 'symptom', 'treatment', 'drug', 'imaging', 'lab-test'];
    const keywordData = keywordLabels.map(k => stats?.keyword_distribution?.[k] || 0);
    const totalKeywords = keywordData.reduce((a, b) => a + b, 0) || 1;
    
    // Bar chart data with percentages
    const labelChartData = keywordLabels.map((name, i) => ({
        name: name.charAt(0).toUpperCase() + name.slice(1),
        count: keywordData[i],
        percentage: Math.round((keywordData[i] / totalKeywords) * 100)
    }));

    // Pie chart data for languages - document based
    const languageCounts: Record<string, number> = {};
    
    // If no explicit language found, we can't really plot meaningful doc distribution
    // But we need to try.
    books.forEach(b => {
        // Safe access, prioritizing root language field from API
        let lang = b.language || (b as any).metadata?.language;
        
        // Normalize
        if (!lang) lang = "Unknown";
        if (lang === 'vi' || lang === 'vietnamese') lang = 'Vietnamese';
        else if (lang === 'en' || lang === 'english') lang = 'English';
        
        // Capitalize
        lang = lang.charAt(0).toUpperCase() + lang.slice(1);
        
        languageCounts[lang] = (languageCounts[lang] || 0) + 1;
    });

    const totalDocsCalculated = books.length || 1;

    const languageChartData = Object.entries(languageCounts)
        .map(([name, value]) => ({
            name,
            value,
            percentage: Math.round((value / totalDocsCalculated) * 100)
        }))
        .sort((a, b) => b.value - a.value)
        .slice(0, 5);

    return (
        <div className={clsx(
            "mt-6 md:mt-12 pb-20 w-full mx-auto transition-all duration-300",
            fullWidth ? "max-w-full" : "max-w-4xl"
        )}>
            
            {/* Controls */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
                <div className="flex items-center justify-between md:justify-start gap-4">
                    <div className="bg-secondary/50 p-1 rounded-lg flex border border-border/50">
                        <button 
                            onClick={() => setViewMode('list')}
                            className={clsx("p-2 rounded-md transition-all", viewMode === 'list' ? "bg-background shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground")}
                        >
                            <LayoutGrid size={16} />
                        </button>
                        <button 
                            onClick={() => setViewMode('chart')}
                            className={clsx("p-2 rounded-md transition-all", viewMode === 'chart' ? "bg-background shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground")}
                        >
                            <BarChart3 size={16} />
                        </button>
                    </div>
                </div>

                 {viewMode === 'list' && (
                     <div className="relative w-full md:w-64 group">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground group-hover:text-foreground transition-colors" />
                        <input 
                            type="text" 
                            placeholder={t('rag.filter_docs')} 
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full bg-secondary/30 border border-border/50 rounded-lg pl-9 pr-4 py-2.5 text-sm focus:ring-1 focus:ring-accent outline-none transition-all focus:bg-secondary/50"
                        />
                     </div>
                 )}
            </div>

            {viewMode === 'list' && (
                <div className="flex items-center gap-2 mb-6">
                    <div className="h-4 w-1 bg-[#3ECF8E] rounded-full" />
                    <div className="flex items-center gap-2 h-full">
                         <h2 className="text-sm font-semibold tracking-tight uppercase text-muted-foreground leading-none">
                            {t('rag.doc_list')}
                        </h2>
                        <button 
                            onClick={onRefresh}
                            className={clsx(
                                "ml-2 p-1 rounded-md text-muted-foreground hover:bg-secondary hover:text-foreground transition-all", 
                                isLoading && "cursor-not-allowed opacity-70"
                            )}
                            disabled={isLoading}
                            title="Reload Library"
                        >
                             <RefreshCw size={14} className={clsx(isLoading && "animate-spin")} />
                        </button>
                    </div>
                </div>
            )}

            {isLoading && books.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
                    <Loader2 className="w-8 h-8 animate-spin mb-4" />
                    <p className="text-sm">{t('rag.loading')}</p>
                </div>
            ) : viewMode === 'list' ? (
                <div className="grid gap-2">
                    {books.filter(b => b.title.toLowerCase().includes(searchQuery.toLowerCase())).map((book, i) => (
                        <BookCard 
                            key={book.id} 
                            book={book} 
                            index={i}
                            isExpanded={expandedBookId === book.id}
                            onToggle={() => handleToggleExpand(book.id)}
                            onDelete={deleteBook}
                            isDeleting={deletingBookId === book.id}
                        />
                    ))}
                    {books.length === 0 && !isLoading && (
                        <div className="text-center py-12 text-muted-foreground">
                            <FileText className="w-12 h-12 mx-auto mb-4 opacity-30" />
                            <p className="text-sm">{t('rag.no_docs')}</p>
                        </div>
                    )}
                </div>
            ) : (
                <div className="space-y-6">
                    {/* Document Insight Header with Full Width Toggle */}
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-2">
                            <div className="h-4 w-1 bg-[#3ECF8E] rounded-full" />
                            <div className="flex items-center gap-2 h-full">
                                <h3 className="text-sm font-semibold tracking-tight uppercase text-muted-foreground leading-none">{t('rag.doc_insight')}</h3>
                                <button 
                                    onClick={onRefresh}
                                    className={clsx(
                                        "ml-2 p-1 rounded-md text-muted-foreground hover:bg-secondary hover:text-foreground transition-all", 
                                        isLoading && "cursor-not-allowed opacity-70"
                                    )}
                                    disabled={isLoading}
                                    title="Reload Insights"
                                >
                                     <RefreshCw size={14} className={clsx(isLoading && "animate-spin")} />
                                </button>
                            </div>
                        </div>
                        <button
                            onClick={() => setFullWidth(!fullWidth)}
                            className={clsx(
                                "hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
                                fullWidth 
                                    ? "bg-accent text-accent-foreground" 
                                    : "bg-secondary/50 text-muted-foreground hover:bg-secondary hover:text-foreground border border-border/50"
                            )}
                        >
                            {fullWidth ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
                            {fullWidth ? t('rag.compact') : t('rag.full_width')}
                        </button>
                    </div>
                    
                    {/* Stats Row */}
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3 md:gap-4">
                        <StatCard icon={FileText} label={t('rag.documents')} value={books.length} change="pdf" delay={0.1} />
                        <StatCard icon={Database} label={t('rag.vector_points')} value={totalPoints.toLocaleString()} change="json" delay={0.2} />
                        <StatCard icon={Ruler} label={t('rag.avg_chunk')} value={stats?.avg_chunk_length?.toLocaleString() || '0'} change="chars" delay={0.3} />
                    </div>
                    
                    {/* Label Distribution Chart - Bar Chart */}
                    <motion.div 
                        initial={{opacity:0, y:10}} 
                        animate={{opacity:1, y:0}} 
                        transition={{delay:0.4}} 
                        className="bg-secondary/10 border border-border/50 rounded-xl p-4 md:p-6"
                    >
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-sm font-medium">{t('rag.label_dist')}</h3>
                            <BarChart3 size={16} className="text-muted-foreground/40" />
                        </div>
                        <LabelDistributionChart data={labelChartData} isDark={isDark} />
                    </motion.div>
                    
                    {/* Language Distribution Chart - Doughnut Chart with Legend */}
                    <motion.div 
                        initial={{opacity:0, y:10}} 
                        animate={{opacity:1, y:0}} 
                        transition={{delay:0.5}} 
                        className="bg-secondary/10 border border-border/50 rounded-xl p-4 md:p-6"
                    >
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-sm font-medium">{t('rag.lang_dist')}</h3>
                            <Globe size={16} className="text-muted-foreground/40" />
                        </div>
                        {languageChartData.length > 0 ? (
                            <LanguageDistributionChart data={languageChartData} isDark={isDark} totalDocs={books.length} />
                        ) : (
                            <div className="flex items-center justify-center h-40">
                                <p className="text-xs text-muted-foreground/50">{t('rag.no_lang_data')}</p>
                            </div>
                        )}
                    </motion.div>

                    {/* Trend Line Chart - Multi-Line Chart */}
                    <motion.div 
                        initial={{opacity:0, y:10}} 
                        animate={{opacity:1, y:0}} 
                        transition={{delay:0.6}} 
                        className="bg-secondary/10 border border-border/50 rounded-xl p-4 md:p-6"
                    >
                         <div className="flex items-center justify-between mb-4">
                            <h3 className="text-sm font-medium">{t('rag.trends_over_time') || "Trends Over Time"}</h3>
                            <BarChart3 size={16} className="text-muted-foreground/40" />
                        </div>
                        {(() => {
                            // Logic to aggregate data by year and keyword
                            const yearMap: Record<string, Record<string, number>> = {};
                            const validYears = new Set<string>();

                            books.forEach(b => {
                                // Extract year
                                let year = b.year;
                                if (!year || year === 'Unknown') return;
                                
                                // Normalize simple years
                                const yearMatch = year.match(/\d{4}/);
                                if (yearMatch) year = yearMatch[0];
                                else return; 
                                validYears.add(year);

                                if (!yearMap[year]) {
                                    yearMap[year] = {};
                                    keywordLabels.forEach(k => yearMap[year][k] = 0);
                                }
                                
                                const totalPoints = b.stats?.qdrantPoints || 0;
                                
                                // Distribute points to keywords present in the book
                                b.keywords.forEach(k => {
                                    const lowerK = k.toLowerCase();
                                    // Map to our labels
                                    keywordLabels.forEach(label => {
                                        if (label.toLowerCase() === lowerK || lowerK.includes(label.toLowerCase())) {
                                            yearMap[year][label] = (yearMap[year][label] || 0) + totalPoints;
                                        }
                                    });
                                });
                            });

                            const sortedYears = Array.from(validYears).sort();
                            const trendData = sortedYears.map(year => {
                                const reducedValues: Record<string, number> = {};
                                Object.entries(yearMap[year]).forEach(([k, v]) => {
                                    reducedValues[k] = Number((v / 1000).toFixed(2));
                                });
                                return {
                                    year,
                                    ...reducedValues
                                };
                            });

                            if (trendData.length === 0) {
                               return (
                                   <div className="flex items-center justify-center h-40">
                                        <p className="text-xs text-muted-foreground/50">{t('rag.no_trend_data') || "No trend data available"}</p>
                                    </div>
                               )
                            }

                            return <TrendLineChart data={trendData} categories={keywordLabels} isDark={isDark} />;
                        })()}
                    </motion.div>
                    

                </div>
            )}
        </div>
    );
};
