import { NextResponse } from 'next/server';
import axios from 'axios';
import { createClient } from '@supabase/supabase-js';

const MEDCHAT_API_URL = 'https://agentsmedchat.onrender.com/chat';

// Initialize Supabase Client
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
// Try Service Role Key first for backend permissions, fallback to Anon Key
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY!;
const supabase = createClient(supabaseUrl, supabaseKey);

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { sessionId, chatInput } = body;

    // 1. Save User Message to History
    if (sessionId && chatInput) {
        const { error: insertError } = await supabase.from('chat_history').insert({
            session_id: sessionId,
            role: 'user',
            content: chatInput,
            metadata: { type: 'chat' }
        });
        if (insertError) console.error("Error saving user message:", insertError);
    }

    // Construct payload for agentsmedchat API
    // API expects: { query: string, session_id?: string }
    const payload = {
      query: chatInput || "",
      session_id: sessionId || null
    };

    console.log(`[${new Date().toISOString()}] Calling agentsmedchat API`);
    console.log("Payload:", JSON.stringify(payload, null, 2));

    const response = await axios.post(MEDCHAT_API_URL, payload, {
      headers: {
        'Content-Type': 'application/json'
      },
      timeout: 120000 // 2 minute timeout for AI processing
    });
    
    // 2. Save Assistant Message to History
    if (sessionId && response.data) {
        // Extract answer safely
        let answer = "No response";
        if (typeof response.data === 'string') answer = response.data;
        else if (response.data.answer) answer = response.data.answer;
        else if (response.data.output) answer = response.data.output;
        else answer = JSON.stringify(response.data);
        
        const thinkingTime = response.data.thinking_time || null;
        
        const { error: aiInsertError } = await supabase.from('chat_history').insert({
            session_id: sessionId,
            role: 'assistant',
            content: answer,
            thinking_time: thinkingTime,
            metadata: { type: 'chat' } // Default metadata
        });
        
        if (aiInsertError) console.error("Error saving AI message:", aiInsertError);
    }

    // Response format: { answer, session_id, agent_type, retrieved_documents, search_results, thinking_time }
    return NextResponse.json(response.data);
  } catch (error: any) {
    console.error('Error calling MedChat API:', error.message);
    return NextResponse.json(
      { 
        error: 'Failed to communicate with MedChat AI', 
        details: error.response?.data || error.message 
      },
      { status: error.response?.status || 500 }
    );
  }
}
