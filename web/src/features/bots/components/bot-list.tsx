import { cn } from '@/shared/lib/utils'
import type { BotConfig } from '@/shared/lib/types'
import { Button } from '@/shared/ui/button'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/shared/ui/card'

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
    <Card className="border-border/60 shadow-sm">
      <CardHeader className="border-b">
        <div className="flex items-center justify-between gap-3">
          <CardTitle>Bot</CardTitle>
          <Button size="sm" onClick={onCreate} className="rounded-xl">
            + Nuovo
          </Button>
        </div>
      </CardHeader>

      <CardContent className="grid gap-2 pt-4">
        {loading ? (
          <div className="flex items-center gap-3 rounded-xl border border-dashed bg-muted/30 p-4 text-sm text-muted-foreground">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            Caricamento...
          </div>
        ) : null}

        {!loading && bots.length === 0 ? (
          <div className="rounded-xl border border-dashed bg-muted/20 p-6 text-center text-sm text-muted-foreground">
            <p className="font-medium">Nessun bot</p>
          </div>
        ) : null}

        {bots.map((bot) => {
          const isActive = bot.id === selectedBotId
          return (
            <button
              key={bot.id}
              type="button"
              className={cn(
                'group rounded-xl border p-3.5 text-left transition-all',
                isActive
                  ? 'border-primary/30 bg-primary/[0.06] shadow-sm'
                  : 'border-transparent bg-background hover:border-border hover:bg-muted/40',
              )}
              onClick={() => onSelect(bot.id)}
            >
              <div className="flex items-start gap-3">
                <div
                  className={cn(
                    'mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg text-xs font-bold transition-colors',
                    isActive ? 'bg-primary/15 text-primary' : 'bg-muted text-muted-foreground group-hover:bg-primary/10 group-hover:text-primary',
                  )}
                >
                  {(bot.name || 'B')[0].toUpperCase()}
                </div>
                <div className="min-w-0">
                  <div className={cn('truncate font-semibold', isActive && 'text-primary')}>
                    {bot.name || 'Senza nome'}
                  </div>
                  <div className="mt-0.5 truncate text-xs text-muted-foreground">
                    {bot.company_name || bot.id}
                  </div>
                </div>
              </div>
            </button>
          )
        })}
      </CardContent>
    </Card>
  )
}
