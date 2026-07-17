/** Author: Dev2 | Date: 2026-07-16 | Purpose: Minimal DOM capabilities required by Ant Design smoke tests. */
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

class TestResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({ matches: false, media: query, onchange: null, addListener: () => {}, removeListener: () => {}, addEventListener: () => {}, removeEventListener: () => {}, dispatchEvent: () => false }),
})
Object.defineProperty(window, 'ResizeObserver', { writable: true, value: TestResizeObserver })
Object.defineProperty(globalThis, 'ResizeObserver', { writable: true, value: TestResizeObserver })
Object.defineProperty(window, 'scrollTo', { writable: true, value: () => {} })
const originalGetComputedStyle = window.getComputedStyle.bind(window)
Object.defineProperty(window, 'getComputedStyle', { writable: true, value: (element: Element) => originalGetComputedStyle(element) })

afterEach(() => cleanup())
