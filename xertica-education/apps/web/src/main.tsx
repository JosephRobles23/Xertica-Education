import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from '@/App'
import { AppStoreProvider } from '@/store'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Toaster } from '@/components/ui/sonner'
import '@/index.css'

const rootEl = document.getElementById('root')
if (!rootEl) throw new Error('#root not found')

ReactDOM.createRoot(rootEl).render(
  <React.StrictMode>
    <BrowserRouter>
      <AppStoreProvider>
        <TooltipProvider>
          <App />
          <Toaster />
        </TooltipProvider>
      </AppStoreProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
