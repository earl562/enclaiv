"use client"

import { motion } from "framer-motion"
import { CaretDown } from "@phosphor-icons/react"
import { MagneticButton } from "./magnetic-button"
import { ParticleNetwork } from "./particle-network"

const containerVariants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.2 },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { type: "spring" as const, stiffness: 80, damping: 20, duration: 1.2 },
  },
}

export function Hero() {
  return (
    <section className="relative min-h-[100dvh] overflow-hidden bg-[#F8F9FA] pt-16">
      <div className="absolute inset-0 hidden opacity-50 md:block">
        <ParticleNetwork />
      </div>

      <div
        className="absolute inset-0 z-[1] pointer-events-none"
        style={{
          background: "radial-gradient(ellipse 60% 40% at 50% 50%, rgba(255,59,48,0.04) 0%, transparent 70%)",
        }}
      />

      <div className="relative z-10 flex min-h-[100dvh] flex-col items-center justify-center px-6 text-center">
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="flex flex-col items-center"
        >
          <motion.div variants={itemVariants}>
            <span className="inline-block rounded border border-[#FF3B30]/20 bg-[#FF3B30]/5 px-3 py-1 text-[10px] uppercase tracking-[0.2em] font-medium text-[#FF3B30]">
              Open Source
            </span>
          </motion.div>

          <motion.h1
            variants={itemVariants}
            className="mt-8 font-sans text-5xl font-bold leading-[1.05] tracking-tighter text-[#1C1C1E] sm:text-6xl md:text-8xl"
          >
            your agent has
            <br />
            nothing worth
            <br />
            <span className="text-[#FF3B30]">stealing.</span>
          </motion.h1>

          <motion.p
            variants={itemVariants}
            className="mt-8 max-w-[48ch] text-lg leading-relaxed text-[#636366]"
          >
            Hardware-isolated sandboxing for AI agents. Every agent runs
            in its own Unikraft VM. No API keys. No credentials. No attack surface.
          </motion.p>

          <motion.div
            variants={itemVariants}
            className="mt-12 flex items-center gap-4"
          >
            <MagneticButton
              href="https://github.com/earl562/enclaiv"
              variant="primary"
            >
              Get Started
            </MagneticButton>
            <MagneticButton href="#products" variant="ghost">
              How it works
            </MagneticButton>
          </motion.div>

          <motion.div variants={itemVariants}>
            <div className="mt-16 rounded-xl border border-[#D1D1D6]/40 bg-white/50 px-8 py-5 backdrop-blur-sm">
              <div className="flex items-center gap-10">
                <div>
                  <div className="font-mono text-2xl font-bold text-[#1C1C1E]">8</div>
                  <div className="mt-1 text-[10px] uppercase tracking-wider text-[#636366]">Security layers</div>
                </div>
                <div className="h-8 w-px bg-[#D1D1D6]" />
                <div>
                  <div className="font-mono text-2xl font-bold text-[#1C1C1E]">&lt;50ms</div>
                  <div className="mt-1 text-[10px] uppercase tracking-wider text-[#636366]">Cold start</div>
                </div>
                <div className="h-8 w-px bg-[#D1D1D6]" />
                <div>
                  <div className="font-mono text-2xl font-bold text-[#1C1C1E]">~5MB</div>
                  <div className="mt-1 text-[10px] uppercase tracking-wider text-[#636366]">Footprint</div>
                </div>
              </div>
            </div>
          </motion.div>

          <motion.div variants={itemVariants} className="mt-12">
            <a href="#products" className="inline-flex flex-col items-center gap-1 text-[#636366] transition-colors hover:text-[#1C1C1E]">
              <span className="text-[10px] uppercase tracking-[0.2em]">Learn more</span>
              <motion.div
                animate={{ y: [0, 6, 0] }}
                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
              >
                <CaretDown size={16} weight="thin" />
              </motion.div>
            </a>
          </motion.div>
        </motion.div>
      </div>
    </section>
  )
}
