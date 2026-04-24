import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ArrowLeft, Loader2, Trash2 } from 'lucide-react'
import { GeloLogo } from '@/shared/ui/gelo-logo'

import {
  deleteLeadConversation,
  listLeadMessages,
  listLeads,
} from '@/shared/lib/dashboard-api'
import { cn } from '@/shared/lib/utils'
import type { BotConfig, ChatMessage, LeadSummary } from '@/shared/lib/types'
import { Button } from '@/shared/ui/button'

const STATUS_COLORS: Record<string, string> = {
  new: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
  in_progress: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
  qualified: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
  follow_up: 'bg-orange-500/10 text-orange-700 dark:text-orange-400',
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
  const [deletingWaId, setDeletingWaId] = useState<string | null>(null)
  const [error, setError] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const selectedWaIdRef = useRef<string | null>(null)

  useEffect(() => {
    selectedWaIdRef.current = selectedWaId
  }, [selectedWaId])

  const reloadLeads = useCallback(async (options?: { preserveSelection?: boolean }) => {
    const preserveSelection = options?.preserveSelection ?? false
    const currentSelectedWaId = selectedWaIdRef.current
    setIsLoadingLeads(true)
    setError('')
    try {
      const data = await listLeads(accessToken, bot.id)
      setLeads(data)

      if (!preserveSelection) {
        setSelectedWaId(null)
        setMessages([])
        return
      }

      if (!currentSelectedWaId) {
        setMessages([])
        return
      }

      const stillExists = data.some((lead) => lead.wa_id === currentSelectedWaId)
      if (!stillExists) {
        setSelectedWaId(null)
        setMessages([])
      }
    } catch {
      setError('Impossibile caricare le conversazioni.')
    } finally {
      setIsLoadingLeads(false)
    }
  }, [accessToken, bot.id])

  useEffect(() => {
    void reloadLeads()
  }, [reloadLeads])

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
    return () => {
      active = false
    }
  }, [accessToken, bot.id, selectedWaId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ block: 'end' })
  }, [messages])

  const selectedLead = useMemo(
    () => leads.find((lead) => lead.wa_id === selectedWaId),
    [leads, selectedWaId],
  )

  async function handleDeleteConversation(waId: string) {
    if (deletingWaId) return

    const confirmed = window.confirm(`Cancellare tutta la chat con +${waId}?`)
    if (!confirmed) return

    setDeletingWaId(waId)
    setError('')

    try {
      await deleteLeadConversation(accessToken, bot.id, waId)
      if (selectedWaId === waId) {
        setSelectedWaId(null)
        setMessages([])
      }
      await reloadLeads({ preserveSelection: true })
    } catch {
      setError('Impossibile cancellare la chat.')
    } finally {
      setDeletingWaId(null)
    }
  }

  return (
    <div className="grid gap-3">
      {error ? (
        <div className="rounded-md bg-destructive/10 px-3 py-2 text-xs font-medium text-destructive">
          {error}
        </div>
      ) : null}

      <div className="flex h-[calc(100vh-7.5rem)] min-h-[28rem] overflow-hidden rounded-md border border-border bg-card">
        <div
          className={cn(
            'flex w-full flex-col border-r border-border md:w-72 md:flex-shrink-0',
            selectedWaId ? 'hidden md:flex' : 'flex',
          )}
        >
          <div className="thin-scrollbar flex-1 overflow-y-auto">
            {isLoadingLeads ? (
              <div className="flex items-center gap-2 p-3 text-xs text-muted-foreground">
                <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
                Caricamento
              </div>
            ) : leads.length === 0 ? (
              <div className="flex h-full items-center justify-center p-6 text-sm text-muted-foreground">
                Nessuna conversazione
              </div>
            ) : (
              <ul className="divide-y divide-border">
                {leads.map((lead) => {
                  const isActive = lead.wa_id === selectedWaId
                  const statusColor =
                    STATUS_COLORS[lead.qualification_status] ?? 'bg-muted text-muted-foreground'
                  const statusLabel =
                    STATUS_LABELS[lead.qualification_status] ?? lead.qualification_status

                  return (
                    <li
                      key={lead.wa_id}
                      className={cn(
                        'group/lead flex items-center gap-1 [content-visibility:auto] [contain-intrinsic-size:56px]',
                        isActive ? 'bg-muted' : 'hover:bg-muted/50',
                      )}
                    >
                      <button
                        type="button"
                        className="min-w-0 flex-1 px-3 py-2 text-left"
                        onClick={() => setSelectedWaId(lead.wa_id)}
                      >
                        <div className="flex items-center gap-1.5">
                          <span className="truncate text-sm font-medium">+{lead.wa_id}</span>
                          <span
                            className={cn(
                              'flex-shrink-0 rounded-sm px-1.5 py-0.5 text-[10px] font-medium',
                              statusColor,
                            )}
                          >
                            {statusLabel}
                          </span>
                          <span className="ml-auto flex-shrink-0 text-[11px] text-muted-foreground">
                            {lead.message_count}
                          </span>
                        </div>
                        {lead.summary ? (
                          <p className="mt-0.5 truncate text-xs text-muted-foreground">
                            {lead.summary}
                          </p>
                        ) : null}
                      </button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon-sm"
                        className="mr-1 flex-shrink-0 text-muted-foreground opacity-0 transition-opacity hover:text-destructive group-hover/lead:opacity-100 aria-[busy=true]:opacity-100"
                        aria-busy={deletingWaId === lead.wa_id}
                        disabled={deletingWaId === lead.wa_id}
                        onClick={() => void handleDeleteConversation(lead.wa_id)}
                        title="Elimina chat"
                        aria-label={`Elimina chat +${lead.wa_id}`}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </li>
                  )
                })}
              </ul>
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
            <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
              Seleziona una conversazione
            </div>
          ) : (
            <>
              <div className="flex h-11 flex-shrink-0 items-center gap-2 border-b border-border px-3">
                <Button
                  variant="ghost"
                  size="icon-sm"
                  className="md:hidden"
                  onClick={() => setSelectedWaId(null)}
                  aria-label="Indietro"
                >
                  <ArrowLeft className="h-4 w-4" />
                </Button>
                <div className="min-w-0 flex-1 truncate text-sm font-medium">
                  +{selectedWaId}
                </div>
                {selectedLead ? (
                  <span
                    className={cn(
                      'flex-shrink-0 rounded-sm px-1.5 py-0.5 text-[10px] font-medium',
                      STATUS_COLORS[selectedLead.qualification_status] ??
                        'bg-muted text-muted-foreground',
                    )}
                  >
                    {STATUS_LABELS[selectedLead.qualification_status] ??
                      selectedLead.qualification_status}
                  </span>
                ) : null}
                <Button
                  type="button"
                  variant="ghost"
                  size="icon-sm"
                  className="text-muted-foreground hover:text-destructive"
                  disabled={!selectedWaId || deletingWaId === selectedWaId}
                  onClick={() =>
                    selectedWaId ? void handleDeleteConversation(selectedWaId) : undefined
                  }
                  title="Elimina chat"
                  aria-label="Elimina chat"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>

              <div className="thin-scrollbar flex-1 overflow-y-auto bg-muted/30 px-4 py-4">
                {isLoadingMessages ? (
                  <div className="flex items-center justify-center py-10 text-xs text-muted-foreground">
                    <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
                    <span className="ml-2">Caricamento</span>
                  </div>
                ) : messages.length === 0 ? (
                  <div className="py-10 text-center text-sm text-muted-foreground">
                    Nessun messaggio
                  </div>
                ) : (
                  <div className="mx-auto w-full max-w-3xl space-y-2">
                    {messages.map((msg, i) => (
                      <div
                        key={i}
                        className={cn(
                          'flex [content-visibility:auto] [contain-intrinsic-size:72px]',
                          msg.role === 'user' ? 'justify-start' : 'justify-end',
                        )}
                      >
                        <div
                          className={cn(
                            'flex max-w-[85%] items-end gap-1.5 md:max-w-[70%]',
                            msg.role === 'assistant' && 'flex-row-reverse',
                          )}
                        >
                          <div
                            className={cn(
                              'flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full',
                              msg.role === 'user'
                                ? 'bg-muted text-muted-foreground'
                                : 'bg-primary/15 text-primary',
                            )}
                          >
                            {msg.role === 'user' ? (
                              <span className="text-[9px] font-bold">U</span>
                            ) : (
                              <GeloLogo className="h-2.5 w-2.5" />
                            )}
                          </div>
                          <div
                            className={cn(
                              'rounded-lg px-3 py-2 text-[13px] leading-relaxed',
                              msg.role === 'user'
                                ? 'rounded-bl-sm bg-card ring-1 ring-border'
                                : 'rounded-br-sm bg-primary text-primary-foreground',
                            )}
                          >
                            <div className="space-y-2">
                              {msg.images.map((imageUrl, imageIndex) => (
                                <a
                                  key={`${i}-${imageIndex}-${imageUrl}`}
                                  href={imageUrl}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="block overflow-hidden rounded-md"
                                >
                                  <img
                                    src={imageUrl}
                                    alt="Immagine inviata dal lead"
                                    className="max-h-72 w-full rounded-md object-cover"
                                    decoding="async"
                                    loading="lazy"
                                  />
                                </a>
                              ))}
                              {msg.display ? <p>{msg.display}</p> : null}
                            </div>
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
