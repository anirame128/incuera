interface IncueraConfig {
    apiKey?: string;
    apiHost: string;
    userId?: string;
    userEmail?: string;
}
declare class Incuera {
    private config;
    private sessionId;
    private events;
    private stopRecording?;
    private uploadInterval?;
    private isRecording;
    constructor(config: IncueraConfig);
    /**
     * Start recording the session
     */
    init(): void;
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
     * Stop recording and cleanup
     */
    stop(): void;
    /**
     * Get current session ID
     */
    getSessionId(): string;
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
