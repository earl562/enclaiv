export const spring = {
  type: "spring" as const,
  stiffness: 400,
  damping: 30,
}

export const springGentle = {
  type: "spring" as const,
  stiffness: 200,
  damping: 25,
}

export const springHeavy = {
  type: "spring" as const,
  stiffness: 100,
  damping: 20,
}

export const fadeUp = {
  initial: { opacity: 0, y: 24 },
  animate: { opacity: 1, y: 0 },
}

export const fadeUpSmall = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
}

export const stagger = {
  visible: {
    transition: {
      staggerChildren: 0.07,
    },
  },
}
