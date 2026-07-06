'use client'

import type { ReactNode } from 'react'
import { AppStoreProvider } from '@/store'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Toaster } from '@/components/ui/sonner'

export default function Providers({ children }: { children: ReactNode }) {
  return (
    <AppStoreProvider>
      <TooltipProvider>
        {children}
        <Toaster />
      </TooltipProvider>
    </AppStoreProvider>
  )
}
