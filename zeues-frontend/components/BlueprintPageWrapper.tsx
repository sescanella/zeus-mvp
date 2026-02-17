'use client';

import { ReactNode } from 'react';

interface BlueprintPageWrapperProps {
  children: ReactNode;
}

export function BlueprintPageWrapper({ children }: BlueprintPageWrapperProps) {
  return (
    <div
      className="min-h-screen bg-zeues-navy"
      style={{
        backgroundImage: `
          linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)
        `,
        backgroundSize: '50px 50px'
      }}
    >
      {children}
    </div>
  );
}
