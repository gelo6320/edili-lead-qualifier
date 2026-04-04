import { useEffect, useState } from 'react'
import { Bot, LogOut } from 'lucide-react'

import { AuthView } from '@/components/auth-view'
import { BotEditor } from '@/components/bot-editor'
import { BotList } from '@/components/bot-list'
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
import type {
  BotConfig,
  DashboardUser,
  TemplateSendRequest,
} from '@/lib/types'

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

  useEffect(() => {
    let active = true
    let unsubscribe: (() => void) | null = null

    async function bootstrap() {
      try {
        const nextAppConfig = await getDashboardAppConfig()
        if (!active) {
          return
        }

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
        if (!active) {
          return
        }

        setAccessToken(session?.access_token ?? '')

        const {
          data: { subscription },
        } = client.auth.onAuthStateChange((_event, nextSession) => {
          if (!active) {
            return
          }
          setAccessToken(nextSession?.access_token ?? '')
        })
        unsubscribe = () => subscription.unsubscribe()
      } catch (error) {
        if (!active) {
          return
        }
        setConfigError(
          error instanceof Error
            ? error.message
            : 'Impossibile inizializzare la dashboard.',
        )
      } finally {
        if (active) {
          setIsBooting(false)
        }
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
        if (!active) {
          return
        }

        setUser(sessionPayload.user)
        setBots(botList)
        syncSelection(botList, selectedBotId)
      } catch (error) {
        if (!active) {
          return
        }

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
        if (active) {
          setIsLoadingDashboard(false)
        }
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
    if (!selectedBot) {
      return
    }

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
  }

  async function refreshBots(preferredBotId: string | null) {
    if (!accessToken) {
      return
    }

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

    if (error) {
      setAuthError(error.message)
    }

    setIsSigningIn(false)
  }

  async function handleSignOut() {
    if (!supabase) {
      return
    }

    await supabase.auth.signOut()
    setAuthPassword('')
    setAuthError('')
    setEditorNotice('')
    setEditorError('')
    setTemplateNotice('')
    setTemplateError('')
  }

  async function handleSaveBot() {
    if (!accessToken) {
      return
    }

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
    if (!accessToken || draftMode !== 'existing') {
      return
    }

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
    if (!accessToken) {
      return
    }

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
    <div className="min-h-screen bg-background text-foreground">
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col gap-6 p-4 md:p-6 lg:p-8">
        {/* Header */}
        <header className="flex items-center justify-between gap-4 rounded-2xl border border-border/60 bg-card px-5 py-4 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#0078ff] text-white shadow-md shadow-[#0078ff]/20">
              <Bot className="h-5 w-5" />
            </div>
            <div>
              <div className="text-base font-[800] tracking-tight">Lead Qualifier</div>
              <div className="text-xs text-muted-foreground">Dashboard di gestione</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden text-sm font-medium text-muted-foreground sm:block">
              {user?.email}
            </div>
            <Button variant="outline" size="sm" className="gap-1.5 rounded-xl" onClick={handleSignOut}>
              <LogOut className="h-3.5 w-3.5" />
              Esci
            </Button>
          </div>
        </header>

        {dashboardError ? (
          <div className="rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
            {dashboardError}
          </div>
        ) : null}

        <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
          <BotList
            bots={bots}
            loading={isLoadingDashboard}
            onCreate={createNewDraft}
            onSelect={selectBot}
            selectedBotId={selectedBotId}
          />

          <div className="grid gap-6">
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

            <SendTemplateCard
              bot={draftBot}
              error={templateError}
              notice={templateNotice}
              onSend={handleSendTemplate}
              pending={isSendingTemplate}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
