import { NextRequest, NextResponse } from 'next/server';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const projectId = searchParams.get('project_id');
  const apiKey = request.headers.get('X-API-Key') || '';

  if (!projectId) {
    return NextResponse.json(
      { detail: 'project_id is required' },
      { status: 400 }
    );
  }

  try {
    const response = await fetch(`${API_URL}/api/sessions?project_id=${projectId}`, {
      headers: {
        'X-API-Key': apiKey,
        'Content-Type': 'application/json',
      },
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
