import { record, type eventWithTime } from 'rrweb'

interface IncueraConfig {
    apiKey?: string  // Optional - not required for development
    apiHost: string
    userId?: string  // Authenticated user ID from your e-commerce store
    userEmail?: string
    maxEventsPerSession?: number  // Maximum events per session (default: 10,000)
}

class Incuera {
    private config: IncueraConfig
    private sessionId: string
    private events: eventWithTime[] = []
    private stopRecording?: () => void
    private uploadInterval?: ReturnType<typeof setInterval>
    private isRecording: boolean = false
    private totalEventCount: number = 0
    private maxEvents: number

    constructor(config: IncueraConfig) {
        this.config = config
        this.sessionId = this.getOrCreateSessionId()
        this.maxEvents = config.maxEventsPerSession ?? 10000
    }

    /**
     * Start recording the session
     */
    init() {
        if (this.isRecording) {
            return
        }

        this.isRecording = true
        this.totalEventCount = 0

        // Start rrweb recording
        this.stopRecording = record({
            emit: (event) => {
                // Check if we've hit the event limit
                if (this.totalEventCount >= this.maxEvents) {
                    console.warn(`[Incuera] Max events (${this.maxEvents}) reached for session`)
                    return
                }

                this.events.push(event)
                this.totalEventCount++

                // Auto-flush when buffer gets large (100 events)
                if (this.events.length >= 100) {
                    this.flush()
                }
            },
            checkoutEveryNms: 15 * 60 * 1000, // Full snapshot every 15 min
            recordCanvas: true,
            collectFonts: true,
            maskAllInputs: false, // We'll handle privacy later
            sampling: {
                mousemove: true,
                scroll: 150, // Emit scroll events every 150ms
                input: 'all',
            },
        })

        // Send initial session metadata
        this.sendSessionMetadata()

        // Auto-flush every 10 seconds
        this.uploadInterval = setInterval(() => this.flush(), 10000)

        // Flush on page unload and signal session end
        if (typeof window !== 'undefined') {
            window.addEventListener('beforeunload', this.handlePageUnload)
            window.addEventListener('pagehide', this.handlePageHide)
            document.addEventListener('visibilitychange', this.handleVisibilityChange)
        }
    }

    /**
     * Handle page unload - flush events and signal session end
     */
    private handlePageUnload = () => {
        this.flush(true)
        this.signalSessionEnd('beforeunload')
    }

    /**
     * Handle page hide (mobile browsers)
     */
    private handlePageHide = (event: PageTransitionEvent) => {
        if (event.persisted) {
            // Page is being cached (bfcache), don't end session
            return
        }
        this.flush(true)
        this.signalSessionEnd('pagehide')
    }

    /**
     * Handle visibility change (tab switch, minimize)
     */
    private handleVisibilityChange = () => {
        if (document.visibilityState === 'hidden') {
            // Flush events when tab becomes hidden
            this.flush(true)
        }
    }

    /**
     * Manually flush events to server
     */
    private async flush(isUnloading: boolean = false) {
        if (this.events.length === 0) return

        const batch = [...this.events]
        this.events = [] // Clear the buffer

        await this.uploadEvents(batch, isUnloading)
    }

    /**
     * Upload events to backend
     */
    private async uploadEvents(events: eventWithTime[], isUnloading: boolean = false) {
        try {
            const headers: Record<string, string> = {
                'Content-Type': 'application/json',
            }

            // Only add API key if provided (optional for development)
            if (this.config.apiKey) {
                headers['X-API-Key'] = this.config.apiKey
            }

            const response = await fetch(`${this.config.apiHost}/api/ingest`, {
                method: 'POST',
                headers,
                body: JSON.stringify({
                    sessionId: this.sessionId,
                    events,
                    timestamp: Date.now(),
                }),
                keepalive: isUnloading, // Critical for beforeunload, but has 64KB limit so only use when needed
            })

            if (!response.ok) {
                throw new Error(`Upload failed: ${response.statusText}`)
            }
        } catch (error) {
            // Re-add events to buffer on failure
            this.events.unshift(...events)
        }
    }

