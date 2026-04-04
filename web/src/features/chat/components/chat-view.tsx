import { useEffect, useRef, useState } from 'react'
import { ArrowLeft, Bot, User } from 'lucide-react'

import { listLeadMessages, listLeads } from '@/shared/lib/dashboard-api'
import { cn } from '@/shared/lib/utils'
import type { BotConfig, ChatMessage, LeadSummary } from '@/shared/lib/types'
import { Button } from '@/shared/ui/button'

const STATUS_COLORS: Record<string, string> = {
  new: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  in_progress: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300',
  qualified: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
  follow_up: 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300',
}

const STATUS_LABELS: Record<string, string> = {
  new: 'Nuovo',
  in_progress: 'In corso',
  qualified: 'Qualificato',
  follow_up: 'Da richiamare',
}

type ChatViewProps = {
  bot: BotConfig
  accessToken: string
}

export function ChatView({ bot, accessToken }: ChatViewProps) {
  const [leads, setLeads] = useState<LeadSummary[]>([])
  const [selectedWaId, setSelectedWaId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoadingLeads, setIsLoadingLeads] = useState(false)
  const [isLoadingMessages, setIsLoadingMessages] = useState(false)
  const [error, setError] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let active = true
    async function load() {
      setIsLoadingLeads(true)
      setError('')
      try {
        const data = await listLeads(accessToken, bot.id)
        if (active) {
          setLeads(data)
          setSelectedWaId(null)
          setMessages([])
        }
      } catch {
        if (active) setError('Impossibile caricare le conversazioni.')
      } finally {
        if (active) setIsLoadingLeads(false)
      }
    }
    void load()
    return () => { active = false }
  }, [accessToken, bot.id])

  useEffect(() => {
    if (!selectedWaId) return
    let active = true
    async function load() {
      setIsLoadingMessages(true)
      try {
        const data = await listLeadMessages(accessToken, bot.id, selectedWaId!)
        if (active) setMessages(data)
      } catch {
        if (active) setMessages([])
      } finally {
        if (active) setIsLoadingMessages(false)
      }
    }
    void load()
    return () => { active = false }
  }, [accessToken, bot.id, selectedWaId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const selectedLead = leads.find((l) => l.wa_id === selectedWaId)

  return (
    <div className="grid gap-3">
      {error ? (
        <div className="rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      ) : null}

      <div className="flex h-[calc(100vh-5.8rem)] min-h-[32rem] overflow-hidden rounded-xl border border-border/60 bg-card shadow-sm">
        <div
          className={cn(
            'flex w-full flex-col border-r border-border/60 md:w-80 md:flex-shrink-0',
            selectedWaId ? 'hidden md:flex' : 'flex',
          )}
        >
          <div className="flex-1 overflow-y-auto">
            {isLoadingLeads ? (
              <div className="flex items-center gap-3 p-4 text-sm text-muted-foreground">
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                Caricamento...
              </div>
            ) : leads.length === 0 ? (
              <div className="flex h-full items-center justify-center p-8 text-sm font-medium text-muted-foreground">
                Nessuna conversazione
              </div>
            ) : (
              <div>
                {leads.map((lead) => {
                  const isActive = lead.wa_id === selectedWaId
                  const statusColor = STATUS_COLORS[lead.qualification_status] ?? 'bg-muted text-muted-foreground'
                  const statusLabel = STATUS_LABELS[lead.qualification_status] ?? lead.qualification_status

                  return (
                    <button
                      key={lead.wa_id}
                      type="button"
                      className={cn(
                        'w-full border-b border-border/40 px-4 py-3 text-left transition-colors',
                        isActive
                          ? 'bg-primary/[0.06]'
                          : 'hover:bg-muted/40',
                      )}
                      onClick={() => setSelectedWaId(lead.wa_id)}
                    >
                      <div className="flex items-center gap-2">
                        <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-muted">
                          <User className="h-3.5 w-3.5 text-muted-foreground" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-1.5">
                            <span className="truncate text-sm font-semibold">+{lead.wa_id}</span>
                            <span className={cn('flex-shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-medium', statusColor)}>
                              {statusLabel}
                            </span>
                          </div>
                          {lead.summary ? (
                            <p className="mt-0.5 truncate text-xs text-muted-foreground">{lead.summary}</p>
                          ) : null}
                        </div>
                        <span className="flex-shrink-0 text-[10px] text-muted-foreground">
                          {lead.message_count}
                        </span>
                      </div>
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        </div>

        <div
          className={cn(
            'flex flex-1 flex-col',
            !selectedWaId ? 'hidden md:flex' : 'flex',
          )}
        >
          {!selectedWaId ? (
            <div className="flex flex-1 items-center justify-center text-sm font-medium text-muted-foreground">
              Apri una chat
            </div>
          ) : (
            <>
              <div className="flex h-12 flex-shrink-0 items-center gap-3 border-b border-border/60 px-4">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0 md:hidden"
                  onClick={() => setSelectedWaId(null)}
                >
                  <ArrowLeft className="h-4 w-4" />
                </Button>
                <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-primary/10">
                  <User className="h-3.5 w-3.5 text-primary" />
                </div>
                <div className="min-w-0 flex-1 truncate text-sm font-semibold">
                  +{selectedWaId}
                </div>
                {selectedLead ? (
                  <span className={cn('flex-shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium', STATUS_COLORS[selectedLead.qualification_status] ?? 'bg-muted text-muted-foreground')}>
                    {STATUS_LABELS[selectedLead.qualification_status] ?? selectedLead.qualification_status}
                  </span>
                ) : null}
              </div>

              <div className="flex-1 overflow-y-auto bg-muted/20 px-4 py-4 lg:px-6">
                {isLoadingMessages ? (
                  <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                    <span className="ml-2">Caricamento...</span>
                  </div>
                ) : messages.length === 0 ? (
                  <div className="py-12 text-center text-sm text-muted-foreground">
                    Nessun messaggio
                  </div>
                ) : (
                  <div className="mx-auto w-full max-w-4xl space-y-3">
                    {messages.map((msg, i) => (
                      <div
                        key={i}
                        className={cn(
                          'flex',
                          msg.role === 'user' ? 'justify-start' : 'justify-end',
                        )}
                      >
                        <div className={cn('flex max-w-[85%] items-end gap-2 md:max-w-[72%] lg:max-w-[42rem]', msg.role === 'assistant' && 'flex-row-reverse')}>
                          <div
                            className={cn(
                              'flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full',
                              msg.role === 'user'
                                ? 'bg-muted text-muted-foreground'
                                : 'bg-primary/15 text-primary',
                            )}
                          >
                            {msg.role === 'user' ? (
                              <User className="h-3 w-3" />
                            ) : (
                              <Bot className="h-3 w-3" />
                            )}
                          </div>
                          <div
                            className={cn(
                              'rounded-2xl px-3.5 py-2.5 text-[13px] leading-relaxed shadow-sm',
                              msg.role === 'user'
                                ? 'rounded-bl-sm bg-card'
                                : 'rounded-br-sm bg-primary text-primary-foreground',
                            )}
                          >
                            {msg.display}
                          </div>
                        </div>
                      </div>
                    ))}
                    <div ref={messagesEndRef} />
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
