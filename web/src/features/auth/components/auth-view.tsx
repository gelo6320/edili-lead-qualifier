import { GeloLogo } from '@/shared/ui/gelo-logo'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Label } from '@/shared/ui/label'

type AuthViewProps = {
  email: string
  password: string
  error: string
  pending: boolean
  onEmailChange: (value: string) => void
  onPasswordChange: (value: string) => void
  onSubmit: () => void
}

export function AuthView({
  email,
  error,
  password,
  pending,
  onEmailChange,
  onPasswordChange,
  onSubmit,
}: AuthViewProps) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-10 text-foreground">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center gap-2">
          <GeloLogo className="h-7 w-7" />
          <span className="text-lg font-semibold tracking-tight">Lead Qualifier</span>
        </div>

        <div className="mb-5">
          <h1 className="text-xl font-semibold tracking-tight">Accedi</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Inserisci le tue credenziali per continuare.
          </p>
        </div>

        <form
          className="grid gap-3"
          onSubmit={(event) => {
            event.preventDefault()
            onSubmit()
          }}
        >
          <div className="grid gap-1.5">
            <Label htmlFor="auth-email" className="text-xs font-medium text-muted-foreground">
              Email
            </Label>
            <Input
              id="auth-email"
              autoComplete="email"
              autoFocus
              placeholder="tu@esempio.com"
              className="h-9 rounded-md"
              value={email}
              onChange={(event) => onEmailChange(event.target.value)}
            />
          </div>

          <div className="grid gap-1.5">
            <Label htmlFor="auth-password" className="text-xs font-medium text-muted-foreground">
              Password
            </Label>
            <Input
              id="auth-password"
              type="password"
              autoComplete="current-password"
              placeholder="Password"
              className="h-9 rounded-md"
              value={password}
              onChange={(event) => onPasswordChange(event.target.value)}
            />
          </div>

          {error ? (
            <div className="rounded-md bg-destructive/10 px-2.5 py-1.5 text-xs font-medium text-destructive">
              {error}
            </div>
          ) : null}

          <Button
            type="submit"
            className="mt-1 h-9"
            disabled={!email.trim() || !password.trim() || pending}
          >
            {pending ? 'Accesso...' : 'Accedi'}
          </Button>
        </form>
      </div>
    </div>
  )
}
