"use client"

import { motion } from "framer-motion"
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
    <section className="relative min-h-[100dvh] overflow-hidden bg-[#F8F9FA]">
      <div className="grid min-h-[100dvh] grid-cols-1 md:grid-cols-2">

        {/* Left column: content */}
        <div className="relative z-10 flex flex-col justify-center px-8 pb-20 pt-28 md:px-12 md:pt-32">
          {/* Ambient radial glow */}
          <div
            className="pointer-events-none absolute inset-0 z-0"
            style={{
              background: "radial-gradient(ellipse 80% 60% at 30% 50%, rgba(255,59,48,0.04) 0%, transparent 70%)",
            }}
          />

          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="relative z-10 flex flex-col"
          >
            <motion.div variants={itemVariants}>
              <span className="inline-block rounded border border-[#FF3B30]/20 bg-[#FF3B30]/5 px-3 py-1 text-[10px] uppercase tracking-[0.2em] font-medium text-[#FF3B30]">
                Open Source
              </span>
            </motion.div>

            <motion.h1
              variants={itemVariants}
              className="mt-8 font-sans text-4xl font-bold leading-[1.05] tracking-tighter text-[#1C1C1E] sm:text-5xl md:text-5xl lg:text-6xl"
            >
              your agent should have
              <br />
              nothing worth stealing
              <br />
              and nothing worth
              <br />
              <span className="text-[#FF3B30]">preserving.</span>
            </motion.h1>

            <motion.p
              variants={itemVariants}
              className="mt-8 max-w-[44ch] text-lg leading-relaxed text-[#636366]"
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

            {/* Stats card — double-bezel */}
            <motion.div variants={itemVariants} className="mt-14">
              <div className="inline-block p-1 rounded-xl border border-[#D1D1D6]/30 bg-white/30 backdrop-blur-sm">
                <div className="rounded-[8px] bg-white/70 px-8 py-5 shadow-[inset_0_1px_1px_rgba(255,255,255,0.8)]">
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
              </div>
            </motion.div>
          </motion.div>
        </div>

        {/* Right column: particle network */}
        <div className="relative hidden overflow-hidden md:block">
          <ParticleNetwork />
          {/* Left edge fade to blend with content column */}
          <div
            className="pointer-events-none absolute inset-y-0 left-0 z-10 w-32"
            style={{
              background: "linear-gradient(to right, #F8F9FA, transparent)",
            }}
          />
        </div>

      </div>
    </section>
  )
}
