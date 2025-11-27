/**
 * Vitest Setup File
 * Configures test environment for Svelte 5 components and stores
 */

import { vi } from "vitest";
import "@testing-library/jest-dom";

// Mock browser environment
global.localStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
};

// Mock document for DOM manipulation
if (typeof document !== "undefined") {
  document.documentElement.setAttribute = vi.fn();
  document.documentElement.getAttribute = vi.fn();
}

// Mock Tauri API (not available in test environment)
globalThis.__TAURI__ = undefined;
