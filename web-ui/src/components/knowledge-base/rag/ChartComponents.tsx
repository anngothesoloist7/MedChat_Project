'use client';

import * as React from "react"
import { Bar, BarChart, CartesianGrid, Label, LabelList, Pie, PieChart, Sector, XAxis, Cell, Line, LineChart, Legend, YAxis } from "recharts"
import { PieSectorDataItem } from "recharts/types/polar/Pie"

import {
  Card,
  CardContent,
} from "@/components/ui/card"
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart"
import { useTranslation } from "react-i18next"

// Palette matching the user's sample image - Shared for both charts
const CHART_COLORS = [
    "#4ade80", // Green (Chart 1)
    "#60a5fa", // Blue (Chart 2)
    "#c084fc", // Purple (Chart 3)
    "#fbbf24", // Yellow (Chart 4)
    "#2dd4bf", // Teal (Chart 5)
    "#fb923c", // Orange (Chart 6)
];

interface LabelChartProps {
    data: { name: string; count: number; percentage: number }[];
    isDark: boolean;
}

export function LabelDistributionChart({ data }: LabelChartProps) {
  const chartData = data.map((item, index) => ({
    label: item.name,
    count: item.count,
    percentage: item.percentage, // Add percentage for LabelList
    fill: CHART_COLORS[index % CHART_COLORS.length] // Unique color per bar
  }))

  const chartConfig = {
    count: {
      label: "Chunks",
      color: "hsl(142, 76%, 36%)", // Fallback
    },
    ...Object.fromEntries(chartData.map((item, index) => [
        item.label,
        { label: item.label, color: CHART_COLORS[index % CHART_COLORS.length] }
    ]))
  } satisfies ChartConfig

  return (
    <Card className="flex flex-col border-0 shadow-none bg-transparent">
      <CardContent className="flex-1 pb-0">
        <ChartContainer config={chartConfig} className="min-h-[200px] w-full">
          <BarChart accessibilityLayer data={chartData} margin={{ top: 20 }}>
            {/* Defs removed as we are using solid colors per bar now */}
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="label"
              tickLine={false}
              tickMargin={10}
              axisLine={false}
            />
            <ChartTooltip
              cursor={false}
              content={<ChartTooltipContent hideLabel />}
            />
            {/* Remove global fill, use Cells instead */}
            <Bar dataKey="count" radius={[8, 8, 0, 0]}>
                {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
                <LabelList 
                    dataKey="percentage" 
                    position="top" 
                    offset={12} 
                    className="fill-foreground" 
                    fontSize={12}
                    formatter={(value: any) => `${value}%`} 
                />
            </Bar>
          </BarChart>
        </ChartContainer>

        {/* Custom Legend */}
        <div className="flex flex-wrap justify-center gap-2 md:gap-4 mt-4">
            {chartData.map((item) => (
                <div key={item.label} className="flex items-center gap-2">
                    <div 
                        className="w-3 h-3 rounded-[2px]" 
                        style={{ backgroundColor: item.fill }}
                    />
                    <span className="text-[10px] md:text-xs font-medium text-foreground">{item.label}</span>
                </div>
            ))}
        </div>
      </CardContent>
    </Card>
  )
}


interface LanguageChartProps {
    data: { name: string; value: number; percentage?: number }[];
    isDark: boolean;
    totalDocs?: number; // New prop for center text
}

export function LanguageDistributionChart({ data, totalDocs }: LanguageChartProps) {
  const { t } = useTranslation('common');
  const derivedTotal = React.useMemo(() => {
    return data.reduce((acc, curr) => acc + curr.value, 0)
  }, [data])

  const displayTotal = totalDocs !== undefined ? totalDocs : derivedTotal;

  const chartData = data.map((item, index) => ({
      lang: item.name,
      value: item.value,
      percentage: item.percentage || 0,
      fill: CHART_COLORS[index % CHART_COLORS.length],
  })).filter(d => d.value > 0);

  const chartConfig = {
    value: {
      label: "Count",
    },
    ...Object.fromEntries(chartData.map((item, index) => [
        item.lang,
        { label: item.lang, color: CHART_COLORS[index % CHART_COLORS.length] }
    ]))
  } satisfies ChartConfig

  return (
    <Card className="flex flex-col border-0 shadow-none bg-transparent">
      <CardContent className="flex-1 pb-0">
        <ChartContainer
          config={chartConfig}
          className="mx-auto aspect-square max-h-[250px]"
        >
          <PieChart>
            <ChartTooltip
              cursor={false}
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const item = payload[0].payload;
                  return (
                    <div className="bg-popover text-popover-foreground border border-border/50 rounded-lg shadow-xl p-3 text-xs min-w-[140px]">
                       <div className="flex items-center gap-2 mb-2 pb-2 border-b border-border/50">
                         <div className="w-2.5 h-2.5 rounded-[2px]" style={{backgroundColor: item.fill}} />
                         <span className="font-semibold">{item.lang}</span>
                       </div>
                       <div className="flex flex-col gap-1.5">
                         <div className="flex justify-between items-center">
                            <span className="text-muted-foreground">Documents</span>
                            <span className="font-mono font-medium">{item.value}</span>
                         </div>
                         <div className="flex justify-between items-center">
                            <span className="text-muted-foreground">Percentage</span>
                            <span className="font-mono font-medium">{item.percentage}%</span>
                         </div>
                       </div>
                    </div>
                  )
                }
                return null;
              }}
            />
            <Pie
              data={chartData}
              dataKey="value"
              nameKey="lang"
              innerRadius={60}
              strokeWidth={5}
            >
              <Label
                content={({ viewBox }) => {
                  if (viewBox && "cx" in viewBox && "cy" in viewBox) {
                    return (
                      <text
                        x={viewBox.cx}
                        y={viewBox.cy}
                        textAnchor="middle"
                        dominantBaseline="middle"
                      >
                        <tspan
                          x={viewBox.cx}
                          y={viewBox.cy}
                          className="fill-foreground text-2xl md:text-3xl font-bold"
                        >
                          {displayTotal.toLocaleString()}
                        </tspan>
                        <tspan
                          x={viewBox.cx}
                          y={(viewBox.cy || 0) + 24}
                          className="fill-muted-foreground text-xs"
                        >
                          Total
                        </tspan>
                      </text>
                    )
                  }
                  return null;
                }}
              />
            </Pie>
          </PieChart>
        </ChartContainer>

        {/* Custom Legend */}
        <div className="flex flex-wrap justify-center gap-2 md:gap-4 mt-4">
            {chartData.map((item, index) => (
                <div key={item.lang} className="flex items-center gap-2">
                    <div 
                        className="w-3 h-3 rounded-[2px]" 
                        style={{ backgroundColor: item.fill }}
                    />
                    <span className="text-[10px] md:text-xs font-medium text-foreground">{item.lang}</span>
                </div>
            ))}
        </div>
      </CardContent>
    </Card>
  )
}

