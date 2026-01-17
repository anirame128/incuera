"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter, useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Download, RefreshCw, Loader2 } from "lucide-react";
import { toast } from "sonner";

interface SessionData {
  id: string;
  session_id: string;
  url: string;
  started_at: string;
  ended_at?: string;
  event_count: number;
  duration?: number;
  user_id?: string;
  user_email?: string;
}

interface VideoStatus {
  session_id: string;
  status: string;
  video_url?: string;
  video_thumbnail_url?: string;
  video_generated_at?: string;
  video_duration_ms?: number;
  video_size_bytes?: number;
}

export default function SessionReplayPage() {
  const router = useRouter();
  const params = useParams();
  const projectSlug = params.id as string; // Directory is [id], but value is slug
  const sessionId = params.sessionId as string;
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const [session, setSession] = useState<SessionData | null>(null);
  const [videoStatus, setVideoStatus] = useState<VideoStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [regenerating, setRegenerating] = useState(false);
  const lastFetchedRef = useRef<string | null>(null);

  useEffect(() => {
    const storedUser = localStorage.getItem("user");
    if (!storedUser) {
      router.push("/login");
      return;
    }

    // Prevent duplicate calls for the same session (React StrictMode in dev causes double renders)
    const fetchKey = `${projectSlug}-${sessionId}`;
    if (lastFetchedRef.current === fetchKey) {
      return;
    }
    lastFetchedRef.current = fetchKey;

    fetchData();

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectSlug, sessionId]);

  const fetchData = async () => {
    setLoading(true);

    // Fetch session events to get session data
    try {
      const eventsResponse = await fetch(
        `/api/sessions/${encodeURIComponent(sessionId)}/events`
      );
      if (eventsResponse.ok) {
        const data = await eventsResponse.json();
        setSession(data.session);
      }
    } catch (error) {
      console.error("Failed to fetch session:", error);
    }

    // Fetch video status
    await fetchVideoStatus();
    setLoading(false);
  };

  const fetchVideoStatus = async () => {
    try {
      const videoResponse = await fetch(
        `/api/sessions/${encodeURIComponent(sessionId)}/video`
      );
      if (videoResponse.ok) {
        const data = await videoResponse.json();
        setVideoStatus(data);

        // If processing, start polling
        if (data.status === "processing" && !pollIntervalRef.current) {
          startPolling();
        }
        // If ready or failed, stop polling
        if ((data.status === "ready" || data.status === "failed") && pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }
      }
    } catch (error) {
      console.error("Failed to fetch video status:", error);
    }
  };

  const startPolling = () => {
    pollIntervalRef.current = setInterval(async () => {
      await fetchVideoStatus();
    }, 5000);
  };

  const handleGenerateVideo = async () => {
    setRegenerating(true);
    try {
      const response = await fetch(
        `/api/sessions/${encodeURIComponent(sessionId)}/regenerate-video`,
        { method: "POST" }
      );

      if (response.ok) {
        const data = await response.json();
        if (data.video_job_queued) {
          toast.success("Video generation started");
          setVideoStatus((prev) => prev ? { ...prev, status: "processing" } : null);
          startPolling();
        } else {
          toast.error("Failed to queue video generation");
        }
      } else {
        toast.error("Failed to generate video");
      }
    } catch (error) {
      toast.error("Failed to generate video");
    } finally {
      setRegenerating(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const config: Record<string, { variant: "default" | "secondary" | "destructive" | "outline"; label: string; className: string }> = {
      active: { variant: "default", label: "Recording", className: "bg-green-100 text-green-800" },
      completed: { variant: "secondary", label: "Processing Queued", className: "bg-blue-100 text-blue-800" },
      processing: { variant: "outline", label: "Generating Video...", className: "bg-yellow-100 text-yellow-800" },
      ready: { variant: "default", label: "Ready", className: "bg-purple-100 text-purple-800" },
      failed: { variant: "destructive", label: "Failed", className: "" },
    };

    const { variant, label, className } = config[status] || config.active;

    return (
      <Badge variant={variant} className={className}>
        {status === "processing" && <Loader2 className="w-3 h-3 mr-1 animate-spin" />}
        {label}
      </Badge>
    );
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds) return "N/A";
    const totalSeconds = Math.round(seconds); // Round to nearest second
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const formatBytes = (bytes?: number) => {
    if (!bytes) return "N/A";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-12 w-12 animate-spin rounded-full border-4 border-gray-200 border-t-indigo-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push(`/dashboard/projects/${projectSlug}/sessions`)}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Session Replay</h2>
            <p className="text-sm text-muted-foreground truncate max-w-md">
              {session?.session_id}
            </p>
          </div>
        </div>
        {videoStatus && getStatusBadge(videoStatus.status)}
      </div>

      {/* Session Info */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Session Details</CardTitle>
          <CardDescription className="truncate">{session?.url}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Started</p>
              <p className="font-medium">
                {session?.started_at
                  ? new Date(session.started_at).toLocaleString()
                  : "N/A"}
              </p>
            </div>
            <div>
              <p className="text-muted-foreground">Events</p>
              <p className="font-medium">{session?.event_count || 0}</p>
            </div>
            <div>
              <p className="text-muted-foreground">User</p>
              <p className="font-medium truncate">
                {session?.user_email || session?.user_id || "Anonymous"}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Video Player */}
      <Card>
        <CardContent className="pt-6">
          {videoStatus?.status === "processing" ? (
            <div className="flex flex-col items-center justify-center py-16 gap-4">
              <div className="relative">
                <div className="h-16 w-16 animate-spin rounded-full border-4 border-gray-200 border-t-indigo-600" />
              </div>
              <div className="text-center">
                <p className="font-medium text-gray-900">Generating Video</p>
                <p className="text-sm text-muted-foreground mt-1">
                  This may take a few minutes depending on session length...
                </p>
              </div>
            </div>
          ) : videoStatus?.status === "ready" && videoStatus.video_url ? (
            <div className="space-y-4">
              <div className="flex justify-center bg-black rounded-lg overflow-hidden">
                <video
                  controls
                  autoPlay={false}
                  className="max-w-full"
                  poster={videoStatus.video_thumbnail_url}
                  style={{ maxHeight: "600px" }}
                >
                  <source src={videoStatus.video_url} type="video/webm" />
                  <source src={videoStatus.video_url} type="video/mp4" />
                  Your browser does not support the video tag.
                </video>
              </div>

              <div className="flex items-center justify-between border-t pt-4">
                <div className="flex gap-4 text-sm text-muted-foreground">
                  <span>Size: {formatBytes(videoStatus.video_size_bytes)}</span>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={async () => {
                      if (videoStatus.video_url) {
                        try {
                          const response = await fetch(videoStatus.video_url);
                          const blob = await response.blob();
                          const url = window.URL.createObjectURL(blob);
                          const a = document.createElement("a");
                          a.href = url;
                          a.download = `session-${sessionId}-replay.webm`;
                          document.body.appendChild(a);
                          a.click();
                          window.URL.revokeObjectURL(url);
                          document.body.removeChild(a);
                        } catch (error) {
                          console.error("Download failed:", error);
                          toast.error("Failed to download video");
                        }
                      }
                    }}
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Download
                  </Button>
                </div>
              </div>
            </div>
          ) : videoStatus?.status === "failed" ? (
            <div className="flex flex-col items-center justify-center py-16 gap-4">
              <div className="rounded-full bg-red-100 p-4">
                <svg className="h-8 w-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
              <div className="text-center">
                <p className="font-medium text-gray-900">Video Generation Failed</p>
                <p className="text-sm text-muted-foreground mt-1">
                  There was an error generating the video. Please try again.
                </p>
              </div>
              <Button onClick={handleGenerateVideo} disabled={regenerating}>
                <RefreshCw className={`h-4 w-4 mr-2 ${regenerating ? "animate-spin" : ""}`} />
                Try Again
              </Button>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-16 gap-4">
              <div className="rounded-full bg-slate-100 p-4">
                <svg className="h-8 w-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </div>
              <div className="text-center">
                <p className="font-medium text-gray-900">No Video Yet</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Generate a video to watch this session replay
                </p>
              </div>
              <Button onClick={handleGenerateVideo} disabled={regenerating || (session?.event_count || 0) === 0}>
                {regenerating ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                )}
                Generate Video
              </Button>
              {(session?.event_count || 0) === 0 && (
                <p className="text-xs text-amber-600">
                  This session has no recorded events
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
