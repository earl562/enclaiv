"use client"

import { EnclaivLogo } from "./enclaiv-logo"

export function Footer() {
  const columns = [
    {
      title: "Product",
      links: [
        { label: "Network Proxy", href: "#products" },
        { label: "Credential Proxy", href: "#products" },
        { label: "Unikernel VMs", href: "#products" },
        { label: "Violation Tracking", href: "#products" },
      ],
    },
    {
      title: "Resources",
      links: [
        { label: "Documentation", href: "https://github.com/earl562/enclaiv#readme" },
        { label: "GitHub", href: "https://github.com/earl562/enclaiv" },
        { label: "Build Guide", href: "https://github.com/earl562/enclaiv/blob/main/BUILD.md" },
        { label: "Roadmap", href: "https://github.com/earl562/enclaiv/blob/main/PROGRESS.md" },
      ],
    },
    {
      title: "Community",
      links: [
        { label: "Contributing", href: "https://github.com/earl562/enclaiv" },
        { label: "License (Apache 2.0)", href: "https://github.com/earl562/enclaiv/blob/main/LICENSE" },
      ],
    },
  ]

  return (
    <footer className="border-t border-[#D1D1D6]/40 bg-white py-16">
      <div className="max-w-5xl px-6" style={{ marginInline: "auto" }}>
        <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <EnclaivLogo size={18} className="text-[#1C1C1E]" />
              <span className="font-mono text-sm font-semibold tracking-wider text-[#1C1C1E]">
                enclaiv
              </span>
            </div>
            <p className="text-xs leading-relaxed text-[#636366]">
              Hardware-isolated sandboxing
              <br />
              for AI agents.
            </p>
          </div>
          {columns.map((col) => (
            <div key={col.title}>
              <h4 className="text-[11px] font-semibold uppercase tracking-[0.15em] text-[#636366]">
                {col.title}
              </h4>
              <ul className="mt-4 space-y-3">
                {col.links.map((link) => (
                  <li key={link.label}>
                    <a
                      href={link.href}
                      className="text-sm text-[#636366] transition-colors duration-200 hover:text-[#1C1C1E]"
                    >
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-16 flex items-center justify-between border-t border-[#D1D1D6]/40 pt-8">
          <p className="text-xs text-[#636366]">© 2026 Enclaiv — Apache 2.0</p>
          <p className="text-xs text-[#636366]">
            Built by{" "}
            <a
              href="https://github.com/earl562"
              className="text-[#1C1C1E] transition-colors hover:text-[#FF3B30]"
            >
              Earl Perry
            </a>
          </p>
        </div>
      </div>
    </footer>
  )
}
