import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient, Project, APIKey, Session } from '@/lib/api';

// Query Keys
export const queryKeys = {
    projects: (userId: string) => ['projects', userId],
    project: (projectSlug: string) => ['project', projectSlug],
    apiKeys: (projectSlug: string) => ['apiKeys', projectSlug],
    sessions: (projectSlug: string) => ['sessions', projectSlug],
};

// Projects
export function useProjects(userId: string | null) {
    return useQuery({
        queryKey: queryKeys.projects(userId || ''),
        queryFn: () => apiClient.getProjects(userId!),
        enabled: !!userId,
    });
}

export function useProject(projectSlug: string) {
    return useQuery({
        queryKey: queryKeys.project(projectSlug),
        queryFn: () => apiClient.getProject(projectSlug),
        enabled: !!projectSlug,
    });
}

export function useCreateProject() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (data: { name: string; domain?: string; userId?: string }) =>
            apiClient.createProject(data.name, data.domain, data.userId),
        onSuccess: (newProject, variables) => {
            // Invalidate projects list for the user
            const userId = variables.userId || localStorage.getItem('userId');
            if (userId) {
                queryClient.invalidateQueries({ queryKey: queryKeys.projects(userId) });
            }
        },
    });
}

export function useUpdateProject() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (data: { slug: string; name: string; domain?: string }) =>
            apiClient.updateProject(data.slug, data.name, data.domain),
        onSuccess: (updatedProject) => {
            queryClient.setQueryData(queryKeys.project(updatedProject.slug), updatedProject);
            queryClient.invalidateQueries({ queryKey: queryKeys.projects('') });
        },
    });
}

export function useDeleteProject() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (projectSlug: string) => apiClient.deleteProject(projectSlug),
        onSuccess: (_, projectSlug) => {
            queryClient.invalidateQueries({ queryKey: ['projects'] });
            queryClient.removeQueries({ queryKey: queryKeys.project(projectSlug) });
        },
    });
}

// API Keys
export function useAPIKeys(projectSlug: string) {
    return useQuery({
        queryKey: queryKeys.apiKeys(projectSlug),
        queryFn: () => apiClient.getAPIKeys(projectSlug),
        enabled: !!projectSlug,
    });
}

export function useCreateAPIKey() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (data: { projectId: string; name: string }) =>
            apiClient.createAPIKey(data.projectId, data.name),
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({ queryKey: queryKeys.apiKeys(variables.projectId) });
        },
    });
}

export function useDeleteAPIKey() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (data: { keyId: string; projectSlug: string }) =>
            apiClient.deleteAPIKey(data.keyId),
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({ queryKey: queryKeys.apiKeys(variables.projectSlug) });
        },
    });
}

// Sessions
export function useSessions(projectSlug: string) {
    return useQuery({
        queryKey: queryKeys.sessions(projectSlug),
        queryFn: () => apiClient.getSessions(projectSlug),
        enabled: !!projectSlug,
    });
}
