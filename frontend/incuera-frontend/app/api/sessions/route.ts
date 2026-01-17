import { NextRequest, NextResponse } from 'next/server';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const projectSlug = searchParams.get('project_slug');
  const apiKey = request.headers.get('X-API-Key') || '';
  const userId = request.headers.get('X-User-ID') || '';

  if (!projectSlug) {
    return NextResponse.json(
      { detail: 'project_slug is required' },
      { status: 400 }
    );
  }

  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    
    if (apiKey) {
      headers['X-API-Key'] = apiKey;
    }
    
    if (userId) {
      headers['X-User-ID'] = userId;
    }
    
    const response = await fetch(`${API_URL}/api/sessions?project_slug=${projectSlug}`, {
      headers,
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { detail: 'Failed to fetch sessions' },
      { status: 500 }
    );
  }
}
