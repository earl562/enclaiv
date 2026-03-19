"use client"

import { motion } from "framer-motion"
import { springGentle } from "@/lib/motion"
import { MagneticButton } from "./magnetic-button"

export function CtaSection() {
  return (
    <section className="relative bg-[#F8F9FA] py-40">
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 50% 60% at 50% 100%, rgba(255,59,48,0.03) 0%, transparent 70%)",
        }}
      />
      <div className="mx-auto max-w-7xl px-6 text-center md:px-12">
        <motion.h2
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={springGentle}
          viewport={{ once: true }}
          className="font-sans text-3xl font-light italic tracking-tighter text-[#1C1C1E] md:text-5xl"
        >
          Start building.
        </motion.h2>
        <motion.p
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ ...springGentle, delay: 0.1 }}
          viewport={{ once: true }}
          className="mx-auto mt-4 max-w-[44ch] text-center text-[15px] leading-relaxed text-[#636366]"
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
