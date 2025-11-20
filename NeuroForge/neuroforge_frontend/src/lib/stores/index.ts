/**
 * Global Svelte Stores for NeuroForge Frontend
 * Manages app-wide state using Svelte 5 runes
 */

import { writable, derived, readonly } from "svelte/store";
import { Domain } from "../types";
import type { InferenceResult } from "../types";

// ============================================================================
// Theme Store (Persisted to localStorage)
// ============================================================================

function createThemeStore() {
  const { subscribe, set, update } = writable<"light" | "dark">("dark");

  return {
    subscribe,
    init: () => {
      if (typeof window !== "undefined") {
        // Check localStorage first
        const stored = localStorage.getItem("nf-theme");
        if (stored === "light" || stored === "dark") {
          set(stored);
          return;
        }

        // Fall back to system preference
        if (
          window.matchMedia &&
          window.matchMedia("(prefers-color-scheme: light)").matches
        ) {
          set("light");
        } else {
          set("dark");
        }
      }
    },
    toggle: () => {
      update((t) => {
        const newTheme = t === "light" ? "dark" : "light";
        if (typeof window !== "undefined") {
          localStorage.setItem("nf-theme", newTheme);
          // Apply immediately to DOM
          if (newTheme === "dark") {
            document.documentElement.classList.add("dark");
          } else {
            document.documentElement.classList.remove("dark");
          }
        }
        return newTheme;
      });
    },
    set: (value: "light" | "dark") => {
      if (typeof window !== "undefined") {
        localStorage.setItem("nf-theme", value);
        // Apply immediately to DOM
        if (value === "dark") {
          document.documentElement.classList.add("dark");
        } else {
          document.documentElement.classList.remove("dark");
        }
      }
      set(value);
    },
  };
}

export const theme = createThemeStore();

// Legacy export for backwards compatibility
export const toggleTheme = () => theme.toggle();

// ============================================================================
// Auth Store
// ============================================================================

interface User {
  id: string;
  name: string;
  email: string;
  role: "admin" | "user";
}

export const user = writable<User | null>(null);
export const isAuthenticated = derived(user, ($user) => $user !== null);

// ============================================================================
// App State Store
// ============================================================================

interface AppState {
  environment: "development" | "staging" | "production";
  backendUrl: string;
  isLoading: boolean;
  errorMessage: string | null;
  notification: {
    type: "success" | "error" | "warning" | "info";
    message: string;
    timestamp: number;
  } | null;
}

const initialAppState: AppState = {
  environment:
    (import.meta.env.MODE as "development" | "staging" | "production") ||
    "development",
  backendUrl:
    import.meta.env.VITE_BACKEND_URL || "http://localhost:8000/api/v1",
  isLoading: false,
  errorMessage: null,
  notification: null,
};

export const appState = writable<AppState>(initialAppState);

export const setLoading = (loading: boolean) => {
  appState.update((state) => ({ ...state, isLoading: loading }));
};

export const setError = (error: string | null) => {
  appState.update((state) => ({ ...state, errorMessage: error }));
};

export const showNotification = (
  message: string,
  type: "success" | "error" | "warning" | "info" = "info"
) => {
  appState.update((state) => ({
    ...state,
    notification: { type, message, timestamp: Date.now() },
  }));

  // Auto-clear notification after 5 seconds
  setTimeout(() => {
    appState.update((state) => ({ ...state, notification: null }));
  }, 5000);
};

// ============================================================================
// UI Navigation Store
// ============================================================================

export type PageName =
  | "overview"
  | "pipelines"
  | "domains"
  | "models"
  | "evaluations"
  | "logs"
  | "playground"
  | "settings"
  | "analytics";

interface NavState {
  currentPage: PageName;
  sidebarOpen: boolean;
  selectedDomain: Domain | null;
  selectedPipelineId: string | null;
}

const initialNavState: NavState = {
  currentPage: "overview",
  sidebarOpen: true,
  selectedDomain: null,
  selectedPipelineId: null,
};

export const navState = writable<NavState>(initialNavState);

export const navigateTo = (page: PageName) => {
  navState.update((state) => ({ ...state, currentPage: page }));
};

export const toggleSidebar = () => {
  navState.update((state) => ({ ...state, sidebarOpen: !state.sidebarOpen }));
};

export const selectDomain = (domain: Domain | null) => {
  navState.update((state) => ({ ...state, selectedDomain: domain }));
};

export const selectPipeline = (pipelineId: string | null) => {
  navState.update((state) => ({ ...state, selectedPipelineId: pipelineId }));
};

// ============================================================================
// Playground State Store
// ============================================================================

interface PlaygroundState {
  query: string;
  context: string;
  selectedDomain: Domain | null;
  selectedModel: string | null;
  isRunning: boolean;
  result: InferenceResult | null;
  error: string | null;
}

const initialPlaygroundState: PlaygroundState = {
  query: "",
  context: "",
  selectedDomain: Domain.LITERARY,
  selectedModel: null,
  isRunning: false,
  result: null,
  error: null,
};

export const playgroundState = writable<PlaygroundState>(
  initialPlaygroundState
);

export const updatePlaygroundQuery = (query: string) => {
  playgroundState.update((state) => ({ ...state, query }));
};

export const updatePlaygroundContext = (context: string) => {
  playgroundState.update((state) => ({ ...state, context }));
};

export const setPlaygroundRunning = (running: boolean) => {
  playgroundState.update((state) => ({ ...state, isRunning: running }));
};

export const setPlaygroundResult = (result: InferenceResult | null) => {
  playgroundState.update((state) => ({ ...state, result, error: null }));
};

export const setPlaygroundError = (error: string | null) => {
  playgroundState.update((state) => ({ ...state, error }));
};

export const resetPlayground = () => {
  playgroundState.set(initialPlaygroundState);
};

// ============================================================================
// Preferences Store (Persisted)
// ============================================================================

interface UserPreferences {
  defaultDomain: Domain;
  defaultModelProvider: string;
  autoRefreshEnabled: boolean;
  refreshIntervalMs: number;
  maxRowsPerTable: number;
  compactMode: boolean;
}

const initialPreferences: UserPreferences = {
  defaultDomain: Domain.LITERARY,
  defaultModelProvider: "ollama",
  autoRefreshEnabled: true,
  refreshIntervalMs: 5000,
  maxRowsPerTable: 50,
  compactMode: false,
};

function createPreferencesStore() {
  const { subscribe, set, update } =
    writable<UserPreferences>(initialPreferences);

  return {
    subscribe,
    load: () => {
      if (typeof window !== "undefined") {
        const stored = localStorage.getItem("nf-preferences");
        if (stored) {
          try {
            set(JSON.parse(stored));
          } catch (e) {
            console.error("Failed to load preferences:", e);
          }
        }
      }
    },
    save: (prefs: Partial<UserPreferences>) => {
      update((state) => {
        const updated = { ...state, ...prefs };
        if (typeof window !== "undefined") {
          localStorage.setItem("nf-preferences", JSON.stringify(updated));
        }
        return updated;
      });
    },
    reset: () => {
      set(initialPreferences);
      if (typeof window !== "undefined") {
        localStorage.removeItem("nf-preferences");
      }
    },
  };
}

export const preferences = createPreferencesStore();
