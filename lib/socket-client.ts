/**
 * lib/socket-client.ts
 * Singleton Socket.IO client — ensures only one connection per browser tab.
 * Import only from 'use client' components.
 */

import { io, type Socket } from 'socket.io-client'

let socket: Socket | null = null

export function getSocket(): Socket {
  if (!socket) {
    socket = io({
      // Connect to the same origin (custom server handles both HTTP + WS)
      path: '/socket.io',
      transports: ['websocket', 'polling'],
      autoConnect: true,
      reconnectionAttempts: Infinity,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      // IMPORTANT: Include cookies in the handshake for authentication
      withCredentials: true,
    })
    
    // Log connection events for debugging
    socket.on('connect', () => console.log('[Socket] Connected:', socket?.id))
    socket.on('disconnect', (reason) => console.log('[Socket] Disconnected:', reason))
    socket.on('connect_error', (err) => console.error('[Socket] Connect error:', err.message))
  }
  return socket
}
