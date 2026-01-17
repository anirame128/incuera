/**
 * Project API route - proxies to backend
 */
import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function GET(
  request: NextRequest,
  props: { params: Promise<{ id: string }> }
) {
  const params = await props.params;
  const searchParams = request.nextUrl.searchParams;
  const userId = searchParams.get('user_id');
  
  if (!userId) {
    return NextResponse.json(
      { error: 'user_id is required' },
      { status: 400 }
    );
  }
  
  if (!params.id) {
    return NextResponse.json(
      { error: 'project slug is required' },
      { status: 400 }
    );
  }
  
  try {
    const response = await fetch(`${BACKEND_URL}/api/projects/${params.id}?user_id=${userId}`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Failed to fetch project' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { error: 'Request failed' },
      { status: 500 }
    );
  }
}

export async function PUT(
  request: NextRequest,
  props: { params: Promise<{ id: string }> }
) {
  const params = await props.params;
  const searchParams = request.nextUrl.searchParams;
  const userId = searchParams.get('user_id');
  
  if (!userId) {
    return NextResponse.json(
      { error: 'user_id is required' },
      { status: 400 }
    );
  }
  
  if (!params.id) {
    return NextResponse.json(
      { error: 'project slug is required' },
      { status: 400 }
    );
  }
  
  try {
    const body = await request.json();

    const response = await fetch(`${BACKEND_URL}/api/projects/${params.id}?user_id=${userId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Failed to update project' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { error: 'Request failed' },
      { status: 500 }
    );
  }
}

export async function DELETE(
  request: NextRequest,
  props: { params: Promise<{ id: string }> }
) {
  const params = await props.params;
  const searchParams = request.nextUrl.searchParams;
  const userId = searchParams.get('user_id');
  
  if (!userId) {
    return NextResponse.json(
      { error: 'user_id is required' },
      { status: 400 }
    );
  }
  
  if (!params.id) {
    return NextResponse.json(
      { error: 'project slug is required' },
      { status: 400 }
    );
  }
  
  try {
    const response = await fetch(`${BACKEND_URL}/api/projects/${params.id}?user_id=${userId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Failed to delete project' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { error: 'Request failed' },
      { status: 500 }
    );
  }
}
