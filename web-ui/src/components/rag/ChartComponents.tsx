'use client';
import React from 'react';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    BarElement,
    Title,
    Tooltip,
    Legend,
    ArcElement,
    PointElement,
} from 'chart.js';
import ChartDataLabels from 'chartjs-plugin-datalabels';
import { Bar, Doughnut } from 'react-chartjs-2';

// Register Chart.js components
ChartJS.register(
    CategoryScale,
    LinearScale,
    BarElement,
    Title,
    Tooltip,
    Legend,
    ArcElement,
    PointElement,
    ChartDataLabels
);

// Color palettes
const LABEL_COLORS = ['#22d3ee', '#a78bfa', '#4ade80', '#f472b6', '#facc15', '#fb923c'];
const LANG_COLORS = ['#60a5fa', '#f87171', '#4ade80', '#facc15', '#a78bfa'];

interface LabelChartProps {
    data: { name: string; count: number; percentage: number }[];
    isDark: boolean;
}

export const LabelDistributionChart: React.FC<LabelChartProps> = ({ data, isDark }) => {
    const textColor = isDark ? '#ffffff' : '#1f2937';
    const gridColor = isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)';
    
    // Calculate max value for y-axis, round up to nice numbers (500, 1000, 1500, 2000, etc)
    const maxValue = Math.max(...data.map(d => d.count));
    // Ensure y-axis is at least 1.5x max value, rounded up to nearest 500
    const yAxisMax = Math.ceil((maxValue * 1.5) / 500) * 500;

    const chartData = {
        labels: data.map(d => d.name),
        datasets: [{
            data: data.map(d => d.count),
            backgroundColor: LABEL_COLORS,
            borderRadius: 6,
            borderSkipped: false,
            // Store percentages for datalabels
            percentages: data.map(d => d.percentage),
        }]
    };

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        layout: {
            padding: {
                top: 25,
            }
        },
        plugins: {
            legend: { display: false },
            tooltip: {
                backgroundColor: isDark ? '#1f2937' : '#ffffff',
                titleColor: textColor,
                bodyColor: textColor,
                borderColor: isDark ? '#374151' : '#e5e7eb',
                borderWidth: 1,
                padding: 12,
                cornerRadius: 8,
                callbacks: {
                    label: (context: { parsed: { y: number } }) => `${context.parsed.y.toLocaleString()} chunks`
                }
            },
            datalabels: {
                anchor: 'end' as const,
                align: 'top' as const,
                color: textColor,
                font: {
                    size: 11,
                    weight: 'bold' as const,
                },
                formatter: (_value: number, context: { dataIndex: number; dataset: { percentages?: number[] } }) => {
                    const percentages = context.dataset.percentages;
                    return percentages ? `${percentages[context.dataIndex]}%` : '';
                },
            }
        },
        scales: {
            x: {
                grid: { display: false },
                ticks: { 
                    color: textColor,
                    font: { size: 11 }
                },
                border: { display: false }
            },
            y: {
                max: yAxisMax,
                beginAtZero: true,
                grid: { 
                    color: gridColor,
                    drawBorder: false
                },
                ticks: { 
                    color: textColor,
                    font: { size: 10 },
                    stepSize: 500,
                    callback: (value: number | string) => {
                        if (typeof value === 'number') {
                            return value >= 1000 ? `${(value/1000).toFixed(1).replace('.0', '')}k` : value;
                        }
                        return value;
                    }
                },
                border: { display: false }
            }
        }
    };

    return (
        <div className="h-[240px]">
            <Bar data={chartData} options={options as Parameters<typeof Bar>[0]['options']} />
        </div>
    );
};

interface LanguageChartProps {
    data: { name: string; value: number }[];
    isDark: boolean;
}

import { 
    PieChart, Pie, Cell, ResponsiveContainer, Label as ReLabel, Tooltip as ReTooltip, Legend as ReLegend 
} from 'recharts';

// ... (existing imports, but wait)

export const LanguageDistributionChart: React.FC<LanguageChartProps> = ({ data, isDark }) => {
    const textColor = isDark ? '#ffffff' : '#1f2937';
    const total = data.reduce((acc, d) => acc + d.value, 0);

    // Filter out 0 value items to avoid ugly chart
    const activeData = data.filter(d => d.value > 0);

    const renderCustomizedLabel = (props: any) => {
        const { cx, cy, midAngle, innerRadius, outerRadius, percent, index, name, value } = props;
        const RADIAN = Math.PI / 180;
        const radius = outerRadius * 1.2;
        const x = cx + radius * Math.cos(-midAngle * RADIAN);
        const y = cy + radius * Math.sin(-midAngle * RADIAN);

        return (
            <text x={x} y={y} fill={textColor} textAnchor={x > cx ? 'start' : 'end'} dominantBaseline="central" fontSize={11}>
                {`${name} ${value} (${(percent * 100).toFixed(1)}%)`}
            </text>
        );
    };

    return (
        <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                    <Pie
                        data={activeData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={80}
                        paddingAngle={0}
                        dataKey="value"
                        strokeWidth={0}
                    >
                        {activeData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={LANG_COLORS[index % LANG_COLORS.length]} stroke="none" />
                        ))}
                        <ReLabel
                            content={({ viewBox }) => {
                                const { cx, cy } = viewBox as any;
                                if (!cx || !cy) return null;
                                return (
                                    <text x={cx} y={cy} textAnchor="middle" dominantBaseline="middle">
                                        <tspan x={cx} dy="-0.5em" fill={textColor} fontSize="28" fontWeight="bold">
                                            {total}
                                        </tspan>
                                        <tspan x={cx} dy="1.5em" fill={textColor} fontSize="12" opacity={0.7}>
                                            Total
                                        </tspan>
                                    </text>
                                );
                            }}
                            position="center"
                        />
                    </Pie>
                    <Pie 
                        data={activeData}
                        cx="50%" 
                        cy="50%" 
                        innerRadius={85} 
                        outerRadius={85} 
                        dataKey="value" 
                        fill="none" 
                        stroke="none"
                        legendType="none"
                        label={renderCustomizedLabel}
                        labelLine={{ stroke: textColor, strokeOpacity: 0.3 }}
                        isAnimationActive={false} // Static labels
                    >
                        {/* Ghost pie just for labels if needed, or use main pie */}
                    </Pie>
                    <ReLegend verticalAlign="bottom" height={36} iconType="circle" />
                </PieChart>
            </ResponsiveContainer>
        </div>
    );
};
