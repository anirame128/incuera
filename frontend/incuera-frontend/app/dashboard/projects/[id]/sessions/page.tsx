'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useTheme } from 'next-themes';
import { Session } from '@/lib/api';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { MagicCard } from '@/components/ui/magic-card';
import { Play, Video, Clock, MousePointer } from 'lucide-react';

interface SessionWithStatus extends Session {
  status?: string;
}

export default function SessionsPage() {
  const router = useRouter();
  const params = useParams();
  const { theme } = useTheme();
  const projectId = params.id as string;

  const [sessions, setSessions] = useState<SessionWithStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [apiKey, setApiKey] = useState<string>('');

  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    if (!storedUser) {
      router.push('/login');
      return;
    }

    fetchAPIKey();
  }, [projectId, router]);

  const fetchAPIKey = async () => {
    try {
      const response = await fetch(`/api/api-keys?project_id=${projectId}`);
      if (response.ok) {
        const keys = await response.json();
        const activeKey = keys.find((k: any) => k.is_active);
        if (activeKey) {
          const storedKey = localStorage.getItem(`apiKey_${projectId}`);
          if (storedKey) {
            setApiKey(storedKey);
            fetchSessions(storedKey);
          } else {
            fetchSessions('');
          }
        } else {
          fetchSessions('');
        }
      } else {
        fetchSessions('');
      }
    } catch (error) {
      fetchSessions('');
    }
  };

  const fetchSessions = async (key: string) => {
    try {
      const response = await fetch(`/api/sessions?project_id=${projectId}`, {
        headers: {
          'X-API-Key': key,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setSessions(data);
      } else {
        const errorData = await response.json().catch(() => ({}));
        console.error('Failed to fetch sessions:', response.status, errorData);
        setSessions([]);
      }
    } catch (error) {
      console.error('Error fetching sessions:', error);
      setSessions([]);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status?: string) => {
    if (!status) return null;

    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      active: "default",
      completed: "secondary",
      processing: "outline",
      ready: "default",
      failed: "destructive",
    };

    const labels: Record<string, string> = {
      active: "Recording",
      completed: "Completed",
      processing: "Processing",
      ready: "Video Ready",
      failed: "Failed",
    };

    const colors: Record<string, string> = {
      active: "bg-green-100 text-green-800 border-green-200",
      completed: "bg-blue-100 text-blue-800 border-blue-200",
      processing: "bg-yellow-100 text-yellow-800 border-yellow-200",
      ready: "bg-purple-100 text-purple-800 border-purple-200",
      failed: "bg-red-100 text-red-800 border-red-200",
    };

    return (
      <Badge
        variant={variants[status] || "secondary"}
        className={colors[status] || ""}
      >
        {status === "ready" && <Video className="w-3 h-3 mr-1" />}
        {labels[status] || status}
      </Badge>
    );
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds) return null;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const handleViewReplay = (sessionId: string) => {
    router.push(`/dashboard/projects/${projectId}/sessions/${encodeURIComponent(sessionId)}`);
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Sessions</h2>
        <p className="text-sm text-muted-foreground">
          {sessions.length} session{sessions.length !== 1 ? 's' : ''} recorded
        </p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-gray-200 border-t-indigo-600"></div>
        </div>
      ) : sessions.length === 0 ? (
        <Card>
          <CardContent className="p-8 text-center">
            <div className="flex flex-col items-center gap-4">
              <div className="rounded-full bg-slate-100 p-4">
                <MousePointer className="h-8 w-8 text-slate-400" />
              </div>
              <div>
                <p className="font-medium text-slate-900">No sessions recorded yet</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Sessions will appear here once users interact with your site
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {sessions.map((session) => (
            <Card key={session.id} className="border-none p-0 shadow-none">
              <MagicCard
                gradientColor={theme === "dark" ? "#262626" : "#D9D9D955"}
                className="p-0"
              >
                <CardHeader className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <CardTitle className="text-base truncate">
                          {session.session_id.substring(0, 25)}...
                        </CardTitle>
                        {getStatusBadge(session.status)}
                      </div>
                      <CardDescription className="mt-1 truncate">
                        {session.url}
                      </CardDescription>
                      <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {new Date(session.started_at).toLocaleString()}
                        </span>
                        <span>{session.event_count} events</span>
                        {session.duration && (
                          <span>Duration: {formatDuration(session.duration)}</span>
                        )}
                        {session.user_email && (
                          <span className="truncate max-w-[150px]">{session.user_email}</span>
                        )}
                      </div>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleViewReplay(session.session_id)}
                      className="ml-4 shrink-0"
                    >
                      <Play className="h-4 w-4 mr-2" />
                      View Replay
                    </Button>
                  </div>
                </CardHeader>
              </MagicCard>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
