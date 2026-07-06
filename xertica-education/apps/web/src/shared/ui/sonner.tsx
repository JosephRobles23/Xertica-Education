import { Toaster as Sonner, type ToasterProps } from 'sonner'

const Toaster = ({ ...props }: ToasterProps) => {
  return (
    <Sonner
      theme="light"
      position="bottom-right"
      toastOptions={{
        style: {
          background: 'var(--card)',
          color: 'var(--card-foreground)',
          border: '1.5px solid var(--border)',
          borderRadius: '12px',
          boxShadow: '0 18px 44px rgba(27,16,51,.14)',
          fontSize: '13.5px',
        },
      }}
      {...props}
    />
  )
}

export { Toaster }
