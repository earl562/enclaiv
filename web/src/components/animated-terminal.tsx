"use client"

import { useRef, useState, useEffect, useCallback, memo } from "react"
import { motion, useInView } from "framer-motion"

interface TerminalLine {
  label: string
  value: string
  color: "green" | "red" | "white" | "muted"
  delay: number
  isHeader?: boolean
}

interface AnimatedTerminalProps {
  lines: TerminalLine[]
  className?: string
}

const colorMap = {
  green: "text-green-500",
  red: "text-red-500",
  white: "text-zinc-900",
  muted: "text-zinc-400",
}

const TerminalValue = memo(function TerminalValue({
  line,
  triggered,
  cycleKey,
}: {
  line: TerminalLine
  triggered: boolean
  cycleKey: number
}) {
  const [phase, setPhase] = useState<"idle" | "loading" | "revealed">("idle")
  const [dots, setDots] = useState("")

  useEffect(() => {
    setPhase("idle")
    setDots("")
  }, [cycleKey])

  useEffect(() => {
    if (!triggered) return

    const startDelay = setTimeout(() => {
      setPhase("loading")
    }, line.delay * 1000 * 0.3)

    const dotInterval = setInterval(() => {
      setDots((prev) => (prev.length >= 3 ? "" : prev + "."))
    }, 350)

    const revealTimer = setTimeout(() => {
      clearInterval(dotInterval)
      setPhase("revealed")
    }, line.delay * 1000)

    return () => {
      clearTimeout(startDelay)
      clearTimeout(revealTimer)
      clearInterval(dotInterval)
    }
  }, [triggered, line.delay, cycleKey])

  if (phase === "idle") {
    return <span className="text-zinc-300">---</span>
  }

  if (phase === "loading") {
    return (
      <span className="text-zinc-400">
        {dots || "."}
        <span
          className="ml-0.5 inline-block animate-pulse"
          style={{ width: "1.5px", height: "14px", backgroundColor: "rgba(255,59,48,0.5)" }}
        />
      </span>
    )
  }

  return (
    <motion.span
      initial={{ opacity: 0, y: 6, filter: "blur(8px)" }}
      animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      transition={{ duration: 0.8, ease: [0.25, 0.46, 0.45, 0.94] }}
      className={`font-semibold ${colorMap[line.color]}`}
    >
      {line.value}
    </motion.span>
  )
})

