import { useEffect, useRef, useState } from 'react'
import { ArrowLeft, Bot, MessageCircle, User } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { listLeadMessages, listLeads } from '@/lib/dashboard-api'
import type { BotConfig, ChatMessage, LeadSummary } from '@/lib/types'

const STATUS_COLORS: Record<string, string> = {
  new: 'bg-blue-100 text-blue-700',
  in_progress: 'bg-yellow-100 text-yellow-700',
  qualified: 'bg-green-100 text-green-700',
  follow_up: 'bg-orange-100 text-orange-700',
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
    <Card className="border-border/60 shadow-sm">
      <CardHeader className="border-b">
        <CardTitle className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
            <MessageCircle className="h-4 w-4 text-primary" />
          </div>
          Conversazioni
        </CardTitle>
      </CardHeader>

      <CardContent className="p-0">
        {error ? (
          <div className="px-4 py-3 text-sm text-destructive">{error}</div>
        ) : null}

        <div className="flex min-h-[420px]">
          {/* Lead list */}
          <div
            className={cn(
              'w-full border-r md:w-72 md:flex-shrink-0',
              selectedWaId ? 'hidden md:block' : 'block',
            )}
          >
            {isLoadingLeads ? (
              <div className="flex items-center gap-3 p-4 text-sm text-muted-foreground">
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                Caricamento...
              </div>
            ) : leads.length === 0 ? (
              <div className="p-6 text-center text-sm text-muted-foreground">
                <MessageCircle className="mx-auto mb-2 h-8 w-8 opacity-30" />
                <p className="font-medium">Nessuna conversazione</p>
                <p className="mt-1 text-xs">Le chat appariranno qui quando i lead scriveranno al bot</p>
              </div>
            ) : (
              <div className="divide-y">
                {leads.map((lead) => {
                  const isActive = lead.wa_id === selectedWaId
                  const statusColor = STATUS_COLORS[lead.qualification_status] ?? 'bg-muted text-muted-foreground'
                  const statusLabel = STATUS_LABELS[lead.qualification_status] ?? lead.qualification_status

                  return (
                    <button
                      key={lead.wa_id}
                      type="button"
                      className={cn(
                        'w-full px-4 py-3 text-left transition-colors',
                        isActive
                          ? 'bg-primary/[0.06]'
                          : 'hover:bg-muted/40',
                      )}
                      onClick={() => setSelectedWaId(lead.wa_id)}
                    >
                      <div className="flex items-center gap-2">
                        <span className="truncate text-sm font-semibold">
                          +{lead.wa_id}
                        </span>
                        <span className={cn('flex-shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium', statusColor)}>
                          {statusLabel}
                        </span>
                      </div>
                      {lead.summary ? (
                        <p className="mt-1 truncate text-xs text-muted-foreground">{lead.summary}</p>
                      ) : null}
                      <div className="mt-1 flex items-center gap-2 text-[10px] text-muted-foreground">
                        <span>{lead.message_count} messaggi</span>
                      </div>
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          {/* Chat panel */}
          <div
            className={cn(
              'flex flex-1 flex-col',
              !selectedWaId ? 'hidden md:flex' : 'flex',
            )}
          >
            {!selectedWaId ? (
              <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
                <div className="text-center">
                  <Bot className="mx-auto mb-2 h-10 w-10 opacity-20" />
                  <p>Seleziona una conversazione</p>
                </div>
              </div>
            ) : (
              <>
                {/* Chat header */}
                <div className="flex items-center gap-3 border-b px-4 py-3">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="md:hidden"
                    onClick={() => setSelectedWaId(null)}
                  >
                    <ArrowLeft className="h-4 w-4" />
                  </Button>
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold">+{selectedWaId}</div>
                    {selectedLead ? (
                      <div className="text-xs text-muted-foreground">
                        {STATUS_LABELS[selectedLead.qualification_status] ?? selectedLead.qualification_status}
                        {selectedLead.summary ? ` - ${selectedLead.summary}` : ''}
                      </div>
                    ) : null}
                  </div>
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto px-4 py-4">
                  {isLoadingMessages ? (
                    <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                      <span className="ml-2">Caricamento messaggi...</span>
                    </div>
                  ) : messages.length === 0 ? (
                    <div className="py-8 text-center text-sm text-muted-foreground">
                      Nessun messaggio
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {messages.map((msg, i) => (
                        <div
                          key={i}
                          className={cn(
                            'flex',
                            msg.role === 'user' ? 'justify-start' : 'justify-end',
                          )}
                        >
                          <div className={cn('flex max-w-[80%] items-end gap-2', msg.role === 'assistant' && 'flex-row-reverse')}>
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
                                'rounded-2xl px-3.5 py-2 text-sm leading-relaxed',
                                msg.role === 'user'
                                  ? 'rounded-bl-md bg-muted'
                                  : 'rounded-br-md bg-primary text-primary-foreground',
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
      </CardContent>
    </Card>
  )
}
