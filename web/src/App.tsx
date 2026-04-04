import { useEffect, useState } from 'react'
import {
  Bot,
  ChevronDown,
  LogOut,
  Menu,
  MessageCircle,
  MessageSquare,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Settings,
  X,
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
  sendTestTemplate,
  updateBot,
} from '@/lib/dashboard-api'
import { getBrowserSupabaseClient } from '@/lib/supabase-browser'
import { cn } from '@/lib/utils'
import type {
  BotConfig,
  DashboardUser,
  TemplateTestRequest,
} from '@/lib/types'

type Section = 'config' | 'template' | 'chat'

const NAV_ITEMS: { id: Section; label: string; icon: typeof Settings }[] = [
  { id: 'config', label: 'Config', icon: Settings },
  { id: 'template', label: 'Template', icon: MessageSquare },
  { id: 'chat', label: 'Chat', icon: MessageCircle },
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

  const [, setUser] = useState<DashboardUser | null>(null)
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
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(() => {
    if (typeof window === 'undefined') return false
    return window.localStorage.getItem('dashboard-sidebar-collapsed') === 'true'
  })

  useEffect(() => {
    window.localStorage.setItem(
      'dashboard-sidebar-collapsed',
      String(isSidebarCollapsed),
    )
  }, [isSidebarCollapsed])

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
    setMobileNavOpen(false)
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
        draftMode === 'new' ? 'Creato.' : 'Salvato.',
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
      setEditorNotice('Eliminato.')
      await refreshBots(null)
    } catch (error) {
      setEditorError(
        error instanceof DashboardApiError ? error.detail : 'Eliminazione fallita.',
      )
    } finally {
      setIsDeletingBot(false)
    }
  }

  async function handleSendTemplate(payload: TemplateTestRequest) {
    if (!accessToken) return

    setIsSendingTemplate(true)
    setTemplateError('')
    setTemplateNotice('')

    try {
      await sendTestTemplate(accessToken, draftBot.id, payload)
      setTemplateNotice('Template di test inviato e conversazione inizializzata.')
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

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-background text-foreground">
      <header className="flex h-14 flex-shrink-0 items-center gap-2 border-b border-border/60 bg-card/90 px-3 backdrop-blur lg:px-4">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#0078ff] text-white shadow-sm shadow-[#0078ff]/20">
            <Bot className="h-4 w-4" />
          </div>

          <Button
            variant="ghost"
            size="icon-sm"
            className="hidden lg:flex"
            onClick={() => setIsSidebarCollapsed((current) => !current)}
            aria-label={
              isSidebarCollapsed
                ? 'Espandi sidebar'
                : 'Comprimi sidebar'
            }
            title={
              isSidebarCollapsed
                ? 'Espandi sidebar'
                : 'Comprimi sidebar'
            }
          >
            {isSidebarCollapsed ? (
              <PanelLeftOpen className="h-4 w-4" />
            ) : (
              <PanelLeftClose className="h-4 w-4" />
            )}
          </Button>
        </div>

        <div className="relative min-w-0 flex-1 lg:max-w-sm">
          <select
            className="h-9 w-full cursor-pointer appearance-none rounded-lg border border-border/60 bg-background py-0 pr-8 pl-3 text-sm font-medium transition-colors hover:border-border focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30"
            value={selectedBotId ?? ''}
            onChange={(e) => {
              if (e.target.value) {
                selectBot(e.target.value)
                return
              }
              createNewDraft()
            }}
          >
            <option value="">Nuovo</option>
            {bots.map((bot) => (
              <option key={bot.id} value={bot.id}>
                {bot.name || bot.id}
              </option>
            ))}
          </select>
          <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
        </div>

        <div className="ml-auto flex items-center gap-1.5">
          {isLoadingDashboard ? (
            <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          ) : null}

          <Button
            variant="ghost"
            size="icon-sm"
            onClick={createNewDraft}
            aria-label="Nuovo bot"
            title="Nuovo bot"
          >
            <Plus className="h-4 w-4" />
          </Button>

          <Button
            variant="ghost"
            size="icon-sm"
            className="lg:hidden"
            onClick={() => setMobileNavOpen((current) => !current)}
            aria-label={mobileNavOpen ? 'Chiudi navigazione' : 'Apri navigazione'}
            title={mobileNavOpen ? 'Chiudi navigazione' : 'Apri navigazione'}
          >
            {mobileNavOpen ? (
              <X className="h-4 w-4" />
            ) : (
              <Menu className="h-4 w-4" />
            )}
          </Button>

          <Button
            variant="ghost"
            size="icon-sm"
            onClick={handleSignOut}
            aria-label="Esci"
            title="Esci"
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </header>

      {dashboardError ? (
        <div className="border-b border-destructive/20 bg-destructive/5 px-3 py-2 text-sm text-destructive lg:px-4">
          {dashboardError}
        </div>
      ) : null}

      <div className="relative flex min-h-0 flex-1 overflow-hidden">
        <aside
          className={cn(
            'absolute inset-y-0 left-0 z-30 flex h-full w-64 flex-col border-r border-border/60 bg-card/95 backdrop-blur transition-[width,transform] duration-200 lg:relative lg:inset-auto lg:z-auto lg:h-auto lg:bg-card',
            mobileNavOpen
              ? 'translate-x-0 shadow-xl lg:shadow-none'
              : '-translate-x-full lg:translate-x-0',
            isSidebarCollapsed ? 'lg:w-[4.5rem]' : 'lg:w-60',
          )}
        >
          <nav className="flex-1 p-2">
            {NAV_ITEMS.map((item) => {
              const isActive = activeSection === item.id
              const Icon = item.icon
              return (
                <button
                  key={item.id}
                  type="button"
                  className={cn(
                    'flex w-full items-center rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                    isSidebarCollapsed ? 'justify-center px-0' : 'gap-2.5',
                    isActive
                      ? 'bg-primary/[0.08] text-primary'
                      : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground',
                  )}
                  onClick={() => {
                    setActiveSection(item.id)
                    setMobileNavOpen(false)
                  }}
                  aria-label={item.label}
                  title={item.label}
                >
                  <Icon className="h-4 w-4 flex-shrink-0" />
                  {!isSidebarCollapsed ? (
                    <span className="truncate">{item.label}</span>
                  ) : null}
                </button>
              )
            })}
          </nav>
        </aside>

        {mobileNavOpen ? (
          <div
            className="fixed inset-0 z-20 bg-black/20 lg:hidden"
            onClick={() => setMobileNavOpen(false)}
          />
        ) : null}

        <main className="min-w-0 flex-1 overflow-y-auto p-3 lg:p-4">
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
              <div className="flex min-h-[24rem] items-center justify-center rounded-xl border border-border/60 bg-card px-6 text-sm font-medium text-muted-foreground shadow-sm">
                Salva il bot prima di aprire la chat
              </div>
            )
          ) : null}
        </main>
      </div>
    </div>
  )
}

export default App
