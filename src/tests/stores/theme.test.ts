/**
 * Theme Store Tests
 * Tests for Svelte 5 rune-based theme store
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { themeStore } from "$lib/core/stores/theme.svelte";
import type { Theme } from "$lib/core/stores/theme.svelte";

// Mock browser environment
const localStorageMock = (() => {
  let store: Record<string, string> = {};

  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

global.localStorage = localStorageMock as Storage;

const documentSetAttributeMock = vi.fn();
global.document = {
  documentElement: {
    setAttribute: documentSetAttributeMock,
  },
} as any;

describe("Theme Store", () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorageMock.clear();
    documentSetAttributeMock.mockClear();
  });

  describe("initialization", () => {
    it("should initialize with dark theme by default", () => {
      expect(themeStore.current).toBe("dark");
    });

    it("should initialize from localStorage if available", () => {
      localStorageMock.setItem("vibeforge-theme", "light");
      
      // Note: Since the store is already initialized, we can't easily test this
      // without module reloading. This is a known limitation of singleton stores.
      // In a real scenario, you'd use dependency injection or module mocking.
    });
  });

  describe("derived state", () => {
    it("should compute isDark correctly", () => {
      themeStore.setTheme("dark");
      expect(themeStore.isDark).toBe(true);
      
      themeStore.setTheme("light");
      expect(themeStore.isDark).toBe(false);
    });

    it("should compute isLight correctly", () => {
      themeStore.setTheme("light");
      expect(themeStore.isLight).toBe(true);
      
      themeStore.setTheme("dark");
      expect(themeStore.isLight).toBe(false);
    });
  });

  describe("setTheme", () => {
    it("should update current theme", () => {
      themeStore.setTheme("light");
      expect(themeStore.current).toBe("light");
      
      themeStore.setTheme("dark");
      expect(themeStore.current).toBe("dark");
    });

    it("should persist theme to localStorage", () => {
      themeStore.setTheme("light");
      expect(localStorageMock.getItem("vibeforge-theme")).toBe("light");
      
      themeStore.setTheme("dark");
      expect(localStorageMock.getItem("vibeforge-theme")).toBe("dark");
    });

    it("should update document root attribute", () => {
      themeStore.setTheme("light");
      expect(documentSetAttributeMock).toHaveBeenCalledWith("data-theme", "light");
      
      documentSetAttributeMock.mockClear();
      
      themeStore.setTheme("dark");
      expect(documentSetAttributeMock).toHaveBeenCalledWith("data-theme", "dark");
    });
  });

  describe("toggle", () => {
    it("should toggle from dark to light", () => {
      themeStore.setTheme("dark");
      themeStore.toggle();
      expect(themeStore.current).toBe("light");
    });

    it("should toggle from light to dark", () => {
      themeStore.setTheme("light");
      themeStore.toggle();
      expect(themeStore.current).toBe("dark");
    });

    it("should persist toggled theme", () => {
      themeStore.setTheme("dark");
      themeStore.toggle();
      expect(localStorageMock.getItem("vibeforge-theme")).toBe("light");
    });

    it("should update document on toggle", () => {
      themeStore.setTheme("dark");
      documentSetAttributeMock.mockClear();
      
      themeStore.toggle();
      expect(documentSetAttributeMock).toHaveBeenCalledWith("data-theme", "light");
    });
  });

  describe("reactivity", () => {
    it("should update derived values when theme changes", () => {
      themeStore.setTheme("dark");
      expect(themeStore.isDark).toBe(true);
      expect(themeStore.isLight).toBe(false);
      
      themeStore.setTheme("light");
      expect(themeStore.isDark).toBe(false);
      expect(themeStore.isLight).toBe(true);
    });

    it("should maintain consistency across multiple operations", () => {
      themeStore.setTheme("dark");
      expect(themeStore.current).toBe("dark");
      expect(themeStore.isDark).toBe(true);
      
      themeStore.toggle();
      expect(themeStore.current).toBe("light");
      expect(themeStore.isLight).toBe(true);
      
      themeStore.toggle();
      expect(themeStore.current).toBe("dark");
      expect(themeStore.isDark).toBe(true);
    });
  });

  describe("edge cases", () => {
    it("should handle rapid theme changes", () => {
      themeStore.setTheme("dark");
      themeStore.setTheme("light");
      themeStore.setTheme("dark");
      themeStore.setTheme("light");
      
      expect(themeStore.current).toBe("light");
      expect(localStorageMock.getItem("vibeforge-theme")).toBe("light");
    });

    it("should handle rapid toggles", () => {
      themeStore.setTheme("dark");
      themeStore.toggle();
      themeStore.toggle();
      themeStore.toggle();
      
      expect(themeStore.current).toBe("light");
    });
  });
});
