import { NextResponse } from 'next/server';
import axios from 'axios';

const MEDCHAT_API_URL = 'https://agentsmedchat.onrender.com/chat';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { sessionId, chatInput } = body;

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
