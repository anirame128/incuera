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
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ArrowLeft, Download, RefreshCw, Loader2, Brain, MousePointerClick, TrendingUp, AlertTriangle, BarChart3 } from "lucide-react";
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

interface AnalysisData {
  session_id: string;
  analysis_status: string;
  analysis_completed_at?: string;
  session_summary?: string;
  interaction_heatmap?: {
    clicks?: Array<{ timestamp_ms: number; x: number; y: number; element?: string }>;
    hovers?: Array<{ timestamp_ms: number; x: number; y: number; duration_ms?: number }>;
    scrolls?: Array<{ timestamp_ms: number; depth_percent?: number }>;
  };
  conversion_funnel?: {
    steps?: Array<{ step: string; timestamp_ms: number; duration_ms: number }>;
    completed: boolean;
    drop_off_step?: string | null;
  };
  error_events?: Array<{ timestamp_ms: number; type: string; description: string }>;
  action_counts?: {
    clicks?: number;
    scrolls?: number;
    form_interactions?: number;
    page_navigations?: number;
    button_presses?: number;
  };
  molmo_analysis_metadata?: {
    model_id?: string;
    processing_time?: number;
  };
}

export default function SessionReplayPage() {
  const router = useRouter();
  const params = useParams();
  const projectSlug = params.id as string; // Directory is [id], but value is slug
  const sessionId = params.sessionId as string;
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const [session, setSession] = useState<SessionData | null>(null);
  const [videoStatus, setVideoStatus] = useState<VideoStatus | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null);
  const [loading, setLoading] = useState(true);
  const [regenerating, setRegenerating] = useState(false);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const lastFetchedRef = useRef<string | null>(null);
  const analysisPollIntervalRef = useRef<NodeJS.Timeout | null>(null);

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
      if (analysisPollIntervalRef.current) {
        clearInterval(analysisPollIntervalRef.current);
        analysisPollIntervalRef.current = null;
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
    
    // Fetch analysis data if video is ready
    if (videoStatus?.status === "ready" || videoStatus?.video_url) {
      await fetchAnalysis();
      // Auto-trigger analysis if it hasn't started yet
      await triggerAnalysisIfNeeded();
    }
    
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
        
        // If video is ready, fetch analysis and auto-trigger if needed
        if (data.status === "ready" || data.video_url) {
          await fetchAnalysis();
          // Auto-trigger analysis if it hasn't started yet
          await triggerAnalysisIfNeeded();
        }
      }
    } catch (error) {
      console.error("Failed to fetch video status:", error);
    }
  };

  const fetchAnalysis = async () => {
    if (analysisLoading) return;
    
    setAnalysisLoading(true);
    try {
      const analysisResponse = await fetch(
        `/api/sessions/${encodeURIComponent(sessionId)}/analysis`
      );
      if (analysisResponse.ok) {
        const data = await analysisResponse.json();
        setAnalysis(data);
        
        // If analysis is processing, start polling
        if (data.analysis_status === "processing" && !analysisPollIntervalRef.current) {
          startAnalysisPolling();
        }
        // If completed or failed, stop polling
        if ((data.analysis_status === "completed" || data.analysis_status === "failed") && analysisPollIntervalRef.current) {
          clearInterval(analysisPollIntervalRef.current);
          analysisPollIntervalRef.current = null;
        }
      }
    } catch (error) {
      console.error("Failed to fetch analysis:", error);
    } finally {
      setAnalysisLoading(false);
    }
  };

  const startAnalysisPolling = () => {
    analysisPollIntervalRef.current = setInterval(async () => {
      await fetchAnalysis();
    }, 10000); // Poll every 10 seconds for analysis
  };

  const triggerAnalysisIfNeeded = async () => {
    // Automatically trigger analysis if video is ready but analysis hasn't started
    if (
      videoStatus?.status === "ready" &&
      videoStatus?.video_url &&
      (!analysis || analysis.analysis_status === "pending" || !analysis.analysis_status)
    ) {
      try {
        const response = await fetch(
          `/api/sessions/${encodeURIComponent(sessionId)}/analyze`,
          { method: "POST" }
        );

        if (response.ok) {
          const data = await response.json();
          if (data.analysis_job_queued) {
            // Silently start analysis - no toast notification
            setAnalysis((prev) => prev ? { ...prev, analysis_status: "processing" } : {
              session_id: sessionId,
              analysis_status: "processing",
            });
            startAnalysisPolling();
            // Fetch analysis status immediately
            await fetchAnalysis();
          }
        }
      } catch (error) {
        // Silently fail - analysis will be retried on next page load
        console.error("Failed to auto-trigger analysis:", error);
      }
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

      {/* Video Player and Analysis */}
      <Tabs defaultValue="video" className="space-y-4">
        <TabsList>
          <TabsTrigger value="video">Video Replay</TabsTrigger>
          {videoStatus?.status === "ready" && (
            <TabsTrigger value="analysis">
              AI Analysis
              {analysis?.analysis_status === "processing" && (
                <Loader2 className="ml-2 h-3 w-3 animate-spin" />
              )}
              {analysis?.analysis_status === "completed" && (
                <Badge variant="secondary" className="ml-2 h-4 px-1.5 text-xs">Ready</Badge>
              )}
            </TabsTrigger>
          )}
        </TabsList>

        <TabsContent value="video">
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
          ) : (videoStatus?.status === "ready" || videoStatus?.video_url) ? (
            <div className="space-y-4">
              <div className="flex justify-center bg-black rounded-lg overflow-hidden">
                <video
                  key={videoStatus.video_url}
                  controls
                  playsInline
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
          ) : (videoStatus?.status === "completed" || videoStatus?.status === "ending") ? (
            <div className="flex flex-col items-center justify-center py-16 gap-4">
              <div className="relative">
                <div className="h-16 w-16 animate-spin rounded-full border-4 border-gray-200 border-t-indigo-600" />
              </div>
              <div className="text-center">
                <p className="font-medium text-gray-900">
                  {videoStatus?.status === "ending" ? "Finalizing Session" : "Video Queued"}
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  {videoStatus?.status === "ending"
                    ? "Waiting for grace period to end..."
                    : "Video generation is queued and will start soon..."}
                </p>
              </div>
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
        </TabsContent>

        {videoStatus?.status === "ready" && (
          <TabsContent value="analysis">
            <div className="space-y-6">
              {/* Analysis Status */}
              {analysisLoading && !analysis ? (
                <Card>
                  <CardContent className="py-12">
                    <div className="flex flex-col items-center justify-center gap-4">
                      <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
                      <p className="text-sm text-muted-foreground">Loading analysis...</p>
                    </div>
                  </CardContent>
                </Card>
              ) : analysis?.analysis_status === "processing" ? (
                <Card>
                  <CardContent className="py-12">
                    <div className="flex flex-col items-center justify-center gap-4">
                      <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
                      <div className="text-center">
                        <p className="font-medium text-gray-900">Analyzing Video</p>
                        <p className="text-sm text-muted-foreground mt-1">
                          AI is analyzing the session replay. This may take a few minutes...
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ) : analysis?.analysis_status === "completed" ? (
                <>
                  {/* Session Summary */}
                  {analysis.session_summary && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <Brain className="h-5 w-5" />
                          Session Summary
                        </CardTitle>
                        <CardDescription>
                          AI-generated summary of the user's journey
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <p className="text-sm leading-relaxed whitespace-pre-wrap">
                          {analysis.session_summary}
                        </p>
                      </CardContent>
                    </Card>
                  )}

                  {/* Action Counts */}
                  {analysis.action_counts && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <BarChart3 className="h-5 w-5" />
                          Action Metrics
                        </CardTitle>
                        <CardDescription>
                          Quantified user interactions
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                          {analysis.action_counts.clicks !== undefined && (
                            <div className="text-center p-4 rounded-lg bg-muted">
                              <p className="text-2xl font-bold">{analysis.action_counts.clicks}</p>
                              <p className="text-xs text-muted-foreground mt-1">Clicks</p>
                            </div>
                          )}
                          {analysis.action_counts.scrolls !== undefined && (
                            <div className="text-center p-4 rounded-lg bg-muted">
                              <p className="text-2xl font-bold">{analysis.action_counts.scrolls}</p>
                              <p className="text-xs text-muted-foreground mt-1">Scrolls</p>
                            </div>
                          )}
                          {analysis.action_counts.form_interactions !== undefined && (
                            <div className="text-center p-4 rounded-lg bg-muted">
                              <p className="text-2xl font-bold">{analysis.action_counts.form_interactions}</p>
                              <p className="text-xs text-muted-foreground mt-1">Form Fields</p>
                            </div>
                          )}
                          {analysis.action_counts.page_navigations !== undefined && (
                            <div className="text-center p-4 rounded-lg bg-muted">
                              <p className="text-2xl font-bold">{analysis.action_counts.page_navigations}</p>
                              <p className="text-xs text-muted-foreground mt-1">Pages</p>
                            </div>
                          )}
                          {analysis.action_counts.button_presses !== undefined && (
                            <div className="text-center p-4 rounded-lg bg-muted">
                              <p className="text-2xl font-bold">{analysis.action_counts.button_presses}</p>
                              <p className="text-xs text-muted-foreground mt-1">Buttons</p>
                            </div>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {/* Conversion Funnel */}
                  {analysis.conversion_funnel && analysis.conversion_funnel.steps && analysis.conversion_funnel.steps.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <TrendingUp className="h-5 w-5" />
                          Conversion Funnel
                        </CardTitle>
                        <CardDescription>
                          User journey through the website
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-3">
                          {analysis.conversion_funnel.steps.map((step, index) => (
                            <div key={index} className="flex items-center gap-4">
                              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center text-sm font-semibold">
                                {index + 1}
                              </div>
                              <div className="flex-1">
                                <p className="font-medium capitalize">{step.step}</p>
                                <p className="text-xs text-muted-foreground">
                                  {formatDuration(step.duration_ms / 1000)} • {new Date(step.timestamp_ms).toLocaleTimeString()}
                                </p>
                              </div>
                            </div>
                          ))}
                          <Separator className="my-4" />
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-medium">
                              Status: {analysis.conversion_funnel.completed ? (
                                <Badge variant="default" className="ml-2">Completed</Badge>
                              ) : (
                                <Badge variant="secondary" className="ml-2">Abandoned</Badge>
                              )}
                            </span>
                            {analysis.conversion_funnel.drop_off_step && (
                              <span className="text-sm text-muted-foreground">
                                Dropped off at: <span className="font-medium capitalize">{analysis.conversion_funnel.drop_off_step}</span>
                              </span>
                            )}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {/* Interaction Heatmap Info */}
                  {analysis.interaction_heatmap && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <MousePointerClick className="h-5 w-5" />
                          Interaction Heatmap
                        </CardTitle>
                        <CardDescription>
                          User interaction locations and patterns
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          {analysis.interaction_heatmap.clicks && analysis.interaction_heatmap.clicks.length > 0 && (
                            <div className="p-4 rounded-lg border">
                              <p className="text-sm font-medium">Clicks</p>
                              <p className="text-2xl font-bold mt-1">{analysis.interaction_heatmap.clicks.length}</p>
                              <p className="text-xs text-muted-foreground mt-1">Total click events</p>
                            </div>
                          )}
                          {analysis.interaction_heatmap.hovers && analysis.interaction_heatmap.hovers.length > 0 && (
                            <div className="p-4 rounded-lg border">
                              <p className="text-sm font-medium">Hovers</p>
                              <p className="text-2xl font-bold mt-1">{analysis.interaction_heatmap.hovers.length}</p>
                              <p className="text-xs text-muted-foreground mt-1">Hover events detected</p>
                            </div>
                          )}
                          {analysis.interaction_heatmap.scrolls && analysis.interaction_heatmap.scrolls.length > 0 && (
                            <div className="p-4 rounded-lg border">
                              <p className="text-sm font-medium">Scrolls</p>
                              <p className="text-2xl font-bold mt-1">{analysis.interaction_heatmap.scrolls.length}</p>
                              <p className="text-xs text-muted-foreground mt-1">Scroll events</p>
                            </div>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground mt-4">
                          Note: Full heatmap visualization with coordinate overlays can be implemented in a future update.
                        </p>
                      </CardContent>
                    </Card>
                  )}

                  {/* Error Events */}
                  {analysis.error_events && analysis.error_events.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <AlertTriangle className="h-5 w-5 text-amber-600" />
                          Error Events
                        </CardTitle>
                        <CardDescription>
                          Detected errors and anomalies
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-3">
                          {analysis.error_events.map((error, index) => (
                            <div key={index} className="p-3 rounded-lg border border-amber-200 bg-amber-50">
                              <div className="flex items-start justify-between">
                                <div className="flex-1">
                                  <p className="text-sm font-medium capitalize">{error.type}</p>
                                  <p className="text-xs text-muted-foreground mt-1">{error.description}</p>
                                </div>
                                <Badge variant="outline" className="ml-2">
                                  {new Date(error.timestamp_ms).toLocaleTimeString()}
                                </Badge>
                              </div>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {/* Analysis Metadata */}
                  {analysis.molmo_analysis_metadata && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-sm">Analysis Metadata</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-xs text-muted-foreground space-y-1">
                          {analysis.molmo_analysis_metadata.model_id && (
                            <p>Model: {analysis.molmo_analysis_metadata.model_id}</p>
                          )}
                          {analysis.analysis_completed_at && (
                            <p>Completed: {new Date(analysis.analysis_completed_at).toLocaleString()}</p>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </>
              ) : analysis?.analysis_status === "failed" ? (
                <Card>
                  <CardContent className="py-12">
                    <div className="flex flex-col items-center justify-center gap-4">
                      <AlertTriangle className="h-8 w-8 text-red-500" />
                      <div className="text-center">
                        <p className="font-medium text-gray-900">Analysis Failed</p>
                        <p className="text-sm text-muted-foreground mt-1">
                          There was an error analyzing the video.
                        </p>
                        {analysis.molmo_analysis_metadata?.error && (
                          <div className="mt-4 p-3 rounded-lg bg-red-50 border border-red-200 max-w-2xl">
                            <p className="text-xs font-medium text-red-900 mb-1">Error Details:</p>
                            <p className="text-xs text-red-700 break-words">
                              {analysis.molmo_analysis_metadata.error}
                            </p>
                            {analysis.molmo_analysis_metadata.error_type && (
                              <p className="text-xs text-red-600 mt-1">
                                Type: {analysis.molmo_analysis_metadata.error_type}
                              </p>
                            )}
                          </div>
                        )}
                        <p className="text-xs text-muted-foreground mt-4">
                          Analysis will be retried automatically when you refresh the page.
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ) : (
                <Card>
                  <CardContent className="py-12">
                    <div className="flex flex-col items-center justify-center gap-4">
                      <Brain className="h-8 w-8 text-muted-foreground" />
                      <div className="text-center">
                        <p className="font-medium text-gray-900">Analysis Pending</p>
                        <p className="text-sm text-muted-foreground mt-1">
                          Analysis will start automatically. Please wait...
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}
