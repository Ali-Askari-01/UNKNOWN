export type FastApiQuizEvent = {
  type: string
  sessionId: string
  sequence?: number
  payload?: {
    status?: string
    questionCount?: number
    currentQuestionId?: string | null
    currentQuestionOrder?: number | null
    question?: { prompt: string; questionType?: string; codeSnippet?: string | null; options: Array<{ key: string; text: string }> } | null
    buzzerState?: string
    buzzerWinner?: string | null
    scores?: Array<{ groupName: string; score: number }>
    participantId?: string
    teamName?: string
    answerDeadline?: string
    correct?: boolean | null
    points?: number
    buzzerOpen?: boolean
    questionClosed?: boolean
  }
}
function websocketBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_FASTAPI_WS_URL
  if (configured) return configured.replace(/\/$/, '')
  if (typeof window === 'undefined') return 'ws://127.0.0.1:8000'
  return `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.hostname}:8000`
}

export function connectFastApiQuiz(
  sessionId: string,
  token: string,
  onEvent: (event: FastApiQuizEvent) => void,
  onState: (state: 'connected' | 'disconnected') => void,
): { close: () => void } {
  let socket: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let closedByClient = false
  let reconnectAttempt = 0

  const connect = () => {
    if (closedByClient) return
    socket = new WebSocket(
      `${websocketBaseUrl()}/api/v1/ws/quiz/${encodeURIComponent(sessionId)}`,
      [`auth.${token}`],
    )
    socket.addEventListener('open', () => {
      reconnectAttempt = 0
      onState('connected')
    })
    socket.addEventListener('close', () => {
      socket = null
      onState('disconnected')
      if (closedByClient) return
      const delay = Math.min(10_000, 500 * 2 ** reconnectAttempt)
      reconnectAttempt += 1
      reconnectTimer = setTimeout(connect, delay)
    })
    socket.addEventListener('message', (message) => {
      try {
        onEvent(JSON.parse(message.data) as FastApiQuizEvent)
      } catch {
        // Ignore malformed events; the next reconnect will request a fresh snapshot.
      }
    })
  }

  connect()
  return {
    close: () => {
      closedByClient = true
      if (reconnectTimer) clearTimeout(reconnectTimer)
      reconnectTimer = null
      socket?.close()
      socket = null
    },
  }
}