    /**
     * Send session metadata on init
     */
    private async sendSessionMetadata() {
        try {
            const headers: Record<string, string> = {
                'Content-Type': 'application/json',
            }

            // Only add API key if provided (optional for development)
            if (this.config.apiKey) {
                headers['X-API-Key'] = this.config.apiKey
            }

            await fetch(`${this.config.apiHost}/api/sessions/start`, {
                method: 'POST',
                headers,
                body: JSON.stringify({
                    sessionId: this.sessionId,
                    userId: this.config.userId,
                    userEmail: this.config.userEmail,
                    metadata: {
                        url: window.location.href,
                        referrer: document.referrer,
                        userAgent: navigator.userAgent,
                        screen: {
                            width: window.screen.width,
                            height: window.screen.height,
                        },
                        viewport: {
                            width: window.innerWidth,
                            height: window.innerHeight,
                        },
                        timestamp: Date.now(),
                    },
                }),
            })
        } catch (error) {
            // Silently fail metadata send
        }
    }

    /**
     * Signal session end to trigger video generation.
     * API key is included in the body because sendBeacon cannot set custom headers.
     */
    private signalSessionEnd(reason: string) {
        if (!this.isRecording) return

        const body: Record<string, unknown> = {
            sessionId: this.sessionId,
            reason,
            timestamp: Date.now(),
            finalEventCount: this.totalEventCount,
        }
        if (this.config.apiKey) {
            body.apiKey = this.config.apiKey
        }
        const payload = JSON.stringify(body)

        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
        }

        if (this.config.apiKey) {
            headers['X-API-Key'] = this.config.apiKey
        }

        // Use sendBeacon for reliable delivery on page close
        if (typeof navigator !== 'undefined' && navigator.sendBeacon) {
            const blob = new Blob([payload], { type: 'application/json' })
            navigator.sendBeacon(`${this.config.apiHost}/api/sessions/end`, blob)
        } else {
            // Fallback to keepalive fetch
            fetch(`${this.config.apiHost}/api/sessions/end`, {
                method: 'POST',
                headers,
                body: payload,
                keepalive: true,
            }).catch(() => {
                // Silently fail
            })
        }
    }

    /**
     * Stop recording and cleanup
     */
    stop() {
        if (!this.isRecording) return

        if (this.stopRecording) {
            this.stopRecording()
        }

        if (this.uploadInterval) {
            clearInterval(this.uploadInterval)
        }

        // Remove event listeners
        if (typeof window !== 'undefined') {
            window.removeEventListener('beforeunload', this.handlePageUnload)
            window.removeEventListener('pagehide', this.handlePageHide)
            document.removeEventListener('visibilitychange', this.handleVisibilityChange)
        }

        this.flush(true)
        this.signalSessionEnd('manual_stop')
        this.isRecording = false
    }

    /**
     * Get current session ID
     */
    getSessionId(): string {
        return this.sessionId
    }

    /**
     * Get current event count
     */
    getEventCount(): number {
        return this.totalEventCount
    }

    /**
     * Get or create session ID (persisted in localStorage)
     * Creates a new session when:
     - No existing session ID in storage
     - Session is older than 30 minutes (new page visit)
     */
    private getOrCreateSessionId(): string {
        if (typeof window === 'undefined') {
            return this.generateSessionId()
        }

        const STORAGE_KEY = 'incuera_session_id'
        const STORAGE_TIMESTAMP_KEY = 'incuera_session_timestamp'
        const SESSION_TIMEOUT_MS = 30 * 60 * 1000 // 30 minutes

        const existingId = localStorage.getItem(STORAGE_KEY)
        const existingTimestamp = localStorage.getItem(STORAGE_TIMESTAMP_KEY)

        // Check if we have a valid existing session
        if (existingId && existingTimestamp) {
            const sessionAge = Date.now() - parseInt(existingTimestamp, 10)

            // Reuse session if it's less than 30 minutes old
            if (sessionAge < SESSION_TIMEOUT_MS) {
                return existingId
            }
        }

        // Create new session
        const newSessionId = this.generateSessionId()
        localStorage.setItem(STORAGE_KEY, newSessionId)
        localStorage.setItem(STORAGE_TIMESTAMP_KEY, Date.now().toString())

        return newSessionId
    }

    /**
     * Generate unique session ID
     */
    private generateSessionId(): string {
        return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    }

    /**
     * Identify user (call this after user logs in)
     */
    identify(userId: string, userEmail?: string) {
        this.config.userId = userId
        this.config.userEmail = userEmail

        // Update session with user info
        this.sendSessionMetadata()
    }
}

// Export for ES modules
export default Incuera

// Also expose on window for script tag usage
if (typeof window !== 'undefined') {
    (window as any).Incuera = Incuera
}
