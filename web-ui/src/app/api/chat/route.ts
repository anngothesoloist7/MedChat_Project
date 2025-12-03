import { NextResponse } from 'next/server';
import axios from 'axios';

const MEDCHAT_WEBHOOK_URL = process.env.MEDCHAT_WEBHOOK_URL!;
const API_KEY = process.env.MEDCHAT_API_KEY!;

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { sessionId, chatInput, recordInfo, checkJob, deviceId } = body;

    // Construct the payload exactly as requested by the n8n webhook
    // The webhook accepts: sessionId, chatInput, record-info, checkJob
    
    const payload: any = {
      sessionId: sessionId,
      checkJob: checkJob ? "true" : "false",
      chatInput: chatInput || "" // Default to empty string as per new requirement
    };

    if (recordInfo !== undefined) {
      // record-info can be a JSON string (Step 1) or a plain string (Step 3 & 4)
      // The frontend should send it as a string or object.
      // If it's an object, we stringify it. If it's already a string, we pass it as is.
      payload["record-info"] = typeof recordInfo === 'object' ? JSON.stringify(recordInfo) : recordInfo;
    }

    console.log(`[${new Date().toISOString()}] Device Access: ${deviceId || 'Unknown'} | Session: ${sessionId}`);
    console.log("Calling n8n with payload:", JSON.stringify(payload, null, 2));

    const response = await axios.post(MEDCHAT_WEBHOOK_URL, payload, {
      headers: {
        'api-key': API_KEY,
        'Content-Type': 'application/json' // Using JSON as it's cleaner, assuming n8n handles it (standard behavior)
      }
    });

    return NextResponse.json(response.data);
  } catch (error: any) {
    console.error('Error calling MedChat webhook:', error.message);
    // Return the error details if available to help debugging
    return NextResponse.json(
      { 
        error: 'Failed to communicate with MedChat AI', 
        details: error.response?.data || error.message 
      },
      { status: error.response?.status || 500 }
    );
  }
}
