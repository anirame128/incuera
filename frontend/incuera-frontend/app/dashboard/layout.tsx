'use client';

import { useState, createContext, useContext, useEffect, Fragment, type ReactNode } from 'react';
import { usePathname } from 'next/navigation';
import { AppSidebar } from '@/components/app-sidebar';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';
import { Separator } from '@/components/ui/separator';
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from '@/components/ui/sidebar';
import { NewProjectDialog } from '@/components/new-project-dialog';
import { Project } from '@/lib/api';
import { useProjects } from '@/hooks/use-queries';
import { useQueryClient } from '@tanstack/react-query';

// Context to share dialog state between sidebar and pages
const NewProjectDialogContext = createContext<{
  open: boolean;
  setOpen: (open: boolean) => void;
  refreshProjects: () => void;
}>({
  open: false,
  setOpen: () => { },
  refreshProjects: () => { },
});

export const useNewProjectDialog = () => useContext(NewProjectDialogContext);

export default function DashboardLayout({
  children,
}: {
  children: ReactNode;
}) {
  const pathname = usePathname();
  const [newProjectDialogOpen, setNewProjectDialogOpen] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  useEffect(() => {
    // Only access localStorage on client mount
    setUserId(localStorage.getItem('userId'));
  }, []);

  const { data: projects = [] } = useProjects(userId);

  // Extract project slug from pathname
  const projectSlugMatch = pathname.match(/\/dashboard\/projects\/([^\/]+)/);
  const currentProjectSlug = projectSlugMatch ? projectSlugMatch[1] : null;
  const currentProject = projects.find(p => p.slug === currentProjectSlug);

  const handleProjectCacheInvalidation = () => {
    if (userId) {
      queryClient.invalidateQueries({ queryKey: ['projects', userId] });
    }
  };

  // Build breadcrumb based on pathname
  const getBreadcrumbs = () => {
    const paths = pathname.split('/').filter(Boolean);
    const breadcrumbs = [];

    if (paths[0] === 'dashboard') {
      // Only show Dashboard if we're not on a project page
      if (paths[1] !== 'projects' || !paths[2]) {
        breadcrumbs.push({ label: 'Dashboard', href: '/dashboard' });
      } else {
        // On a project page
        breadcrumbs.push({ label: 'Projects', href: '/dashboard' });
        // Use project name if available, otherwise fallback to "Project"
        const projectName = currentProject?.name || 'Project';
        breadcrumbs.push({ label: projectName, href: `/dashboard/projects/${currentProjectSlug || paths[2]}` });

        if (paths[3] === 'sessions') {
          breadcrumbs.push({ label: 'Sessions', href: pathname });
        } else if (paths[2] && !paths[3]) {
          breadcrumbs.push({ label: 'Settings', href: pathname });
        }
      }
    }

    return breadcrumbs;
  };

  const breadcrumbs = getBreadcrumbs();

  return (
    <NewProjectDialogContext.Provider value={{
      open: newProjectDialogOpen,
      setOpen: setNewProjectDialogOpen,
      refreshProjects: handleProjectCacheInvalidation,
    }}>
      <NewProjectDialog
        open={newProjectDialogOpen}
        onOpenChange={setNewProjectDialogOpen}
        onProjectCreated={handleProjectCacheInvalidation}
      />
      <SidebarProvider>
        <AppSidebar />
        <SidebarInset>
          <header className="flex h-16 shrink-0 items-center transition-[width,height] ease-linear group-has-data-[collapsible=icon]/sidebar-wrapper:h-12">
            <div className="flex items-center gap-3 px-4">
              <SidebarTrigger className="-ml-1" />
              <Separator
                orientation="vertical"
                className="h-4"
              />
              <Breadcrumb>
                <BreadcrumbList className="gap-2">
                  {breadcrumbs.map((crumb, index) => (
                    <Fragment key={`${crumb.href}-${index}`}>
                      {index > 0 && <BreadcrumbSeparator className="hidden md:block" />}
                      <BreadcrumbItem className={index === breadcrumbs.length - 1 ? '' : 'hidden md:block'}>
                        {index === breadcrumbs.length - 1 ? (
                          <BreadcrumbPage>{crumb.label}</BreadcrumbPage>
                        ) : (
                          <BreadcrumbLink href={crumb.href}>
                            {crumb.label}
                          </BreadcrumbLink>
                        )}
                      </BreadcrumbItem>
                    </Fragment>
                  ))}
                </BreadcrumbList>
              </Breadcrumb>
            </div>
          </header>
          <div className="flex flex-1 flex-col gap-4 p-4 md:p-6">
            {children}
          </div>
        </SidebarInset>
      </SidebarProvider>
    </NewProjectDialogContext.Provider>
  );
}
