/**
 * Wizard Store (Stub)
 * 
 * TODO: Implement full wizard store
 */

class WizardStore {
  isOpen = $state(false);

  open() {
    this.isOpen = true;
  }

  close() {
    this.isOpen = false;
  }
}

export const wizardStore = new WizardStore();
