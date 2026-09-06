'use client';

import { useLayoutEffect } from 'react';

/** Plays a one-time edge-reveal when the user first opens the site this session. */
export function EnterMotion() {
  useLayoutEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    if (sessionStorage.getItem('dar-enter-motion') === '1') return;
    document.documentElement.classList.add('dar-enter');
    sessionStorage.setItem('dar-enter-motion', '1');
    const timer = window.setTimeout(() => {
      document.documentElement.classList.remove('dar-enter');
    }, 1200);
    return () => window.clearTimeout(timer);
  }, []);
  return null;
}
