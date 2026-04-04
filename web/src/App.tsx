import { useEffect, useState } from 'react'
import {
  Bot,
  ChevronDown,
  LogOut,
  MessageCircle,
  MessageSquare,
  Plus,
  Settings,
} from 'lucide-react'

import { AuthView } from '@/components/auth-view'
import { BotEditor } from '@/components/bot-editor'
import { ChatView } from '@/components/chat-view'
import { SendTemplateCard } from '@/components/send-template-card'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  createEmptyBotConfig,
  cloneBotConfig,
} from '@/lib/bot-config'
import {
  createBot,
  DashboardApiError,
  deleteBot,
  getDashboardAppConfig,
  getDashboardSession,
  listBots,
  sendTemplate,
  updateBot,
} from '@/lib/dashboard-api'
import { getBrowserSupabaseClient } from '@/lib/supabase-browser'
import { cn } from '@/lib/utils'
import type {
  BotConfig,
  DashboardUser,
  TemplateSendRequest,
} from '@/lib/types'

type Section = 'config' | 'template' | 'chat'

const NAV_ITEMS: { id: Section; label: string; icon: typeof Settings }[] = [
  { id: 'config', label: 'Configurazione', icon: Settings },
  { id: 'template', label: 'Template WhatsApp', icon: MessageSquare },
  { id: 'chat', label: 'Conversazioni', icon: MessageCircle },
]

