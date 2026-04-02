import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

type AuthViewProps = {
  email: string
  error: string
  notice: string
  pending: boolean
  onEmailChange: (value: string) => void
  onSubmit: () => void
}

export function AuthView({
  email,
  error,
  notice,
  pending,
  onEmailChange,
  onSubmit,
}: AuthViewProps) {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(180,83,9,0.15),transparent_28%),linear-gradient(180deg,#faf8f5_0%,#ece7df_100%)] px-4 py-10 text-foreground">
      <div className="mx-auto flex min-h-[85vh] max-w-5xl items-center">
        <div className="grid w-full gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <Card className="border-none bg-card/90 shadow-xl backdrop-blur">
            <CardHeader className="gap-6">
              <Badge variant="outline" className="w-fit">
                Dashboard privata
              </Badge>
              <div className="space-y-3">
                <CardTitle className="text-4xl tracking-tight">
                  Un solo runtime, piu tenant, zero prompt hardcoded.
                </CardTitle>
                <CardDescription className="max-w-xl text-base leading-7">
                  Accedi con Supabase Auth via email e amministra i bot che
                  guidano la qualifica lead per numeri WhatsApp e clienti diversi.
                </CardDescription>
              </div>
            </CardHeader>
            <CardContent className="grid gap-4 text-sm text-muted-foreground">
              <div className="rounded-xl border border-foreground/10 bg-background/70 p-4">
                Configurazioni versionabili, campi dinamici, prompt tenant-specific
                e invio template da un'unica console.
              </div>
              <div className="rounded-xl border border-foreground/10 bg-background/70 p-4">
                In produzione le configurazioni vengono persistite su Supabase.
                I file JSON restano come seed e come base versionabile nel repo.
              </div>
            </CardContent>
          </Card>

          <Card className="border-none bg-card/95 shadow-xl">
            <CardHeader>
              <CardTitle>Login email</CardTitle>
              <CardDescription>
                Invia un magic link al tuo indirizzo. L'utente deve gia esistere
                in Supabase Auth.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4">
              <div className="grid gap-2">
                <Label htmlFor="auth-email">Email</Label>
                <Input
                  id="auth-email"
                  autoComplete="email"
                  placeholder="tuo.nome@azienda.it"
                  value={email}
                  onChange={(event) => onEmailChange(event.target.value)}
                />
              </div>

              {notice ? (
                <div className="rounded-lg border border-foreground/10 bg-muted/70 px-3 py-2 text-sm">
                  {notice}
                </div>
              ) : null}

              {error ? (
                <div className="rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 text-sm text-destructive">
                  {error}
                </div>
              ) : null}

              <Button onClick={onSubmit} disabled={!email.trim() || pending}>
                {pending ? 'Invio in corso...' : 'Invia magic link'}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