export function AnimatedTerminal({ lines, className = "" }: AnimatedTerminalProps) {
  const ref = useRef<HTMLDivElement>(null)
  const isInView = useInView(ref, { once: true, amount: 0.2 })
  const [cycleKey, setCycleKey] = useState(0)
  const [triggered, setTriggered] = useState(false)

  const maxDelay = Math.max(...lines.filter((l) => !l.isHeader).map((l) => l.delay))

  const startCycle = useCallback(() => {
    setTriggered(true)
  }, [])

  useEffect(() => {
    if (!isInView) return
    startCycle()
  }, [isInView, startCycle])

  useEffect(() => {
    if (!triggered) return

    const holdTime = 2500
    const totalAnimTime = maxDelay * 1000 + holdTime

    const loopTimer = setTimeout(() => {
      setTriggered(false)
      setCycleKey((prev) => prev + 1)

      setTimeout(() => {
        setTriggered(true)
      }, 400)
    }, totalAnimTime)

    return () => clearTimeout(loopTimer)
  }, [triggered, maxDelay, cycleKey])

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: 0.9, ease: [0.25, 0.46, 0.45, 0.94] }}
      className={className}
    >
      <div
        className="overflow-hidden rounded-2xl"
        style={{
          border: "1px solid rgba(0,0,0,0.08)",
          background: "linear-gradient(145deg, #EAEAEF 0%, #E4E4E9 50%, #DEDEDF 100%)",
          padding: "6px",
          boxShadow: "0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03)",
        }}
      >
        <div
          className="rounded-xl"
          style={{
            background: "#FFFFFF",
            padding: "32px",
            border: "1px solid rgba(255,255,255,0.8)",
            boxShadow: "inset 0 1px 0 rgba(255,255,255,0.9), inset 0 -1px 0 rgba(0,0,0,0.02)",
          }}
        >
          <div className="font-mono text-sm" style={{ fontSize: "13px" }}>
            {lines.map((line, i) => {
              if (line.isHeader) {
                return (
                  <div
                    key={`${cycleKey}-${i}`}
                    className="text-zinc-400"
                    style={{
                      marginTop: i > 0 ? "28px" : "0",
                      paddingTop: i > 0 ? "28px" : "0",
                      borderTop: i > 0 ? "1px solid #E5E5EA" : "none",
                      marginBottom: "14px",
                      fontSize: "10px",
                      letterSpacing: "0.25em",
                      textTransform: "uppercase" as const,
                      fontWeight: 600,
                    }}
                  >
                    {line.label}
                  </div>
                )
              }

              return (
                <div
                  key={`${cycleKey}-${i}`}
                  className="flex items-center justify-between"
                  style={{ gap: "32px", padding: "10px 0" }}
                >
                  <span className="text-zinc-500">{line.label}</span>
                  <TerminalValue line={line} triggered={triggered} cycleKey={cycleKey} />
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </motion.div>
  )
}

interface AnimatedBarItem {
  label: string
  value: number
  displayValue: string
  highlight?: boolean
}

interface AnimatedBarsProps {
  items: AnimatedBarItem[]
  header: string
  className?: string
}

export const AnimatedBars = memo(function AnimatedBars({
  items,
  header,
  className = "",
}: AnimatedBarsProps) {
  const ref = useRef<HTMLDivElement>(null)
  const isInView = useInView(ref, { once: true, amount: 0.2 })
  const [cycleKey, setCycleKey] = useState(0)
  const [animating, setAnimating] = useState(false)

  const maxValue = Math.max(...items.map((i) => i.value))

  useEffect(() => {
    if (!isInView) return
    setAnimating(true)
  }, [isInView])

  useEffect(() => {
    if (!animating) return

    const totalTime = (items.length - 1) * 600 + 800 + 1800 + 2500

    const loopTimer = setTimeout(() => {
      setAnimating(false)
      setCycleKey((prev) => prev + 1)

      setTimeout(() => {
        setAnimating(true)
      }, 400)
    }, totalTime)

    return () => clearTimeout(loopTimer)
  }, [animating, items.length, cycleKey])

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: 0.9, ease: [0.25, 0.46, 0.45, 0.94] }}
      className={className}
    >
      <div
        className="overflow-hidden rounded-2xl"
        style={{
          border: "1px solid rgba(0,0,0,0.08)",
          background: "linear-gradient(145deg, #EAEAEF 0%, #E4E4E9 50%, #DEDEDF 100%)",
          padding: "6px",
          boxShadow: "0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03)",
        }}
      >
        <div
          className="rounded-xl"
          style={{
            background: "#FFFFFF",
            padding: "32px",
            border: "1px solid rgba(255,255,255,0.8)",
            boxShadow: "inset 0 1px 0 rgba(255,255,255,0.9), inset 0 -1px 0 rgba(0,0,0,0.02)",
          }}
        >
          <div
            className="text-zinc-400"
            style={{
              marginBottom: "20px",
              fontSize: "10px",
              letterSpacing: "0.25em",
              textTransform: "uppercase" as const,
              fontWeight: 600,
            }}
          >
            {header}
          </div>
          <div className="font-mono text-sm" style={{ fontSize: "13px" }}>
            {items.map((item, i) => (
              <div key={`${cycleKey}-${item.label}`} style={{ marginBottom: i < items.length - 1 ? "20px" : "0" }}>
                <div className="flex items-center justify-between" style={{ marginBottom: "8px" }}>
                  <span className={item.highlight ? "font-semibold text-red-500" : "text-zinc-500"}>
                    {item.label}
                  </span>
                  <span className={item.highlight ? "font-semibold text-red-500" : "text-zinc-400"}>
                    {item.displayValue}
                  </span>
                </div>
                <div
                  className="overflow-hidden rounded-full"
                  style={{ height: "10px", background: "#F2F2F7" }}
                >
                  <motion.div
                    className="h-full rounded-full"
                    style={{ background: item.highlight ? "#FF3B30" : "#C7C7CC" }}
                    initial={{ width: 0 }}
                    animate={animating ? { width: `${(item.value / maxValue) * 100}%` } : { width: 0 }}
                    transition={{
                      duration: 1.8,
                      ease: [0.25, 0.46, 0.45, 0.94],
                      delay: i * 0.6 + 0.8,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  )
})
