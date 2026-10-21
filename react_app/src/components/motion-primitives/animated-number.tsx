'use client';
import { cn } from '../../lib/utils';
import { motion, useSpring, useTransform } from 'motion/react';
import React, { useEffect } from 'react';

export type AnimatedNumberProps = {
  value: number;
  className?: string;
  springOptions?: {
    bounce?: number;
    duration?: number;
  };
  as?: 'span' | 'div' | 'p' | 'h1' | 'h2' | 'h3';
};

const motionComponents: Record<string, any> = {
  span: motion.span,
  div: motion.div,
  p: motion.p,
  h1: motion.h1,
  h2: motion.h2,
  h3: motion.h3,
};

export function AnimatedNumber({
  value,
  className,
  springOptions,
  as = 'span',
}: AnimatedNumberProps) {
  const Component = motionComponents[as] || motion.span;
  const spring = useSpring(value, springOptions || { duration: 0.3 });
  const display = useTransform(spring, (current) =>
    Math.round(current).toLocaleString()
  );

  useEffect(() => {
    spring.set(value);
  }, [spring, value]);

  return (
    <Component className={cn('tabular-nums font-mono', className)}>
      {display}
    </Component>
  );
}
