declare global {
  interface Window {
    Easymap?: new (target: string) => unknown;
  }
}

export interface EasymapShell {
  map: unknown | null;
  ready: boolean;
}

export function createEasymapShell(targetId: string): EasymapShell {
  if (!window.Easymap) {
    return { map: null, ready: false };
  }

  return {
    map: new window.Easymap(targetId),
    ready: true
  };
}
