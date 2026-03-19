import { Nav } from "@/components/nav"
import { Hero } from "@/components/hero"
import { ProductSections } from "@/components/product-sections"
import { CtaSection } from "@/components/cta-section"
import { Footer } from "@/components/footer"

export default function Home() {
  return (
    <main>
      <Nav />
      <Hero />
      <ProductSections />
      <CtaSection />
      <Footer />
    </main>
  )
}
