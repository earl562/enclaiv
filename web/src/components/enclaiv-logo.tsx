"use client"

export function EnclaivLogo({ size = 24, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 28 28"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Outer hexagonal shield shape */}
      <path
        d="M14 1.5L24.5 7.5v13L14 26.5L3.5 20.5v-13L14 1.5z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
        fill="none"
      />
      {/* Inner concentric hexagon */}
      <path
        d="M14 7L20 10.5v7L14 21L8 17.5v-7L14 7z"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinejoin="round"
        fill="currentColor"
        fillOpacity="0.06"
      />
      {/* Center dot — the secured core */}
      <circle cx="14" cy="14" r="2.5" fill="#FF3B30" />
    </svg>
  )
}
