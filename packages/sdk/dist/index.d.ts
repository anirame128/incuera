interface IncueraConfig {
    apiKey?: string;
    apiHost: string;
    userId?: string;
    userEmail?: string;
    maxEventsPerSession?: number;
}
declare class Incuera {
    private config;
    private sessionId;
    private events;
    private stopRecording?;
    private uploadInterval?;
    private heartbeatInterval?;
    private isRecording;
    private totalEventCount;
    private maxEvents;
    private isRestarting;
    constructor(config: IncueraConfig);
    /**
     * Start recording the session
     */
    init(): void;
    /**
     * Handle page unload - flush events and signal session end
     */
    private handlePageUnload;
    /**
     * Handle page hide (mobile browsers)
     */
    private handlePageHide;
    /**
     * Handle visibility change (tab switch, minimize)
     */
    private handleVisibilityChange;
    /**
     * Manually flush events to server
     */
    private flush;
    /**
     * Upload events to backend
     */
    private uploadEvents;
    /**
     * Send session metadata on init
     */
    private sendSessionMetadata;
    /**
     * Send heartbeat to keep session active
     */
    private sendHeartbeat;
    /**
     * Handle session finalized - create a new session seamlessly
     * This is called when the backend indicates the previous session is finalized
     * (video generation started or complete)
     */
    private handleSessionFinalized;
    /**
     * Signal session end to trigger video generation
     */
    private signalSessionEnd;
    /**
     * Stop recording and cleanup
     */
    stop(): void;
    /**
     * Get current session ID
     */
    getSessionId(): string;
    /**
     * Get current event count
     */
    getEventCount(): number;
    /**
     * Get or create session ID (persisted in localStorage)
     * Creates a new session when:
     - No existing session ID in storage
     - Session is older than 30 minutes (new page visit)
     */
    private getOrCreateSessionId;
    /**
     * Generate unique session ID
     */
    private generateSessionId;
    /**
     * Identify user (call this after user logs in)
     */
    identify(userId: string, userEmail?: string): void;
}

export { Incuera as default };
