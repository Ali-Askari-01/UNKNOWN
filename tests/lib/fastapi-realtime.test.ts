import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { connectFastApiQuiz } from '@/lib/fastapi-realtime'

const WS_URL_ENV = 'NEXT_PUBLIC_FASTAPI_WS_URL'
const originalEnv = process.env[WS_URL_ENV]

type Listener = (event: any) => void
type FakeMessage = { data: string }

class FakeWebSocket {
  static instances: FakeWebSocket[] = []

  url: string
  protocols: string[]
  readyState = 0

  private readonly listeners = new Map<string, Listener[]>()

  constructor(url: string, protocols: string[] = []) {
    this.url = url
    this.protocols = protocols
    FakeWebSocket.instances.push(this)
  }

  static last(): FakeWebSocket {
    const instance = FakeWebSocket.instances[FakeWebSocket.instances.length - 1]
    if (!instance) throw new Error('No WebSocket instance was created')
    return instance
  }

  addEventListener(type: string, listener: Listener) {
    const existing = this.listeners.get(type) ?? []
    existing.push(listener)
    this.listeners.set(type, existing)
  }

  emit(type: string, event?: unknown) {
    for (const listener of [...(this.listeners.get(type) ?? [])]) {
      listener(event)
    }
  }

  close() {
    this.readyState = 3
    this.emit('close', { wasClean: true })
  }
}

type SetupOptions = {
  sessionId?: string
  token?: string
}

function setup(options: SetupOptions = {}) {
  const onEvent = vi.fn()
  const onState = vi.fn()
  const handle = connectFastApiQuiz(
    options.sessionId ?? 'session-1',
    options.token ?? 'team-token',
    onEvent,
    onState,
  )
  return { onEvent, onState, handle }
}

describe('connectFastApiQuiz', () => {
  beforeEach(() => {
    vi.stubGlobal('WebSocket', FakeWebSocket)
    FakeWebSocket.instances = []
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.useRealTimers()
    if (originalEnv === undefined) {
      delete process.env[WS_URL_ENV]
    } else {
      process.env[WS_URL_ENV] = originalEnv
    }
  })

  it('connects with a subprotocol token to the default local endpoint', () => {
    setup({ sessionId: 'session-1', token: 'team-token' })

    const socket = FakeWebSocket.last()
    expect(socket.url).toBe('ws://127.0.0.1:8000/api/v1/ws/quiz/session-1')
    expect(socket.protocols).toEqual(['auth.team-token'])
  })

  it('strips the trailing slash from the configured base URL and encodes the session id', () => {
    process.env[WS_URL_ENV] = 'wss://backend.example.test:9000/'
    setup({ sessionId: 'class A/1?', token: 'tok/base64==' })

    const socket = FakeWebSocket.last()
    expect(socket.url).toBe(
      'wss://backend.example.test:9000/api/v1/ws/quiz/class%20A%2F1%3F',
    )
    expect(socket.protocols).toEqual(['auth.tok/base64=='])
  })

  it('reports connected on open and disconnected on close', () => {
    const { onState, handle } = setup()
    expect(onState).not.toHaveBeenCalled()

    FakeWebSocket.last().emit('open', {})
    expect(onState).toHaveBeenCalledTimes(1)
    expect(onState).toHaveBeenLastCalledWith('connected')

    handle.close()
    expect(onState).toHaveBeenLastCalledWith('disconnected')
  })

  it('reconnects with exponential backoff capped at ten seconds and resets after success', () => {
    vi.useFakeTimers()
    const { onState } = setup()

    FakeWebSocket.last().emit('open', {})
    expect(onState).toHaveBeenLastCalledWith('connected')

    const delays = [500, 1000, 2000, 4000, 8000, 10000, 10000]
    for (const delay of delays) {
      const before = FakeWebSocket.instances.length
      FakeWebSocket.last().emit('close', {})
      expect(onState).toHaveBeenLastCalledWith('disconnected')

      vi.advanceTimersByTime(delay - 1)
      expect(FakeWebSocket.instances.length).toBe(before)

      vi.advanceTimersByTime(1)
      expect(FakeWebSocket.instances.length).toBe(before + 1)
    }

    FakeWebSocket.last().emit('open', {})
    expect(onState).toHaveBeenLastCalledWith('connected')

    const before = FakeWebSocket.instances.length
    FakeWebSocket.last().emit('close', {})
    vi.advanceTimersByTime(499)
    expect(FakeWebSocket.instances.length).toBe(before)
    vi.advanceTimersByTime(1)
    expect(FakeWebSocket.instances.length).toBe(before + 1)
  })

  it('cancels a pending reconnect when close() is called', () => {
    vi.useFakeTimers()
    const { handle } = setup()

    FakeWebSocket.last().emit('close', {})
    close(handle)

    vi.advanceTimersByTime(60_000)
    expect(FakeWebSocket.instances).toHaveLength(1)
  })

  it('does not reconnect after an explicit client close', () => {
    vi.useFakeTimers()
    const { handle } = setup()

    FakeWebSocket.last().emit('open', {})
    close(handle)

    vi.advanceTimersByTime(60_000)
    expect(FakeWebSocket.instances).toHaveLength(1)
  })

  it('parses valid events and ignores malformed payloads', () => {
    const { onEvent } = setup()

    const socket = FakeWebSocket.last()
    socket.emit('open', {})
    socket.emit('message', { data: 'not-json' })
    expect(onEvent).not.toHaveBeenCalled()

    const validEvent = {
      type: 'quiz.broadcast',
      sessionId: 'session-1',
      sequence: 4,
      payload: { status: 'started' },
    }
    socket.emit('message', { data: JSON.stringify(validEvent) })
    expect(onEvent).toHaveBeenCalledTimes(1)
    expect(onEvent).toHaveBeenLastCalledWith(validEvent)
  })
})

function close(handle: { close: () => void }) {
  handle.close()
}
