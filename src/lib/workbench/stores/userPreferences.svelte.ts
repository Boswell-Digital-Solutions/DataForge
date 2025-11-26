/**
 * User Preferences Store
 *
 * Manages user preference settings with localStorage persistence
 */

import { browser } from '$app/environment';
import type { UserPreferences } from '../types/userPreferences';
import { DEFAULT_USER_PREFERENCES } from '../types/userPreferences';

const STORAGE_KEY = 'vibeforge:user-preferences';

/**
 * Load preferences from localStorage
 */
function loadPreferences(): UserPreferences {
  if (!browser) {
    return { ...DEFAULT_USER_PREFERENCES };
  }

  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      return { ...DEFAULT_USER_PREFERENCES, ...parsed };
    }
  } catch (error) {
    console.error('Failed to load user preferences:', error);
  }

  return { ...DEFAULT_USER_PREFERENCES };
}

/**
 * Save preferences to localStorage
 */
function savePreferences(preferences: UserPreferences): void {
  if (!browser) return;

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences));
  } catch (error) {
    console.error('Failed to save user preferences:', error);
  }
}

/**
 * User Preferences Store
 */
class UserPreferencesStore {
  preferences = $state<UserPreferences>(loadPreferences());

  constructor() {
    // Watch for changes and persist
    $effect(() => {
      savePreferences(this.preferences);
    });
  }

  /**
   * Update skip wizard preference
   */
  setSkipWizard(skip: boolean): void {
    this.preferences.skipWizard = skip;
  }

  /**
   * Toggle skip wizard preference
   */
  toggleSkipWizard(): void {
    this.preferences.skipWizard = !this.preferences.skipWizard;
  }

  /**
   * Set theme preference
   */
  setTheme(theme: 'light' | 'dark' | 'system'): void {
    this.preferences.theme = theme;
  }

  /**
   * Reset preferences to defaults
   */
  reset(): void {
    this.preferences = { ...DEFAULT_USER_PREFERENCES };
  }

  /**
   * Get skip wizard setting
   */
  get skipWizard(): boolean {
    return this.preferences.skipWizard;
  }

  /**
   * Get theme setting
   */
  get theme(): 'light' | 'dark' | 'system' | undefined {
    return this.preferences.theme;
  }
}

// Export singleton instance
export const userPreferencesStore = new UserPreferencesStore();
