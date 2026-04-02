import { useEffect, useState } from 'react'

import { AuthView } from '@/components/auth-view'
import { BotEditor } from '@/components/bot-editor'
import { BotList } from '@/components/bot-list'
import { SendTemplateCard } from '@/components/send-template-card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
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
  const [authNotice, setAuthNotice] = useState('')
  const [authError, setAuthError] = useState('')
  const [isSendingMagicLink, setIsSendingMagicLink] = useState(false)

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

  async function handleSendMagicLink() {
    if (!supabase) {
      setAuthError('Client Supabase non inizializzato.')
      return
    }

    setIsSendingMagicLink(true)
    setAuthError('')
    setAuthNotice('')

    const email = authEmail.trim().toLowerCase()
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: {
        shouldCreateUser: false,
        emailRedirectTo: window.location.origin,
      },
    })

    if (error) {
      setAuthError(error.message)
    } else {
      setAuthNotice('Email inviata. Apri il link ricevuto e torna su questa pagina.')
    }

    setIsSendingMagicLink(false)
  }

  async function handleSignOut() {
    if (!supabase) {
      return
    }

    await supabase.auth.signOut()
    setAuthNotice('')
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

  const requiredFields = draftBot.fields.filter((field) => field.required).length

  if (isBooting) {
    return (
      <div className="min-h-screen bg-[linear-gradient(180deg,#faf8f5_0%,#efebe5_100%)] p-6 text-foreground">
        <Card className="mx-auto mt-24 max-w-xl border-none bg-card/90 shadow-xl">
          <CardHeader>
            <CardTitle>Avvio dashboard</CardTitle>
            <CardDescription>
              Sto caricando Supabase Auth e le configurazioni del bot.
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }

  if (configError) {
    return (
      <div className="min-h-screen bg-[linear-gradient(180deg,#faf8f5_0%,#efebe5_100%)] p-6 text-foreground">
        <Card className="mx-auto mt-24 max-w-xl border-none bg-card/95 shadow-xl">
          <CardHeader>
            <Badge variant="outline" className="w-fit">
              Config mancante
            </Badge>
            <CardTitle>Dashboard non inizializzata</CardTitle>
            <CardDescription>{configError}</CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Imposta `SUPABASE_URL` e `SUPABASE_PUBLISHABLE_KEY` sul backend, poi
            ricostruisci il frontend.
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!accessToken) {
    return (
      <AuthView
        email={authEmail}
        error={authError}
        notice={authNotice}
        onEmailChange={setAuthEmail}
        onSubmit={handleSendMagicLink}
        pending={isSendingMagicLink}
      />
    )
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(180,83,9,0.12),transparent_32%),radial-gradient(circle_at_top_right,rgba(15,23,42,0.08),transparent_28%),linear-gradient(180deg,#faf8f5_0%,#ece7df_100%)] text-foreground">
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col gap-6 p-4 md:p-6">
        <Card className="border-none bg-card/85 shadow-xl backdrop-blur">
          <CardHeader className="gap-4">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
              <div className="space-y-3">
                <Badge variant="outline" className="w-fit">
                  Multi-tenant runtime
                </Badge>
                <div className="space-y-1">
                  <CardTitle className="text-3xl tracking-tight">
                    Lead Qualifier Control
                  </CardTitle>
                  <CardDescription className="max-w-2xl text-sm">
                    Un singolo runtime WhatsApp con configurazioni bot versionabili
                    in file seed e persistite in Supabase per uso reale.
                  </CardDescription>
                </div>
              </div>

              <div className="flex flex-col gap-3 md:items-end">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge>{user?.email ?? 'utente sconosciuto'}</Badge>
                  <Badge variant="secondary">
                    {bots.length} bot
                  </Badge>
                  <Badge variant="secondary">
                    {requiredFields} campi richiesti
                  </Badge>
                </div>
                <Button variant="outline" onClick={handleSignOut}>
                  Esci
                </Button>
              </div>
            </div>
          </CardHeader>
        </Card>

        {dashboardError ? (
          <Card className="border-none bg-destructive/5 shadow-sm">
            <CardContent className="pt-4 text-sm text-destructive">
              {dashboardError}
            </CardContent>
          </Card>
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

            <Separator className="bg-foreground/10" />

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
