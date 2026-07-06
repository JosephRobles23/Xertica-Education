import './globals.css'
import type { Metadata } from 'next'
import type { ReactNode } from 'react'
import { Space_Grotesk } from 'next/font/google'
import Providers from './providers'
import Layout from '@/shared/components/Layout'

const spaceGrotesk = Space_Grotesk({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-space-grotesk',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'xertica.education · Estudio',
  description: 'Estudio interno de autoría de contenido educativo asistido por IA.',
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es" className={spaceGrotesk.variable}>
      <body>
        <Providers>
          <Layout>{children}</Layout>
        </Providers>
      </body>
    </html>
  )
}
