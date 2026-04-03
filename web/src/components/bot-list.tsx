import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
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
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <CardTitle>Bot</CardTitle>
          <Button size="sm" onClick={onCreate}>
            Nuovo
          </Button>
        </div>
      </CardHeader>

      <CardContent className="grid gap-3">
        {loading ? (
          <div className="rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
            Caricamento...
          </div>
        ) : null}

        {!loading && bots.length === 0 ? (
          <div className="rounded-lg border border-dashed bg-muted/20 p-3 text-sm text-muted-foreground">
            Nessun bot
          </div>
        ) : null}

        {bots.map((bot) => {
          const isActive = bot.id === selectedBotId
          return (
            <button
              key={bot.id}
              type="button"
              className={cn(
                'rounded-lg border p-3 text-left transition-colors',
                isActive
                  ? 'border-primary bg-accent'
                  : 'bg-background hover:bg-muted/30',
              )}
              onClick={() => onSelect(bot.id)}
            >
              <div className="space-y-1">
                <div className="font-medium">{bot.name}</div>
                <div className="text-sm text-muted-foreground">
                  {bot.company_name || bot.id}
                </div>
              </div>
            </button>
          )
        })}
      </CardContent>
    </Card>
  )
}
