'use client';

import React from 'react';
import ThemeToggle from './ThemeToggle';

export default function ThemeToggleWrapper() {
  return (
    <div className="fixed right-4 top-4 z-50">
      <ThemeToggle />
    </div>
  );
} 