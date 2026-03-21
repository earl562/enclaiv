"use client"

import { motion } from "framer-motion"
import { GithubLogo } from "@phosphor-icons/react"
import { springGentle } from "@/lib/motion"
import { EnclaivLogo } from "./enclaiv-logo"

export function Nav() {
  return (
    <motion.nav
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ ...springGentle, delay: 0.1 }}
      className="fixed top-6 left-1/2 z-50 -translate-x-1/2 rounded-full border border-[#D1D1D6]/40 bg-white/70 backdrop-blur-xl shadow-[0_2px_16px_rgba(0,0,0,0.04)]"
    >
      <div className="flex items-center gap-6 px-5 py-2.5">
        <a href="/" className="flex items-center gap-2.5">
          <EnclaivLogo size={22} className="text-[#1C1C1E]" />
          <span className="font-mono text-sm font-semibold tracking-wider text-[#1C1C1E]">
            enclaiv
          </span>
        </a>

        <div className="flex items-center gap-5">
          <a
            href="#products"
            className="text-xs font-medium text-[#636366] transition-colors duration-200 hover:text-[#1C1C1E]"
          >
            Products
          </a>
          <a
            href="https://github.com/earl562/enclaiv"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-xs font-medium text-[#636366] transition-colors duration-200 hover:text-[#1C1C1E]"
          >
            <GithubLogo size={16} weight="regular" />
            GitHub
          </a>
        </div>
      </div>
    </motion.nav>
  )
}
