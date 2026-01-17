/**
 * Simple in-memory cache for API data
 * Caches projects, project details, and API keys
 */

import { Project, APIKey } from './api';

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  expiresIn: number; // milliseconds
}

class DataCache {
  private cache: Map<string, CacheEntry<any>> = new Map();
  private defaultExpiry = 5 * 60 * 1000; // 5 minutes

  private getKey(prefix: string, id?: string): string {
    return id ? `${prefix}:${id}` : prefix;
  }

  set<T>(key: string, data: T, expiresIn?: number): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      expiresIn: expiresIn || this.defaultExpiry,
    });
  }

  get<T>(key: string): T | null {
    const entry = this.cache.get(key);
    if (!entry) return null;

    const age = Date.now() - entry.timestamp;
    if (age > entry.expiresIn) {
      this.cache.delete(key);
      return null;
    }

    return entry.data as T;
  }

  invalidate(pattern: string): void {
    if (pattern.includes('*')) {
      // Pattern matching for wildcards
      const regex = new RegExp(pattern.replace('*', '.*'));
      for (const key of this.cache.keys()) {
        if (regex.test(key)) {
          this.cache.delete(key);
        }
      }
    } else {
      this.cache.delete(pattern);
    }
  }

  clear(): void {
    this.cache.clear();
  }

  // Convenience methods for specific data types
  setProjects(userId: string, projects: Project[]): void {
    this.set(`projects:${userId}`, projects);
  }

  getProjects(userId: string): Project[] | null {
    return this.get<Project[]>(`projects:${userId}`);
  }

  setProject(projectId: string, project: Project): void {
    this.set(`project:${projectId}`, project);
  }

  getProject(projectId: string): Project | null {
    return this.get<Project>(`project:${projectId}`);
  }

  setAPIKeys(projectId: string, keys: APIKey[]): void {
    this.set(`apiKeys:${projectId}`, keys, 2 * 60 * 1000); // 2 minutes for API keys
  }

  getAPIKeys(projectId: string): APIKey[] | null {
    return this.get<APIKey[]>(`apiKeys:${projectId}`);
  }

  invalidateProject(projectId: string): void {
    this.invalidate(`project:${projectId}`);
    this.invalidate(`apiKeys:${projectId}`);
  }

  invalidateProjects(userId: string): void {
    this.invalidate(`projects:${userId}`);
  }
}

export const dataCache = new DataCache();
