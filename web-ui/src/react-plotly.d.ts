declare module 'react-plotly.js' {
    import * as Plotly from 'plotly.js';
    import React from 'react';

    export interface PlotParams {
        data: Plotly.Data[];
        layout?: Partial<Plotly.Layout>;
        frames?: Plotly.Frame[];
        config?: Partial<Plotly.Config>;
        onInitialized?: (figure: Readonly<Plotly.Figure>, graphDiv: Readonly<HTMLElement>) => void;
        onUpdate?: (figure: Readonly<Plotly.Figure>, graphDiv: Readonly<HTMLElement>) => void;
        onPurge?: (figure: Readonly<Plotly.Figure>, graphDiv: Readonly<HTMLElement>) => void;
        onError?: (err: Readonly<Error>) => void;
        onClick?: (event: Readonly<Plotly.PlotMouseEvent>) => void;
        divId?: string;
        className?: string;
        style?: React.CSSProperties;
        useResizeHandler?: boolean;
        debug?: boolean;
    }

    const Plot: React.ComponentType<PlotParams>;
    export default Plot;
}
