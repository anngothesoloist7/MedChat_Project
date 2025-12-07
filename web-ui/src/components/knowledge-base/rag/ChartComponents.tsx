'use client';

import * as React from "react"
import { Bar, BarChart, CartesianGrid, Label, LabelList, Pie, PieChart, Sector, XAxis, Cell } from "recharts"
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
        <div className="flex flex-wrap justify-center gap-4 mt-4">
            {chartData.map((item) => (
                <div key={item.label} className="flex items-center gap-2">
                    <div 
                        className="w-3 h-3 rounded-[2px]" 
                        style={{ backgroundColor: item.fill }}
                    />
                    <span className="text-xs font-medium text-foreground">{item.label}</span>
                </div>
            ))}
        </div>
      </CardContent>
    </Card>
  )
}


interface LanguageChartProps {
    data: { name: string; value: number }[];
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
              content={<ChartTooltipContent hideLabel />}
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
                          className="fill-foreground text-3xl font-bold"
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
        <div className="flex flex-wrap justify-center gap-4 mt-4">
            {chartData.map((item, index) => (
                <div key={item.lang} className="flex items-center gap-2">
                    <div 
                        className="w-3 h-3 rounded-[2px]" 
                        style={{ backgroundColor: item.fill }}
                    />
                    <span className="text-xs font-medium text-foreground">{item.lang}</span>
                </div>
            ))}
        </div>
      </CardContent>
    </Card>
  )
}
