'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useTheme } from 'next-themes';
import {
  FolderIcon,
  SettingsIcon,
  PlayIcon,
  LogOutIcon,
  PlusIcon,
} from 'lucide-react';
import { Project } from '@/lib/api';
import { dataCache } from '@/lib/cache';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarGroupAction,
} from '@/components/ui/sidebar';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { useNewProjectDialog } from '@/app/dashboard/layout';

export function AppSidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const { theme } = useTheme();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [userId, setUserId] = useState<string | null>(null);
  const { setOpen: setNewProjectDialogOpen } = useNewProjectDialog();

  // Extract project ID from pathname
  const projectIdMatch = pathname.match(/\/dashboard\/projects\/([^\/]+)/);
  const currentProjectId = projectIdMatch ? projectIdMatch[1] : null;
  const currentProject = projects.find(p => p.id === currentProjectId);

  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    const storedUserId = localStorage.getItem('userId');
    
    if (!storedUser || !storedUserId) {
      router.push('/login');
      return;
    }

    setUserId(storedUserId);
    fetchProjects(storedUserId);
  }, [router]);

  const fetchProjects = async (userId: string, useCache = true) => {
    // Check cache first
    if (useCache) {
      const cached = dataCache.getProjects(userId);
      if (cached) {
        setProjects(cached);
        setLoading(false);
        return;
      }
    }

    try {
      const response = await fetch(`/api/projects?user_id=${userId}`);
      if (response.ok) {
        const data = await response.json();
        setProjects(data);
        dataCache.setProjects(userId, data);
      }
    } catch (error) {
      // Silently fail
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('user');
    localStorage.removeItem('userId');
    router.push('/login');
  };

  const handleNewProject = () => {
    setNewProjectDialogOpen(true);
  };

  // Refresh projects when pathname changes (e.g., after creating a project)
  useEffect(() => {
    if (userId && pathname === '/dashboard') {
      fetchProjects(userId);
    }
  }, [userId, pathname]);

  return (
    <Sidebar>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <a href="/dashboard">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
                  <FolderIcon className="size-4" />
                </div>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-semibold">Incuera</span>
                  <span className="truncate text-xs">Dashboard</span>
                </div>
              </a>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        {currentProjectId ? (
          // Show project-specific navigation
          <SidebarGroup>
            <SidebarGroupLabel>Project</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    asChild
                    isActive={pathname === `/dashboard/projects/${currentProjectId}`}
                  >
                    <a href={`/dashboard/projects/${currentProjectId}`}>
                      <SettingsIcon />
                      <span>Settings</span>
                    </a>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    asChild
                    isActive={pathname === `/dashboard/projects/${currentProjectId}/sessions`}
                  >
                    <a href={`/dashboard/projects/${currentProjectId}/sessions`}>
                      <PlayIcon />
                      <span>Session Replays</span>
                    </a>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ) : (
          // Show projects list
          <SidebarGroup>
            <SidebarGroupLabel>Projects</SidebarGroupLabel>
            <SidebarGroupAction
              title="New Project"
              onClick={handleNewProject}
            >
              <PlusIcon />
              <span className="sr-only">New Project</span>
            </SidebarGroupAction>
            <SidebarGroupContent>
              {loading ? (
                <SidebarMenu>
                  {[1, 2, 3].map((i) => (
                    <SidebarMenuItem key={i}>
                      <div className="flex items-center gap-2 px-2 py-1.5">
                        <Skeleton className="h-4 w-4" />
                        <Skeleton className="h-4 flex-1" />
                      </div>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              ) : projects.length === 0 ? (
                <div className="px-2 py-4 text-sm text-muted-foreground text-center">
                  No projects yet
                </div>
              ) : (
                <SidebarMenu>
                  {projects.map((project) => (
                    <SidebarMenuItem key={project.id}>
                      <SidebarMenuButton
                        asChild
                        isActive={currentProjectId === project.id}
                      >
                        <a href={`/dashboard/projects/${project.id}`}>
                          <FolderIcon />
                          <span>{project.name}</span>
                        </a>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              )}
            </SidebarGroupContent>
          </SidebarGroup>
        )}
      </SidebarContent>
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" onClick={handleLogout}>
              <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
                <span className="text-xs font-semibold">
                  {userId ? userId.substring(0, 2).toUpperCase() : 'U'}
                </span>
              </div>
              <div className="grid flex-1 text-left text-sm leading-tight">
                <span className="truncate font-semibold">User</span>
                <span className="truncate text-xs">Account</span>
              </div>
              <LogOutIcon className="ml-auto" />
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}
