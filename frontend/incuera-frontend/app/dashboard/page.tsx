'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useTheme } from 'next-themes';
import { Project } from '@/lib/api';
import { dataCache } from '@/lib/cache';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { MagicCard } from '@/components/ui/magic-card';
import { NumberTicker } from '@/components/ui/number-ticker';
import { AnimatedShinyText } from '@/components/ui/animated-shiny-text';
import { useNewProjectDialog } from '@/app/dashboard/layout';

export default function DashboardPage() {
  const router = useRouter();
  const { theme } = useTheme();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [userId, setUserId] = useState<string | null>(null);
  const { setOpen: setNewProjectDialogOpen } = useNewProjectDialog();

  useEffect(() => {
    // Check if user is logged in
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


  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">
            <AnimatedShinyText className="!text-gray-900 dark:!text-gray-100">
              Projects
            </AnimatedShinyText>
          </h2>
          {!loading && projects.length > 0 && (
            <p className="text-sm text-gray-600 mt-1">
              <NumberTicker value={projects.length} /> project{projects.length !== 1 ? 's' : ''}
            </p>
          )}
        </div>
        <Button
          onClick={() => setNewProjectDialogOpen(true)}
        >
          New Project
        </Button>
      </div>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="h-12 w-12 animate-spin rounded-full border-4 border-gray-200 border-t-indigo-600"></div>
            </div>
          ) : projects.length === 0 ? (
            <div className="rounded-lg bg-white p-8 text-center shadow">
              <p className="text-gray-600">No projects yet. Create your first project to get started.</p>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {projects.map((project) => (
                <Link
                  key={project.id}
                  href={`/dashboard/projects/${project.id}`}
                  className="block"
                >
                  <Card className="h-full border-none p-0 shadow-none">
                    <MagicCard
                      gradientColor={theme === "dark" ? "#262626" : "#D9D9D955"}
                      className="h-full p-0"
                    >
                      <CardHeader className="p-6">
                        <CardTitle className="text-lg font-semibold">
                          {project.name}
                        </CardTitle>
                        {project.domain && (
                          <CardDescription className="mt-2">
                            {project.domain}
                          </CardDescription>
                        )}
                      </CardHeader>
                      <CardContent className="p-6 pt-0">
                        <p className="text-xs text-muted-foreground">
                          Created {new Date(project.created_at).toLocaleDateString()}
                        </p>
                      </CardContent>
                    </MagicCard>
                  </Card>
                </Link>
              ))}
            </div>
          )}
    </div>
  );
}
