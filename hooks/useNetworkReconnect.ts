import * as Network from 'expo-network'
import { useEffect, useRef } from 'react'

export default function useNetworkReconnect(pollInterval = 5000) {
  const wasConnectedRef = useRef<boolean | null>(null)

  useEffect(() => {
    let mounted = true
    let timer: any

    async function check() {
      try {
        const state = await Network.getNetworkStateAsync()
        const isConnected = !!state.isConnected

        if (wasConnectedRef.current === null) {
          // initialize connectivity state but do NOT trigger any reconnection logic
          wasConnectedRef.current = isConnected
        } else {
          // update connectivity state only; do not call ensureSupabaseConnected or recreate clients
          wasConnectedRef.current = isConnected
        }
      } catch (err) {
        console.warn('Network check failed:', err)
      } finally {
        if (mounted) timer = setTimeout(check, pollInterval)
      }
    }

    check()

    return () => {
      mounted = false
      if (timer) clearTimeout(timer)
    }
  }, [pollInterval])
}
