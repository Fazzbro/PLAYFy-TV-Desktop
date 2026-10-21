'use client';
import { ReactNode } from 'react';
import { motion, type Variants, type Transition } from 'motion/react';

export type InViewProps = {
  children: ReactNode;
  variants?: Variants;
  transition?: Transition;
  className?: string;
};

const defaultVariants: Variants = {
  hidden: { opacity: 0, y: 10 },
  visible: { opacity: 1, y: 0 },
};

export function InView({
  children,
  variants = defaultVariants,
  transition = { duration: 0.25, ease: 'easeOut' },
  className,
}: InViewProps) {
  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={variants}
      transition={transition}
      className={className}
    >
      {children}
    </motion.div>
  );
}
