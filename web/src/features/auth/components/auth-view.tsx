import { GeloLogo } from '@/shared/ui/gelo-logo'
import { Button } from '@/shared/ui/button'
import {
  Card,
  CardContent,
} from '@/shared/ui/card'
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
    <div className="min-h-screen bg-background text-foreground">
      <div className="grid min-h-screen lg:grid-cols-[1.1fr_0.9fr]">
        {/* Left panel - brand hero */}
        <div className="relative hidden overflow-hidden bg-[#0078ff] lg:flex lg:items-center lg:justify-center">
          {/* Decorative elements */}
          <div className="pointer-events-none absolute inset-0">
            <div className="absolute -left-32 -top-32 h-[500px] w-[500px] rounded-full bg-white/[0.06]" />
            <div className="absolute -bottom-40 -right-40 h-[600px] w-[600px] rounded-full bg-white/[0.04]" />
            <div className="absolute left-1/2 top-1/4 h-[300px] w-[300px] -translate-x-1/2 rounded-full bg-[#3399ff]/30 blur-[100px]" />
          </div>

          <div className="relative z-10 max-w-md px-12 text-white">
            <div className="mb-10 flex h-16 w-16 items-center justify-center rounded-2xl bg-white/10 backdrop-blur-sm">
              <GeloLogo className="h-8 w-8" />
            </div>
          </div>
        </div>

        {/* Right panel - login form */}
        <div className="flex items-center justify-center px-5 py-10 sm:px-8">
          <div className="mx-auto w-full max-w-sm">
            {/* Mobile brand */}
            <div className="mb-8 flex items-center gap-3 lg:hidden">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#0078ff]/10">
                <GeloLogo className="h-5 w-5" />
              </div>
            </div>

            <div className="mb-8">
              <h2 className="text-2xl font-[800] tracking-tight lg:text-3xl">Accedi</h2>
            </div>

            <Card className="border-border/60 shadow-sm">
              <CardContent className="pt-6">
                <form
                  className="grid gap-5"
                  onSubmit={(event) => {
                    event.preventDefault()
                    onSubmit()
                  }}
                >
                  <div className="grid gap-2">
                    <Label htmlFor="auth-email" className="text-sm font-semibold">
                      Email
                    </Label>
                    <Input
                      id="auth-email"
                      autoComplete="email"
                      autoFocus
                      placeholder="tu@esempio.com"
                      className="h-11 rounded-xl"
                      value={email}
                      onChange={(event) => onEmailChange(event.target.value)}
                    />
                  </div>

                  <div className="grid gap-2">
                    <Label htmlFor="auth-password" className="text-sm font-semibold">
                      Password
                    </Label>
                    <Input
                      id="auth-password"
                      type="password"
                      autoComplete="current-password"
                      placeholder="Password"
                      className="h-11 rounded-xl"
                      value={password}
                      onChange={(event) => onPasswordChange(event.target.value)}
                    />
                  </div>

                  {error ? (
                    <div className="rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
                      {error}
                    </div>
                  ) : null}

                  <Button
                    type="submit"
                    size="lg"
                    className="h-12 rounded-xl text-base font-bold shadow-md shadow-primary/20"
                    disabled={!email.trim() || !password.trim() || pending}
                  >
                    {pending ? 'Accesso...' : 'Accedi'}
                  </Button>
                </form>
              </CardContent>
            </Card>

          </div>
        </div>
      </div>
    </div>
  )
}
