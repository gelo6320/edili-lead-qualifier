import { Bot, Lock, Mail } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

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
              <Bot className="h-8 w-8" />
            </div>

            <h1 className="text-[2.75rem] font-[900] leading-[1.05] tracking-tight">
              Lead Qualifier
            </h1>
            <p className="mt-4 text-lg font-medium leading-relaxed text-white/70">
              Gestisci i tuoi bot WhatsApp, configura i campi di qualifica e invia template in un unico pannello.
            </p>

            <div className="mt-12 space-y-4">
              {[
                'Configurazione multi-bot',
                'Qualifica lead con AI',
                'Template WhatsApp integrati',
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-white/15">
                    <svg className="h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <span className="text-sm font-semibold text-white/80">{item}</span>
                </div>
              ))}
            </div>

            <div className="mt-14 text-xs font-semibold text-white/30">
              Powered by Gelo Digital
            </div>
          </div>
        </div>

        {/* Right panel - login form */}
        <div className="flex items-center justify-center px-5 py-10 sm:px-8">
          <div className="mx-auto w-full max-w-sm">
            {/* Mobile brand */}
            <div className="mb-8 flex items-center gap-3 lg:hidden">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#0078ff]/10">
                <Bot className="h-5 w-5 text-[#0078ff]" />
              </div>
              <span className="text-lg font-[800] tracking-tight">Lead Qualifier</span>
            </div>

            <div className="mb-8">
              <h2 className="text-2xl font-[800] tracking-tight lg:text-3xl">Accedi</h2>
              <p className="mt-2 text-sm text-muted-foreground">
                Inserisci le tue credenziali per accedere alla dashboard.
              </p>
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
                    <Label htmlFor="auth-email" className="flex items-center gap-2 text-sm font-semibold">
                      <Mail className="h-3.5 w-3.5 text-muted-foreground" />
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
                    <Label htmlFor="auth-password" className="flex items-center gap-2 text-sm font-semibold">
                      <Lock className="h-3.5 w-3.5 text-muted-foreground" />
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

            <p className="mt-6 text-center text-xs text-muted-foreground">
              Accesso riservato agli operatori autorizzati.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
