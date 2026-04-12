import { useEffect, useState } from 'react'
import {
  ChevronsLeft,
  ChevronsRight,
  type LucideIcon,
  Menu,
  MessageSquare,
  Plus,
  Send,
  Settings2,
  X,
} from 'lucide-react'

import { AuthView } from '@/features/auth/components/auth-view'
import { BotEditor } from '@/features/bots/components/bot-editor'
import { ChatView } from '@/features/chat/components/chat-view'
import { SendTemplateCard } from '@/features/templates/components/send-template-card'
import {
  cloneBotConfig,
  createEmptyBotConfig,
} from '@/shared/lib/bot-config'
import {
  crawlSite,
  createBot,
  DashboardApiError,
  deleteBot,
  getDashboardAppConfig,
  getDashboardSession,
  getMetaAssets,
  listBots,
  sendTestTemplate,
  startMetaOAuth,
  updateBot,
} from '@/shared/lib/dashboard-api'
import { getBrowserSupabaseClient } from '@/shared/lib/supabase-browser'
import type {
  BotConfig,
  DashboardAppConfig,
  DashboardUser,
  MetaAssetsPayload,
  TemplateTestRequest,
} from '@/shared/lib/types'
import { cn } from '@/shared/lib/utils'
import { Button } from '@/shared/ui/button'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/shared/ui/card'
import { GeloLogo } from '@/shared/ui/gelo-logo'

type Section = 'config' | 'template' | 'chat'

const NAV_ITEMS: {
  id: Section
  label: string
  icon: LucideIcon
}[] = [
  { id: 'config', label: 'Config', icon: Settings2 },
  { id: 'template', label: 'Template', icon: Send },
  { id: 'chat', label: 'Chat', icon: MessageSquare },
]

const EMPTY_META_ASSETS: MetaAssetsPayload = {
  connected: false,
  profile: null,
  waba_options: [],
}

type DashboardRefreshOptions = {
  preferredBotId: string | null
  includeMetaAssets?: boolean
}

function normalizeUrlMessage(value: string): string {
  return value.replaceAll('_', ' ')
}

