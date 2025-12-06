export type PipelineState = 'idle' | 'checking' | 'confirming' | 'processing' | 'completed';

export interface Book {
    id: string;
    pdf_id?: string;
    title: string;
    author: string;
    year: string;
    keywords: string[];
    stats?: { qdrantPoints: number; avgChunkLength: number; };
}

export type LogMessage = {
    step: number;
    message: string;
};
