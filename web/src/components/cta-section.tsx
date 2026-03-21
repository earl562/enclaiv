"use client"

import { motion } from "framer-motion"
import { springGentle } from "@/lib/motion"
import { MagneticButton } from "./magnetic-button"

export function CtaSection() {
  return (
    <section className="relative overflow-hidden bg-[#F8F9FA] py-40">
      {/* Warm red ambient glow from bottom */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 70% 60% at 50% 100%, rgba(255,59,48,0.06) 0%, transparent 70%)",
        }}
      />

      {/* Subtle grid pattern overlay */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.025]"
        style={{
          backgroundImage:
            "linear-gradient(#1C1C1E 1px, transparent 1px), linear-gradient(90deg, #1C1C1E 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
      />

      <div className="relative z-10 max-w-7xl px-6 text-center md:px-12" style={{ marginInline: "auto" }}>
        <motion.h2
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={springGentle}
          viewport={{ once: true }}
          className="font-sans text-4xl font-bold tracking-tighter leading-[1.0] text-[#1C1C1E] md:text-6xl"
        >
          Start building.
        </motion.h2>
        <motion.p
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ ...springGentle, delay: 0.1 }}
          viewport={{ once: true }}
          className="mt-4 max-w-[44ch] text-center text-[15px] leading-relaxed text-[#636366]"
          style={{ marginInline: "auto" }}
        >
          Enclaiv is open-source. Clone the repo, run a local VM, and add your agent in minutes.
        </motion.p>
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ ...springGentle, delay: 0.15 }}
          viewport={{ once: true }}
          className="mt-10 flex items-center justify-center gap-4"
        >
          <MagneticButton href="https://github.com/earl562/enclaiv" variant="primary">
            Get Started
          </MagneticButton>
          <MagneticButton href="https://github.com/earl562/enclaiv" variant="ghost">
            Read the source
          </MagneticButton>
        </motion.div>
      </div>
    </section>
  )
}
