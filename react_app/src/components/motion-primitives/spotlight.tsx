'use client';
import { cn } from '../../lib/utils';

export type SpotlightProps = {
  className?: string;
  size?: number;
};

export function Spotlight({ className }: SpotlightProps) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        'pointer-events-none absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-[radial-gradient(circle_at_50%_0%,rgba(255,255,255,0.08)_0%,transparent_75%)]',
        className
      )}
    />
  );
}
