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
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    // Use relative paths to hit Next.js API routes which proxy to backend
    const url = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Request failed' }));
      throw new Error(error.message || `HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  // Authentication
  async login(email: string, password: string): Promise<{ user: User; token?: string }> {
    return this.request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
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

  async getProject(projectId: string): Promise<Project> {
    return this.request(`/api/projects/${projectId}`);
  }

  async updateProject(projectId: string, name: string, domain?: string): Promise<Project> {
    return this.request(`/api/projects/${projectId}`, {
      method: 'PUT',
      body: JSON.stringify({ name, domain }),
    });
  }

  async deleteProject(projectId: string): Promise<void> {
    return this.request(`/api/projects/${projectId}`, {
      method: 'DELETE',
    });
  }

  // API Keys
  async getAPIKeys(projectId: string): Promise<APIKey[]> {
    return this.request(`/api/api-keys?project_id=${projectId}`);
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
  async getSessions(projectId: string): Promise<Session[]> {
    return this.request(`/api/sessions?project_id=${projectId}`);
  }
}

export const apiClient = new ApiClient();
