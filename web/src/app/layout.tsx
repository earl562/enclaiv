import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"
import "./globals.css"

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
})

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
})

export const metadata: Metadata = {
  title: "Enclaiv — Securing AI Agents through Sandboxed Unikernels",
  description:
    "Hardware-isolated sandboxing for AI agents. Every agent runs in its own Unikraft VM. No API keys. No credentials. No attack surface.",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} antialiased`}
    >
      <body className="min-h-[100dvh] bg-[#F8F9FA] font-sans text-[#1C1C1E]">
        {children}
      </body>
    </html>
  )
}
