import './globals.css'
import type { Metadata } from 'next'
import type { ReactNode } from 'react'
import Providers from './providers'
import Layout from '@/shared/components/Layout'

export const metadata: Metadata = {
  title: 'xertica.education · Estudio',
  description: 'Estudio interno de autoría de contenido educativo asistido por IA.',
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es">
      <body>
        <Providers>
          <Layout>{children}</Layout>
        </Providers>
      </body>
    </html>
  )
}
