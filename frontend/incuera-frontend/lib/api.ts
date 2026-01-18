/**
 * API client for communicating with the backend
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface User {
  id: string;
  email: string;
  name: string | null;
  created_at: string;
}

export interface Project {
  id: string;
  user_id: string;
  name: string;
  slug: string;
  domain: string | null;
  created_at: string;
}

export interface APIKey {
  id: string;
  project_id: string;
  key_prefix: string;
  name: string;
  is_active: boolean;
  last_used_at: string | null;
  created_at: string;
}

export interface Session {
  id: string;
  session_id: string;
  project_id: string;
  user_id: string | null;
  user_email: string | null;
  url: string;
  started_at: string;
  event_count: number;
  duration?: number;
}

class ApiClient {
  private getUserId(): string | null {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('userId');
    }
    return null;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    // Use relative paths to hit Next.js API routes which proxy to backend
    let url = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    
    // Add user_id to query params if not already present
    const userId = this.getUserId();
    if (userId && !url.includes('user_id=')) {
      const separator = url.includes('?') ? '&' : '?';
      url = `${url}${separator}user_id=${userId}`;
    }
    
    // Add user_id to headers for endpoints that need it
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> || {}),
    };
    
    if (userId && !headers['X-User-ID']) {
      headers['X-User-ID'] = userId;
    }
    
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Request failed' }));
      throw new Error(error.message || `HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  // Projects
  async getProjects(userId: string): Promise<Project[]> {
    return this.request(`/api/projects?user_id=${userId}`);
  }

  async createProject(name: string, domain?: string, userId?: string): Promise<Project> {
    const storedUserId = userId || localStorage.getItem('userId');
    if (!storedUserId) {
      throw new Error('User ID is required');
    }
    return this.request('/api/projects', {
      method: 'POST',
      body: JSON.stringify({ name, domain, user_id: storedUserId }),
    });
  }

  async getProject(projectSlug: string): Promise<Project> {
    return this.request(`/api/projects/${projectSlug}`);
  }

  async updateProject(projectSlug: string, name: string, domain?: string): Promise<Project> {
    return this.request(`/api/projects/${projectSlug}`, {
      method: 'PUT',
      body: JSON.stringify({ name, domain }),
    });
  }

  async deleteProject(projectSlug: string): Promise<void> {
    return this.request(`/api/projects/${projectSlug}`, {
      method: 'DELETE',
    });
  }

  // API Keys
  async getAPIKeys(projectSlug: string): Promise<APIKey[]> {
    // user_id is automatically added by the request method
    return this.request(`/api/api-keys?project_slug=${projectSlug}`);
  }

  async createAPIKey(projectId: string, name: string): Promise<{ key: string; apiKey: APIKey }> {
    return this.request('/api/api-keys', {
      method: 'POST',
      body: JSON.stringify({ project_id: projectId, name }),
    });
  }

  async deleteAPIKey(keyId: string): Promise<void> {
    return this.request(`/api/api-keys/${keyId}`, {
      method: 'DELETE',
    });
  }

  // Sessions
  async getSessions(projectSlug: string): Promise<Session[]> {
    return this.request(`/api/sessions?project_slug=${projectSlug}`);
  }
}

export const apiClient = new ApiClient();
