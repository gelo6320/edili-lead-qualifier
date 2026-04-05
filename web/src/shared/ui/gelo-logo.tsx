import { cn } from '@/shared/lib/utils'

type GeloLogoProps = {
  className?: string
}

export function GeloLogo({ className }: GeloLogoProps) {
  return (
    <img
      src="/logo-gelo.svg"
      alt="Gelo"
      className={cn('h-5 w-5', className)}
    />
  )
}
