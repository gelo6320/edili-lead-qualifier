import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
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
    <div className="min-h-screen bg-background px-4 py-10 text-foreground">
      <div className="mx-auto flex min-h-[85vh] max-w-md items-center">
        <Card className="w-full">
          <CardHeader>
            <CardTitle>Login</CardTitle>
          </CardHeader>
          <CardContent>
            <form
              className="grid gap-4"
              onSubmit={(event) => {
                event.preventDefault()
                onSubmit()
              }}
            >
              <div className="grid gap-2">
                <Label htmlFor="auth-email">Email</Label>
                <Input
                  id="auth-email"
                  autoComplete="email"
                  autoFocus
                  value={email}
                  onChange={(event) => onEmailChange(event.target.value)}
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="auth-password">Password</Label>
                <Input
                  id="auth-password"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(event) => onPasswordChange(event.target.value)}
                />
              </div>

              {error ? (
                <div className="rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 text-sm text-destructive">
                  {error}
                </div>
              ) : null}

              <Button
                type="submit"
                disabled={!email.trim() || !password.trim() || pending}
              >
                {pending ? 'Accesso...' : 'Accedi'}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
