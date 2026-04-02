import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { cn } from '@/lib/utils'
import type { BotConfig } from '@/lib/types'

type BotListProps = {
  bots: BotConfig[]
  loading: boolean
  selectedBotId: string | null
  onSelect: (botId: string) => void
  onCreate: () => void
}

export function BotList({
  bots,
  loading,
  onCreate,
  onSelect,
  selectedBotId,
}: BotListProps) {
  return (
    <Card className="border-none bg-card/88 shadow-xl backdrop-blur">
      <CardHeader className="gap-4">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <CardTitle>Bot</CardTitle>
            <CardDescription>
              Ogni bot mappa prompt, campi richiesti e numero WhatsApp.
            </CardDescription>
          </div>
          <Button size="sm" onClick={onCreate}>
            Nuovo
          </Button>
        </div>
      </CardHeader>

      <CardContent className="grid gap-3">
        {loading ? (
          <div className="rounded-xl border border-foreground/10 bg-background/70 p-4 text-sm text-muted-foreground">
            Caricamento configurazioni...
          </div>
        ) : null}

        {!loading && bots.length === 0 ? (
          <div className="rounded-xl border border-dashed border-foreground/15 bg-background/70 p-4 text-sm text-muted-foreground">
            Nessun bot presente. Crea il primo tenant.
          </div>
        ) : null}

        {bots.map((bot) => {
          const isActive = bot.id === selectedBotId
          return (
            <button
              key={bot.id}
              type="button"
              className={cn(
                'rounded-2xl border p-4 text-left transition-all',
                isActive
                  ? 'border-transparent bg-primary text-primary-foreground shadow-lg'
                  : 'border-foreground/10 bg-background/70 hover:border-foreground/20 hover:bg-background',
              )}
              onClick={() => onSelect(bot.id)}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="font-medium">{bot.name}</div>
                  <div
                    className={cn(
                      'text-sm',
                      isActive
                        ? 'text-primary-foreground/75'
                        : 'text-muted-foreground',
                    )}
                  >
                    {bot.company_name || 'Azienda non impostata'}
                  </div>
                </div>
                <Badge variant={isActive ? 'secondary' : 'outline'}>{bot.id}</Badge>
              </div>

              <div className="mt-4 flex flex-wrap gap-2 text-xs">
                <Badge variant={isActive ? 'secondary' : 'outline'}>
                  {bot.fields.length} campi
                </Badge>
                <Badge variant={isActive ? 'secondary' : 'outline'}>
                  {bot.phone_number_id || 'phone_number_id mancante'}
                </Badge>
              </div>
            </button>
          )
        })}
      </CardContent>
    </Card>
  )
}
