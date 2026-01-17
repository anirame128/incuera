'use client'

import { useEffect, useRef } from 'react'

// Dynamically import the SDK to avoid SSR issues with Turbopack
const loadSDK = async () => {
  if (typeof window === 'undefined') return null
  const module = await import('@incuera/sdk')
  return module.default
}

interface IncueraProviderProps {
  apiKey: string
  apiHost: string
  userId?: string
  userEmail?: string
}

export default function IncueraProvider({
  apiKey,
  apiHost,
  userId,
  userEmail,
}: IncueraProviderProps) {
  const incueraRef = useRef<any>(null)
  const initializedRef = useRef(false)

  useEffect(() => {
    // Prevent double initialization in development (React Strict Mode)
    if (initializedRef.current) return

    // Only initialize in browser
    if (typeof window === 'undefined') return

    // Validate required config (only apiHost is required now)
    if (!apiHost) {
      return
    }

    // Dynamically load and initialize SDK
    loadSDK()
      .then((Incuera) => {
        if (!Incuera) {
          return
        }

        try {
          // Initialize Incuera
          const incuera = new Incuera({
            apiKey,
            apiHost,
            userId,
            userEmail,
          })

          incueraRef.current = incuera

          // Start recording
          incuera.init()
          initializedRef.current = true
        } catch (error) {
          // Silently fail initialization
        }
      })
      .catch((error) => {
        // Silently fail SDK loading
      })

    // Cleanup on unmount
    return () => {
      if (incueraRef.current) {
        incueraRef.current.stop()
        incueraRef.current = null
        initializedRef.current = false
      }
    }
  }, [apiKey, apiHost]) // Don't include userId/userEmail here

  // Update user info when userId/userEmail changes (e.g., after login)
  useEffect(() => {
    if (incueraRef.current && userId) {
      incueraRef.current.identify(userId, userEmail)
    }
  }, [userId, userEmail])

  return null // This component doesn't render anything
}
