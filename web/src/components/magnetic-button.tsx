"use client"

import { useRef } from "react"
import { motion, useMotionValue, useSpring } from "framer-motion"
import { ArrowUpRight } from "@phosphor-icons/react"

interface MagneticButtonProps {
  children: React.ReactNode
  href?: string
  variant?: "primary" | "ghost" | "ghost-dark"
  className?: string
}

export function MagneticButton({
  children,
  href,
  variant = "primary",
  className = "",
}: MagneticButtonProps) {
  const ref = useRef<HTMLDivElement>(null)
  const x = useMotionValue(0)
  const y = useMotionValue(0)

  const springX = useSpring(x, { stiffness: 400, damping: 30 })
  const springY = useSpring(y, { stiffness: 400, damping: 30 })

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!ref.current) return
    const rect = ref.current.getBoundingClientRect()
    const centerX = rect.left + rect.width / 2
    const centerY = rect.top + rect.height / 2
    x.set((e.clientX - centerX) * 0.15)
    y.set((e.clientY - centerY) * 0.15)
  }

  const handleMouseLeave = () => {
    x.set(0)
    y.set(0)
  }

  const baseStyles = {
    primary:
      "bg-[#FF3B30] text-white hover:bg-[#E02B20] shadow-[0_2px_8px_rgba(255,59,48,0.25)]",
    ghost:
      "border border-[#D1D1D6] text-[#1C1C1E] hover:border-[#636366] hover:bg-white",
    "ghost-dark":
      "border border-zinc-700 text-zinc-300 hover:border-zinc-500 hover:text-white",
  }[variant]

  const Tag = href ? "a" : "button"

  return (
    <motion.div
      ref={ref}
      style={{ x: springX, y: springY }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className="inline-block"
    >
      <motion.div
        whileTap={{ scale: 0.97 }}
        transition={{ type: "spring", stiffness: 400, damping: 30 }}
      >
        <Tag
          href={href}
          className={`group relative inline-flex items-center gap-2 rounded px-5 py-2.5 text-sm font-medium transition-all duration-200 ${baseStyles} ${className}`}
        >
          {children}
          {variant === "primary" && (
            <span className="flex h-5 w-5 items-center justify-center rounded bg-white/20 transition-transform duration-200 group-hover:translate-x-0.5 group-hover:-translate-y-px">
              <ArrowUpRight size={12} weight="bold" />
            </span>
          )}
        </Tag>
      </motion.div>
    </motion.div>
  )
}