function App() {
  const [configError, setConfigError] = useState('')
  const [isBooting, setIsBooting] = useState(true)

  const [supabase, setSupabase] = useState<ReturnType<
    typeof getBrowserSupabaseClient
  > | null>(null)
  const [accessToken, setAccessToken] = useState('')

  const [authEmail, setAuthEmail] = useState('')
  const [authPassword, setAuthPassword] = useState('')
  const [authError, setAuthError] = useState('')
  const [isSigningIn, setIsSigningIn] = useState(false)

  const [user, setUser] = useState<DashboardUser | null>(null)
  const [bots, setBots] = useState<BotConfig[]>([])
  const [selectedBotId, setSelectedBotId] = useState<string | null>(null)
  const [draftBot, setDraftBot] = useState<BotConfig>(createEmptyBotConfig())
  const [draftMode, setDraftMode] = useState<'new' | 'existing'>('new')
  const [dashboardError, setDashboardError] = useState('')
  const [editorNotice, setEditorNotice] = useState('')
  const [editorError, setEditorError] = useState('')
  const [isLoadingDashboard, setIsLoadingDashboard] = useState(false)
  const [isSavingBot, setIsSavingBot] = useState(false)
  const [isDeletingBot, setIsDeletingBot] = useState(false)
  const [templateNotice, setTemplateNotice] = useState('')
  const [templateError, setTemplateError] = useState('')
  const [isSendingTemplate, setIsSendingTemplate] = useState(false)

  const [activeSection, setActiveSection] = useState<Section>('config')
  const [mobileNavOpen, setMobileNavOpen] = useState(false)

  useEffect(() => {
    let active = true
    let unsubscribe: (() => void) | null = null

    async function bootstrap() {
      try {
        const nextAppConfig = await getDashboardAppConfig()
        if (!active) return

        if (
          !nextAppConfig.supabase_url ||
          !nextAppConfig.supabase_publishable_key
        ) {
          setConfigError(
            'SUPABASE_URL e SUPABASE_PUBLISHABLE_KEY non sono configurate lato server.',
          )
          setIsBooting(false)
          return
        }

        const client = getBrowserSupabaseClient(nextAppConfig)
        setSupabase(client)

        const {
          data: { session },
        } = await client.auth.getSession()
        if (!active) return

        setAccessToken(session?.access_token ?? '')

        const {
          data: { subscription },
        } = client.auth.onAuthStateChange((_event, nextSession) => {
          if (!active) return
          setAccessToken(nextSession?.access_token ?? '')
        })
        unsubscribe = () => subscription.unsubscribe()
      } catch (error) {
        if (!active) return
        setConfigError(
          error instanceof Error
            ? error.message
            : 'Impossibile inizializzare la dashboard.',
        )
      } finally {
        if (active) setIsBooting(false)
      }
    }

    void bootstrap()

    return () => {
      active = false
      unsubscribe?.()
    }
  }, [])

  useEffect(() => {
    if (!accessToken) {
      setUser(null)
      setBots([])
      setSelectedBotId(null)
      setDraftBot(createEmptyBotConfig())
      setDraftMode('new')
      setDashboardError('')
      return
    }

    let active = true
    async function loadDashboard() {
      setIsLoadingDashboard(true)
      setDashboardError('')

      try {
        const [sessionPayload, botList] = await Promise.all([
          getDashboardSession(accessToken),
          listBots(accessToken),
        ])
        if (!active) return

        setUser(sessionPayload.user)
        setBots(botList)
        syncSelection(botList, selectedBotId)
      } catch (error) {
        if (!active) return

        const message =
          error instanceof DashboardApiError
            ? error.detail
            : 'Impossibile caricare i dati della dashboard.'
        setDashboardError(message)

        if (
          error instanceof DashboardApiError &&
          (error.status === 401 || error.status === 403) &&
          supabase
        ) {
          await supabase.auth.signOut()
        }
      } finally {
        if (active) setIsLoadingDashboard(false)
      }
    }

    void loadDashboard()

    return () => {
      active = false
    }
  }, [accessToken, supabase])

  function syncSelection(botList: BotConfig[], preferredBotId: string | null) {
    if (preferredBotId) {
      const selectedBot = botList.find((bot) => bot.id === preferredBotId)
      if (selectedBot) {
        setSelectedBotId(selectedBot.id)
        setDraftBot(cloneBotConfig(selectedBot))
        setDraftMode('existing')
        return
      }
    }

    if (botList.length > 0) {
      const firstBot = botList[0]
      setSelectedBotId(firstBot.id)
      setDraftBot(cloneBotConfig(firstBot))
      setDraftMode('existing')
      return
    }

    setSelectedBotId(null)
    setDraftBot(createEmptyBotConfig())
    setDraftMode('new')
  }

  function selectBot(botId: string) {
    const selectedBot = bots.find((bot) => bot.id === botId)
    if (!selectedBot) return

    setSelectedBotId(selectedBot.id)
    setDraftBot(cloneBotConfig(selectedBot))
    setDraftMode('existing')
    setEditorNotice('')
    setEditorError('')
    setTemplateNotice('')
    setTemplateError('')
  }

  function createNewDraft() {
    setSelectedBotId(null)
    setDraftBot(createEmptyBotConfig())
    setDraftMode('new')
    setEditorNotice('')
    setEditorError('')
    setActiveSection('config')
  }

  async function refreshBots(preferredBotId: string | null) {
    if (!accessToken) return

    const freshBots = await listBots(accessToken)
    setBots(freshBots)
    syncSelection(freshBots, preferredBotId)
  }

  async function handleSignIn() {
    if (!supabase) {
      setAuthError('Client Supabase non inizializzato.')
      return
    }

    setIsSigningIn(true)
    setAuthError('')

    const email = authEmail.trim().toLowerCase()
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password: authPassword,
    })

    if (error) setAuthError(error.message)
    setIsSigningIn(false)
  }

  async function handleSignOut() {
    if (!supabase) return

    await supabase.auth.signOut()
    setAuthPassword('')
    setAuthError('')
    setEditorNotice('')
    setEditorError('')
    setTemplateNotice('')
    setTemplateError('')
  }

  async function handleSaveBot() {
    if (!accessToken) return

    setIsSavingBot(true)
    setEditorError('')
    setEditorNotice('')

    try {
      const savedBot =
        draftMode === 'new'
          ? await createBot(accessToken, draftBot)
          : await updateBot(accessToken, draftBot)

      setEditorNotice(
        draftMode === 'new'
          ? 'Bot creato e persistito su Supabase.'
          : 'Configurazione aggiornata su Supabase.',
      )
      await refreshBots(savedBot.id)
    } catch (error) {
      setEditorError(
        error instanceof DashboardApiError
          ? error.detail
          : 'Salvataggio fallito.',
      )
    } finally {
      setIsSavingBot(false)
    }
  }

  async function handleDeleteBot() {
    if (!accessToken || draftMode !== 'existing') return

    setIsDeletingBot(true)
    setEditorError('')
    setEditorNotice('')

    try {
      await deleteBot(accessToken, draftBot.id)
      setEditorNotice('Bot eliminato.')
      await refreshBots(null)
    } catch (error) {
      setEditorError(
        error instanceof DashboardApiError ? error.detail : 'Eliminazione fallita.',
      )
    } finally {
      setIsDeletingBot(false)
    }
  }

  async function handleSendTemplate(payload: TemplateSendRequest) {
    if (!accessToken) return

    setIsSendingTemplate(true)
    setTemplateError('')
    setTemplateNotice('')

    try {
      await sendTemplate(accessToken, payload)
      setTemplateNotice('Template inviato con successo.')
    } catch (error) {
      setTemplateError(
        error instanceof DashboardApiError
          ? error.detail
          : 'Invio template fallito.',
      )
    } finally {
      setIsSendingTemplate(false)
    }
  }

  // --- Early returns for boot / config error / auth ---

  if (isBooting) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-6 text-foreground">
        <Card className="w-full max-w-sm border-border/60 shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-3">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              Caricamento...
            </CardTitle>
          </CardHeader>
        </Card>
      </div>
    )
  }

  if (configError) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-6 text-foreground">
        <Card className="w-full max-w-xl border-border/60 shadow-sm">
          <CardHeader>
            <CardTitle className="text-destructive">Config mancante</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">{configError}</CardContent>
        </Card>
      </div>
    )
  }

  if (!accessToken) {
    return (
      <AuthView
        email={authEmail}
        error={authError}
        password={authPassword}
        onEmailChange={setAuthEmail}
        onPasswordChange={setAuthPassword}
        onSubmit={handleSignIn}
        pending={isSigningIn}
      />
    )
  }

  // --- Main dashboard shell ---

  const selectedBotLabel =
    bots.find((b) => b.id === selectedBotId)?.name || (draftMode === 'new' ? 'Nuovo bot' : 'Seleziona bot')

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-background text-foreground">
      {/* ═══ Top bar ═══ */}
      <header className="flex h-14 flex-shrink-0 items-center gap-4 border-b border-border/60 bg-card px-4 lg:px-6">
        {/* Logo */}
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#0078ff] text-white shadow-sm shadow-[#0078ff]/20">
            <Bot className="h-4 w-4" />
          </div>
          <span className="hidden text-sm font-[800] tracking-tight sm:block">
            Lead Qualifier
          </span>
        </div>

        {/* Separator */}
        <div className="hidden h-6 w-px bg-border/60 sm:block" />

        {/* Bot selector */}
        <div className="relative flex-1 sm:flex-none">
          <select
            className="h-9 w-full cursor-pointer appearance-none rounded-lg border border-border/60 bg-background py-0 pr-8 pl-3 text-sm font-medium transition-colors hover:border-border focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30 sm:w-52"
            value={selectedBotId ?? ''}
            onChange={(e) => {
              if (e.target.value) selectBot(e.target.value)
            }}
          >
            {draftMode === 'new' ? (
              <option value="">Nuovo bot</option>
            ) : null}
            {bots.map((bot) => (
              <option key={bot.id} value={bot.id}>
                {bot.name || bot.id}
              </option>
            ))}
          </select>
          <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
        </div>

        {/* Mobile nav toggle */}
        <Button
          variant="ghost"
          size="sm"
          className="ml-auto lg:hidden"
          onClick={() => setMobileNavOpen(!mobileNavOpen)}
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d={mobileNavOpen ? 'M6 18L18 6M6 6l12 12' : 'M4 6h16M4 12h16M4 18h16'} />
          </svg>
        </Button>

        {/* Right side: user + logout */}
        <div className="ml-auto hidden items-center gap-3 lg:flex">
          {isLoadingDashboard ? (
            <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          ) : null}
          <span className="text-xs text-muted-foreground">{user?.email}</span>
          <Button variant="ghost" size="sm" className="gap-1.5" onClick={handleSignOut}>
            <LogOut className="h-3.5 w-3.5" />
            Esci
          </Button>
        </div>
      </header>

      {dashboardError ? (
        <div className="border-b border-destructive/20 bg-destructive/5 px-4 py-2.5 text-center text-sm text-destructive">
          {dashboardError}
        </div>
      ) : null}

      {/* ═══ Body: sidebar + main ═══ */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside
          className={cn(
            'flex w-56 flex-shrink-0 flex-col border-r border-border/60 bg-card transition-transform lg:translate-x-0',
            mobileNavOpen
              ? 'absolute inset-y-14 left-0 z-30 translate-x-0 shadow-xl'
              : 'absolute -translate-x-full lg:relative',
          )}
        >
          <nav className="flex-1 p-3">
            <div className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              Sezioni
            </div>
            {NAV_ITEMS.map((item) => {
              const isActive = activeSection === item.id
              const Icon = item.icon
              return (
                <button
                  key={item.id}
                  type="button"
                  className={cn(
                    'flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary/[0.08] text-primary'
                      : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground',
                  )}
                  onClick={() => {
                    setActiveSection(item.id)
                    setMobileNavOpen(false)
                  }}
                >
                  <Icon className="h-4 w-4 flex-shrink-0" />
                  {item.label}
                </button>
              )
            })}
          </nav>

          {/* Bottom actions */}
          <div className="border-t border-border/60 p-3">
            <Button
              variant="outline"
              size="sm"
              className="w-full justify-start gap-2 rounded-lg"
              onClick={() => {
                createNewDraft()
                setMobileNavOpen(false)
              }}
            >
              <Plus className="h-3.5 w-3.5" />
              Nuovo bot
            </Button>

            {/* Mobile-only: user + logout */}
            <div className="mt-3 flex items-center justify-between gap-2 lg:hidden">
              <span className="truncate text-xs text-muted-foreground">{user?.email}</span>
              <Button variant="ghost" size="sm" className="flex-shrink-0 gap-1.5" onClick={handleSignOut}>
                <LogOut className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        </aside>

        {/* Mobile overlay backdrop */}
        {mobileNavOpen ? (
          <div
            className="fixed inset-0 z-20 bg-black/20 lg:hidden"
            onClick={() => setMobileNavOpen(false)}
          />
        ) : null}

        {/* ═══ Main content ═══ */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          <div className="mx-auto max-w-4xl">
            {activeSection === 'config' ? (
              <BotEditor
                bot={draftBot}
                editorError={editorError}
                editorNotice={editorNotice}
                isDeleting={isDeletingBot}
                isNew={draftMode === 'new'}
                isSaving={isSavingBot}
                onChange={setDraftBot}
                onDelete={handleDeleteBot}
                onSave={handleSaveBot}
              />
            ) : null}

            {activeSection === 'template' ? (
              <SendTemplateCard
                bot={draftBot}
                error={templateError}
                notice={templateNotice}
                onSend={handleSendTemplate}
                pending={isSendingTemplate}
              />
            ) : null}

            {activeSection === 'chat' ? (
              draftMode === 'existing' ? (
                <ChatView bot={draftBot} accessToken={accessToken} />
              ) : (
                <Card className="border-border/60 shadow-sm">
                  <CardContent className="flex flex-col items-center justify-center py-16 text-center">
                    <MessageCircle className="mb-3 h-10 w-10 text-muted-foreground/30" />
                    <p className="text-sm font-medium text-muted-foreground">
                      Salva prima il bot per vedere le conversazioni
                    </p>
                  </CardContent>
                </Card>
              )
            ) : null}
          </div>
        </main>
      </div>
    </div>
  )
}

export default App
