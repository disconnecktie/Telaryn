// Extend Vitest with DOM assertions shared by every frontend behavioral test.
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

afterEach(() => {
  cleanup()
  window.localStorage.clear()
  window.sessionStorage.clear()
})
