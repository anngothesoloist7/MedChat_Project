import { NextRequest, NextResponse } from 'next/server';
import { writeFile, mkdir } from 'fs/promises';
import { join, resolve } from 'path';
import { spawn } from 'child_process';
import { existsSync } from 'fs';

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get('file') as File;

    if (!file) {
      return NextResponse.json(
        { error: 'No file uploaded' },
        { status: 400 }
      );
    }

    // Define paths
    // web-ui is at projects/MedChat/web-ui
    // rag-pipeline is at projects/MedChat/rag-pipeline
    const projectRoot = resolve(process.cwd(), '..');
    const ragPipelineDir = join(projectRoot, 'rag-pipeline');
    const rawDir = join(ragPipelineDir, 'database', 'raw');

    // Ensure raw directory exists
    if (!existsSync(rawDir)) {
      await mkdir(rawDir, { recursive: true });
    }

    // Save file
    const bytes = await file.arrayBuffer();
    const buffer = Buffer.from(bytes);
    const filePath = join(rawDir, file.name);
    await writeFile(filePath, buffer);

    console.log(`File saved to: ${filePath}`);

    // Run RAG pipeline
    // Assuming python is in the path. You might need 'python3' or a specific venv python.
    // We'll try 'python' first.
    const pythonScript = join(ragPipelineDir, 'rag-main.py');
    
    console.log(`Executing: python ${pythonScript} "${filePath}"`);

    return new Promise((resolvePromise) => {
      const pythonProcess = spawn('python', [pythonScript, filePath], {
        cwd: ragPipelineDir, // Run from rag-pipeline dir so relative paths work
        env: process.env, // Inherit env vars
      });

      let output = '';
      let errorOutput = '';

      pythonProcess.stdout.on('data', (data) => {
        const str = data.toString();
        console.log(`[RAG stdout]: ${str}`);
        output += str;
      });

      pythonProcess.stderr.on('data', (data) => {
        const str = data.toString();
        console.error(`[RAG stderr]: ${str}`);
        errorOutput += str;
      });

      pythonProcess.on('close', (code) => {
        console.log(`RAG process exited with code ${code}`);
        if (code === 0) {
          resolvePromise(NextResponse.json({ 
            success: true, 
            message: 'Pipeline completed successfully',
            logs: output
          }));
        } else {
          resolvePromise(NextResponse.json({ 
            error: 'Pipeline failed', 
            details: errorOutput || output 
          }, { status: 500 }));
        }
      });

      pythonProcess.on('error', (err) => {
        console.error('Failed to start python process:', err);
        resolvePromise(NextResponse.json({ 
          error: 'Failed to start RAG pipeline', 
          details: err.message 
        }, { status: 500 }));
      });
    });

  } catch (error: any) {
    console.error('Upload error:', error);
    return NextResponse.json(
      { error: 'Internal server error', details: error.message },
      { status: 500 }
    );
  }
}
