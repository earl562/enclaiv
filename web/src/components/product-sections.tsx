"use client"

import { motion } from "framer-motion"
import { AnimatedTerminal, AnimatedBars } from "./animated-terminal"

const headingVariants = {
  hidden: { opacity: 0, y: 40, filter: "blur(4px)" },
  visible: {
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: { duration: 1.2, ease: [0.16, 1, 0.3, 1] as const },
  },
}

const descVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 1.0, ease: [0.16, 1, 0.3, 1] as const, delay: 0.15 },
  },
}

interface ProductSectionProps {
  title: string
  description: string
  visual: React.ReactNode
  bgClass: string
  align: "left" | "right"
}

function ProductSection({ title, description, visual, bgClass, align }: ProductSectionProps) {
  return (
    <section className={bgClass}>
      <div className="max-w-5xl px-6 py-28 md:py-36" style={{ marginInline: "auto" }}>
        <div className="grid grid-cols-1 items-center gap-16 md:grid-cols-2">

          {/* Text column */}
          <div className={align === "right" ? "md:order-last" : ""}>
            <motion.h2
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, amount: 0.3 }}
              variants={headingVariants}
              className="font-sans text-3xl font-bold leading-[1.08] tracking-tighter text-[#1C1C1E] md:text-5xl"
            >
              {title}
            </motion.h2>
            <motion.p
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, amount: 0.3 }}
              variants={descVariants}
              className="mt-5 max-w-[42ch] text-[15px] leading-relaxed text-[#636366]"
            >
              {description}
            </motion.p>
          </div>

          {/* Visual column — double-bezel shell */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.2 }}
            transition={{ duration: 0.9, ease: [0.25, 0.46, 0.45, 0.94] as const, delay: 0.2 }}
          >
            <div className="p-1.5 rounded-[20px] border border-[#D1D1D6]/30 bg-[#F2F2F7]/50">
              <div className="rounded-[14px] overflow-hidden bg-white shadow-[inset_0_1px_1px_rgba(255,255,255,0.8)]">
                {visual}
              </div>
            </div>
          </motion.div>

        </div>
      </div>
    </section>
  )
}

export function ProductSections() {
  return (
    <div id="products">
      <ProductSection
        title="Network Proxy"
        description="Every outbound request routes through a Go proxy. Allowed domains pass. Everything else is blocked and logged."
        bgClass="bg-[#F8F9FA]"
        align="left"
        visual={
          <AnimatedTerminal
            lines={[
              { label: "ALLOWLIST CHECK", value: "", color: "white", delay: 0, isHeader: true },
              { label: "arxiv.org", value: "allowed", color: "green", delay: 1.2 },
              { label: "api.anthropic.com", value: "allowed", color: "green", delay: 2.4 },
              { label: "evil.com", value: "blocked", color: "red", delay: 3.6 },
              { label: "malware.net", value: "blocked", color: "red", delay: 4.8 },
              { label: "VIOLATION LOG", value: "", color: "white", delay: 0, isHeader: true },
              { label: "evil.com", value: "403 Forbidden", color: "red", delay: 6.0 },
              { label: "malware.net", value: "403 Forbidden", color: "red", delay: 7.2 },
            ]}
          />
        }
      />

      <ProductSection
        title="Credential Injection"
        description="API keys are injected outside the VM boundary. The agent makes requests normally — the key is added after the request leaves the sandbox."
        bgClass="bg-white"
        align="right"
        visual={
          <AnimatedTerminal
            lines={[
              { label: "REQUEST INTERCEPT", value: "", color: "white", delay: 0, isHeader: true },
              { label: "destination", value: "api.anthropic.com", color: "white", delay: 1.0 },
              { label: "method", value: "POST", color: "white", delay: 2.0 },
              { label: "HEADER INJECTION", value: "", color: "white", delay: 0, isHeader: true },
              { label: "x-api-key", value: "sk-ant---------", color: "green", delay: 3.5 },
              { label: "authorization", value: "Bearer ------", color: "green", delay: 4.8 },
              { label: "AGENT SEES", value: "", color: "white", delay: 0, isHeader: true },
              { label: "x-api-key", value: "[none]", color: "red", delay: 6.0 },
              { label: "authorization", value: "[none]", color: "red", delay: 7.0 },
            ]}
          />
        }
      />

      <ProductSection
        title="Unikernel Isolation"
        description="No shell. No SSH. No package manager. Each VM boots in under 50ms with a ~5MB footprint. Hardware boundaries, not process boundaries."
        bgClass="bg-[#F8F9FA]"
        align="left"
        visual={
          <div className="flex flex-col gap-8 p-6">
            <AnimatedBars
              header="ATTACK SURFACE"
              items={[
                { label: "Docker", value: 90, displayValue: "high" },
                { label: "Standard VM", value: 60, displayValue: "medium" },
                { label: "Enclaiv", value: 5, displayValue: "minimal", highlight: true },
              ]}
            />
            <AnimatedBars
              header="BOOT TIME"
              items={[
                { label: "Docker", value: 50, displayValue: "1-5s" },
                { label: "Standard VM", value: 95, displayValue: "30-60s" },
                { label: "Enclaiv", value: 3, displayValue: "<50ms", highlight: true },
              ]}
            />
          </div>
        }
      />

      <ProductSection
        title="Violation Tracking"
        description="Every blocked request is structured JSON. Query violations by agent, session, or destination. Full audit trail."
        bgClass="bg-white"
        align="right"
        visual={
          <AnimatedTerminal
            lines={[
              { label: "LATEST VIOLATION", value: "", color: "white", delay: 0, isHeader: true },
              { label: "timestamp", value: "2026-03-19T01:17:31Z", color: "white", delay: 1.2 },
              { label: "destination", value: "evil.com", color: "red", delay: 2.4 },
              { label: "protocol", value: "HTTP", color: "white", delay: 3.2 },
              { label: "action", value: "blocked", color: "red", delay: 4.0 },
              { label: "reason", value: "domain not in allowlist", color: "red", delay: 5.0 },
              { label: "agent_id", value: "agent-7f3a", color: "muted", delay: 6.0 },
              { label: "session_id", value: "sess-2b91", color: "muted", delay: 7.0 },
            ]}
          />
        }
      />
    </div>
  )
}