function App() {
  const [configError, setConfigError] = useState('')
  const [isBooting, setIsBooting] = useState(true)
  const [appConfig, setAppConfig] = useState<DashboardAppConfig | null>(null)

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
  const [metaAssets, setMetaAssets] = useState<MetaAssetsPayload>(EMPTY_META_ASSETS)
  const [metaAssetsError, setMetaAssetsError] = useState('')
  const [isLoadingMetaAssets, setIsLoadingMetaAssets] = useState(false)
  const [isConnectingMeta, setIsConnectingMeta] = useState(false)
  const [crawlNotice, setCrawlNotice] = useState('')
  const [crawlError, setCrawlError] = useState('')
  const [isCrawlingSite, setIsCrawlingSite] = useState(false)

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

        setAppConfig(nextAppConfig)

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
      setMetaAssets(EMPTY_META_ASSETS)
      setMetaAssetsError('')
      setCrawlNotice('')
      setCrawlError('')
      setIsLoadingMetaAssets(false)
      return
    }

    let active = true
    async function loadAll() {
      setIsLoadingDashboard(true)
      setIsLoadingMetaAssets(true)
      setDashboardError('')
      setMetaAssetsError('')

      const [dashboardResult, assetsResult] = await Promise.allSettled([
        Promise.all([
          getDashboardSession(accessToken),
          listBots(accessToken),
        ]),
        getMetaAssets(accessToken),
      ])

      if (!active) return

      if (dashboardResult.status === 'fulfilled') {
        const [sessionPayload, botList] = dashboardResult.value
        setUser(sessionPayload.user)
        setBots(botList)
        syncSelection(botList, null)
      } else {
        const error = dashboardResult.reason
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
      }

      if (assetsResult.status === 'fulfilled') {
        setMetaAssets(assetsResult.value)
      } else {
        const error = assetsResult.reason
        setMetaAssetsError(
          error instanceof DashboardApiError
            ? error.detail
            : 'Impossibile caricare asset Meta.',
        )
      }

      setIsLoadingDashboard(false)
      setIsLoadingMetaAssets(false)
    }

    void loadAll()

    return () => {
      active = false
    }
  }, [accessToken, supabase])

  useEffect(() => {
    if (!accessToken || typeof window === 'undefined') {
      return
    }

    const url = new URL(window.location.href)
    const oauthStatus = url.searchParams.get('meta_oauth')
    if (!oauthStatus) {
      return
    }

    const message = normalizeUrlMessage(url.searchParams.get('message') ?? '')
    if (oauthStatus === 'success') {
      setEditorError('')
      setEditorNotice('Facebook collegato.')
    } else {
      setEditorNotice('')
      setEditorError(message || 'Connessione Facebook fallita.')
    }

    url.searchParams.delete('meta_oauth')
    url.searchParams.delete('message')
    const cleanUrl = `${url.pathname}${url.search}${url.hash}`
    window.history.replaceState({}, '', cleanUrl)
  }, [accessToken])

  function clearEditorFeedback() {
    setEditorNotice('')
    setEditorError('')
    setTemplateNotice('')
    setTemplateError('')
    setCrawlNotice('')
    setCrawlError('')
  }

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
    clearEditorFeedback()
  }

  function createNewDraft() {
    setSelectedBotId(null)
    setDraftBot(createEmptyBotConfig())
    setDraftMode('new')
    clearEditorFeedback()
    setActiveSection('config')
    setMobileNavOpen(false)
  }

  async function refreshDashboardData({
    preferredBotId,
    includeMetaAssets = false,
  }: DashboardRefreshOptions) {
    if (!accessToken) {
      if (includeMetaAssets) {
        setMetaAssets(EMPTY_META_ASSETS)
      }
      return
    }

    setIsLoadingDashboard(true)
    setDashboardError('')
    if (includeMetaAssets) {
      setIsLoadingMetaAssets(true)
      setMetaAssetsError('')
    }

    const [botsResult, assetsResult] = await Promise.allSettled([
      listBots(accessToken),
      includeMetaAssets ? getMetaAssets(accessToken) : Promise.resolve(null),
    ])

    if (botsResult.status === 'fulfilled') {
      setBots(botsResult.value)
      syncSelection(botsResult.value, preferredBotId)
    } else {
      const error = botsResult.reason
      setDashboardError(
        error instanceof DashboardApiError
          ? error.detail
          : 'Impossibile caricare i dati della dashboard.',
      )

      if (
        error instanceof DashboardApiError &&
        (error.status === 401 || error.status === 403) &&
        supabase
      ) {
        await supabase.auth.signOut()
      }
    }

    if (includeMetaAssets) {
      if (assetsResult.status === 'fulfilled' && assetsResult.value) {
        setMetaAssets(assetsResult.value)
      } else if (assetsResult.status === 'rejected') {
        const error = assetsResult.reason
        setMetaAssetsError(
          error instanceof DashboardApiError
            ? error.detail
            : 'Impossibile caricare asset Meta.',
        )
      }
    }

    setIsLoadingDashboard(false)
    if (includeMetaAssets) {
      setIsLoadingMetaAssets(false)
    }
  }

  async function refreshBots(
    preferredBotId: string | null,
    options?: Omit<DashboardRefreshOptions, 'preferredBotId'>,
  ) {
    await refreshDashboardData({
      preferredBotId,
      includeMetaAssets: options?.includeMetaAssets ?? false,
    })
  }

  async function refreshMetaAssets() {
    if (!accessToken) {
      setMetaAssets(EMPTY_META_ASSETS)
      return
    }

    setIsLoadingMetaAssets(true)
    setMetaAssetsError('')

    try {
      const assets = await getMetaAssets(accessToken)
      setMetaAssets(assets)
    } catch (error) {
      setMetaAssetsError(
        error instanceof DashboardApiError
          ? error.detail
          : 'Impossibile caricare asset Meta.',
      )
    } finally {
      setIsLoadingMetaAssets(false)
    }
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
    clearEditorFeedback()
    setMetaAssets(EMPTY_META_ASSETS)
    setMetaAssetsError('')
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

      setEditorNotice(draftMode === 'new' ? 'Creato.' : 'Salvato.')
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
      setTemplateNotice('Template inviato.')
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

  async function handleConnectMeta() {
    if (!accessToken || !appConfig?.meta_oauth_enabled) return

    setIsConnectingMeta(true)
    setEditorNotice('')
    setEditorError('')

    try {
      const payload = await startMetaOAuth(accessToken)
      window.location.assign(payload.authorize_url)
    } catch (error) {
      setEditorError(
        error instanceof DashboardApiError
          ? error.detail
          : "Impossibile avviare l'OAuth Facebook.",
      )
      setIsConnectingMeta(false)
    }
  }

  async function handleCrawlSite(siteUrl: string) {
    if (!accessToken || draftMode !== 'existing') return

    const normalizedUrl = siteUrl.trim()
    if (!normalizedUrl) {
      setCrawlError('Inserisci un URL valido prima di avviare il crawl.')
      return
    }

    setIsCrawlingSite(true)
    setCrawlNotice('')
    setCrawlError('')

    try {
      const result = await crawlSite(accessToken, draftBot.id, {
        site_url: normalizedUrl,
      })
      setCrawlNotice(
        `${result.pages_crawled} pagine · ${result.chunks_stored} chunk.`,
      )
      await refreshBots(result.bot.id)
    } catch (error) {
      setCrawlError(
        error instanceof DashboardApiError
          ? error.detail
          : 'Crawl sito fallito.',
      )
    } finally {
      setIsCrawlingSite(false)
    }
  }

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

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-background text-foreground">
      <header className="flex h-14 flex-shrink-0 items-center gap-2 border-b border-border/60 bg-card/90 px-3 backdrop-blur lg:px-4">
        <div className="flex items-center gap-2">
          <GeloLogo className="h-7 w-7" />

          <Button
            variant="ghost"
            size="icon-sm"
            className="hidden text-xs font-bold lg:flex"
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
              <ChevronsRight className="h-4 w-4" />
            ) : (
              <ChevronsLeft className="h-4 w-4" />
            )}
          </Button>
        </div>

        <div className="relative min-w-0 flex-1 lg:max-w-sm">
          <select
            className="h-9 w-full cursor-pointer appearance-none rounded-lg border border-border/60 bg-background py-0 pr-8 pl-3 text-sm font-medium transition-colors hover:border-border focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30"
            value={selectedBotId ?? ''}
            onChange={(event) => {
              if (event.target.value) {
                selectBot(event.target.value)
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
          <span className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">{'\u25BE'}</span>
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
            size="sm"
            className="text-xs"
            onClick={handleSignOut}
            aria-label="Esci"
            title="Esci"
          >
            Esci
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
                    isSidebarCollapsed ? 'justify-center px-2' : 'gap-2.5',
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
              cloudflareCrawlEnabled={Boolean(appConfig?.cloudflare_crawl_enabled)}
              crawlError={crawlError}
              crawlNotice={crawlNotice}
              editorError={editorError}
              editorNotice={editorNotice}
              isConnectingMeta={isConnectingMeta}
              isCrawlingSite={isCrawlingSite}
              isDeleting={isDeletingBot}
              isLoadingMetaAssets={isLoadingMetaAssets}
              isNew={draftMode === 'new'}
              isSaving={isSavingBot}
              metaAssets={metaAssets}
              metaAssetsError={metaAssetsError}
              metaOauthEnabled={Boolean(appConfig?.meta_oauth_enabled)}
              onChange={setDraftBot}
              onConnectMeta={handleConnectMeta}
              onCrawlSite={handleCrawlSite}
              onDelete={handleDeleteBot}
              onReloadMetaAssets={refreshMetaAssets}
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
                Salva prima
              </div>
            )
          ) : null}
        </main>
      </div>
    </div>
  )
}

export default App
