import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient, Project, APIKey, Session } from '@/lib/api';

// Query Keys
export const queryKeys = {
    projects: (userId: string) => ['projects', userId],
    project: (projectId: string) => ['project', projectId],
    apiKeys: (projectId: string) => ['apiKeys', projectId],
    sessions: (projectId: string) => ['sessions', projectId],
};

// Projects
export function useProjects(userId: string | null) {
    return useQuery({
        queryKey: queryKeys.projects(userId || ''),
        queryFn: () => apiClient.getProjects(userId!),
        enabled: !!userId,
    });
}

export function useProject(projectId: string) {
    return useQuery({
        queryKey: queryKeys.project(projectId),
        queryFn: () => apiClient.getProject(projectId),
        enabled: !!projectId,
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
        mutationFn: (data: { id: string; name: string; domain?: string }) =>
            apiClient.updateProject(data.id, data.name, data.domain),
        onSuccess: (updatedProject) => {
            queryClient.setQueryData(queryKeys.project(updatedProject.id), updatedProject);
            queryClient.invalidateQueries({ queryKey: queryKeys.projects('') }); // Optimistic update might be better but this is fine
            // Ideally we should know the userId to invalidate the list more precisely, 
            // but 'projects' key usually needs a userId. 
            // We can invalidate all 'projects' queries or pass userId in variables.
        },
    });
}

export function useDeleteProject() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (projectId: string) => apiClient.deleteProject(projectId),
        onSuccess: (_, projectId) => {
            // We can't easily invalidate the specific user's project list without the userId here.
            // But typically we redirect after delete anyway.
            // A 'soft' invalidation of everything 'projects' works:
            queryClient.invalidateQueries({ queryKey: ['projects'] });
            queryClient.removeQueries({ queryKey: queryKeys.project(projectId) });
        },
    });
}

// API Keys
export function useAPIKeys(projectId: string) {
    return useQuery({
        queryKey: queryKeys.apiKeys(projectId),
        queryFn: () => apiClient.getAPIKeys(projectId),
        enabled: !!projectId,
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
        mutationFn: (data: { keyId: string; projectId: string }) =>
            apiClient.deleteAPIKey(data.keyId),
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({ queryKey: queryKeys.apiKeys(variables.projectId) });
        },
    });
}

// Sessions
export function useSessions(projectId: string) {
    return useQuery({
        queryKey: queryKeys.sessions(projectId),
        queryFn: () => apiClient.getSessions(projectId),
        enabled: !!projectId,
    });
}
