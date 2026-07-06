'use client'

import type { ReactNode } from 'react'
import { AppStoreProvider } from '@/shared/store'
import { TooltipProvider } from '@/shared/ui/tooltip'
import { Toaster } from '@/shared/ui/sonner'

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