interface TrendChartProps {
    data: any[];
    categories: string[];
    isDark: boolean;
}

export function TrendLineChart({ data, categories, isDark }: TrendChartProps) {
  const [hiddenSeries, setHiddenSeries] = React.useState<string[]>([]);
  const [hoveredSeries, setHoveredSeries] = React.useState<string | null>(null);

  const toggleSeries = (name: string) => {
      setHiddenSeries(prev => 
          prev.includes(name) 
              ? prev.filter(item => item !== name) 
              : [...prev, name]
      );
  };

  const chartConfig = {
      // Map categories to config
      ...Object.fromEntries(categories.map((cat, index) => [
          cat,
          { label: cat.charAt(0).toUpperCase() + cat.slice(1), color: CHART_COLORS[index % CHART_COLORS.length] }
      ]))
  } satisfies ChartConfig

  return (
    <Card className="flex flex-col border-0 shadow-none bg-transparent">
        <CardContent className="flex-1 pb-0">
            <ChartContainer config={chartConfig} className="min-h-[250px] w-full">
                <LineChart
                    accessibilityLayer
                    data={data}
                    margin={{
                        left: 12,
                        right: 12,
                        top: 12,
                        bottom: 12,
                    }}
                >
                    <CartesianGrid vertical={false} strokeDasharray="3 3" strokeOpacity={0.2} />
                    <XAxis
                        dataKey="year"
                        tickLine={false}
                        axisLine={false}
                        tickMargin={8}
                    />
                    <YAxis 
                         tickLine={false}
                         axisLine={false}
                         tickMargin={8}
                         width={40}
                         tickFormatter={(value) => `${value}k`}
                    />
                    <ChartTooltip
                        cursor={false}
                        content={<ChartTooltipContent indicator="line" />}
                    />
                    {categories.map((cat, index) => {
                         const isHidden = hiddenSeries.includes(cat);
                         if (isHidden) return null;
                         
                         const isDimmed = hoveredSeries && hoveredSeries !== cat;

                         return (
                            <Line
                                key={cat}
                                dataKey={cat}
                                type="monotone"
                                stroke={CHART_COLORS[index % CHART_COLORS.length]}
                                strokeWidth={hoveredSeries === cat ? 3 : 2}
                                strokeOpacity={isDimmed ? 0.2 : 1}
                                dot={false}
                                activeDot={{ r: 6 }}
                                onMouseEnter={() => setHoveredSeries(cat)}
                                onMouseLeave={() => setHoveredSeries(null)}
                            />
                        );
                    })}
                    <Legend 
                        content={({ payload }) => (
                           <div className="flex flex-wrap justify-center gap-2 md:gap-4 mt-4">
                                {(payload || []).map((entry: any, index: number) => {
                                    const isHidden = hiddenSeries.includes(entry.value);
                                    const isHovered = hoveredSeries === entry.value;
                                    const isDimmed = hoveredSeries && hoveredSeries !== entry.value;

                                    return (
                                    <div 
                                        key={`item-${index}`} 
                                        className={`flex items-center gap-2 cursor-pointer transition-all duration-200 ${isHidden ? 'opacity-40 grayscale' : isDimmed ? 'opacity-30' : 'opacity-100'} ${isHovered ? 'scale-105 font-semibold' : ''}`}
                                        onClick={() => toggleSeries(entry.value)}
                                        onMouseEnter={() => setHoveredSeries(entry.value)}
                                        onMouseLeave={() => setHoveredSeries(null)}
                                    >
                                        <div 
                                            className="w-2.5 h-2.5 md:w-3 md:h-3 rounded-[2px]" 
                                            style={{ backgroundColor: entry.color }}
                                        />
                                        <span className="text-[10px] md:text-xs font-medium text-foreground">
                                            {typeof entry.value === 'string' ? entry.value.charAt(0).toUpperCase() + entry.value.slice(1) : entry.value}
                                        </span>
                                    </div>
                                    )
                                })}
                            </div>
                        )}
                    />
                </LineChart>
            </ChartContainer>
        </CardContent>
    </Card>
  )
}
