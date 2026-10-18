import { AsyncLocalStorage } from 'node:async_hooks'

const globalWithAls = globalThis as typeof globalThis & {
  AsyncLocalStorage?: typeof AsyncLocalStorage
}

if (typeof globalWithAls.AsyncLocalStorage === 'undefined') {
  globalWithAls.AsyncLocalStorage = AsyncLocalStorage
}

export {}
