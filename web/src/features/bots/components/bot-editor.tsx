import { useEffect } from 'react'
import { FieldListEditor } from '@/features/bots/components/field-list-editor'
import {
  commaSeparatedToList,
  listToCommaSeparated,
} from '@/shared/lib/bot-config'
import type {
  BotConfig,
  LeadManagerPageOption,
  MetaAssetsPayload,
  MetaWabaOption,
} from '@/shared/lib/types'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Label } from '@/shared/ui/label'
import { Textarea } from '@/shared/ui/textarea'

const SELECT_CLASS_NAME =
  'h-11 w-full cursor-pointer rounded-xl border border-border/60 bg-background px-3 text-sm transition-colors hover:border-border focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30 disabled:cursor-not-allowed disabled:opacity-60'

type BotEditorProps = {
  bot: BotConfig
  isNew: boolean
  isSaving: boolean
  isDeleting: boolean
  editorNotice: string
  editorError: string
  metaOauthEnabled: boolean
  cloudflareCrawlEnabled: boolean
  metaAssets: MetaAssetsPayload
  metaAssetsError: string
  isLoadingMetaAssets: boolean
  isConnectingMeta: boolean
  isCrawlingSite: boolean
  crawlNotice: string
  crawlError: string
  onChange: (bot: BotConfig) => void
  onSave: () => void
  onDelete: () => void
  onConnectMeta: () => void
  onReloadMetaAssets: () => void
  onCrawlSite: (siteUrl: string) => void
}

function formatDateTime(value: string): string {
  if (!value) {
    return 'Scadenza non disponibile'
  }

  const date = new Date(value)
  if (Number.isNaN(date.valueOf())) {
    return value
  }

  return new Intl.DateTimeFormat('it-IT', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

function getSelectedWaba(
  bot: BotConfig,
  metaAssets: MetaAssetsPayload,
): MetaWabaOption | null {
  return metaAssets.waba_options.find((item) => item.id === bot.meta_waba_id) ?? null
}

function matchTemplate(bot: BotConfig, templateOptions: MetaWabaOption['templates']) {
  if (bot.default_template_id.trim()) {
    const byId = templateOptions.find((item) => item.id === bot.default_template_id)
    if (byId) {
      return byId
    }
  }

  const templateName = bot.default_template_name.trim()
  if (!templateName) {
    return null
  }

  const templateLanguage = bot.template_language.trim().toLowerCase()
  const byNameAndLanguage = templateOptions.find(
    (item) =>
      item.name === templateName &&
      item.language.trim().toLowerCase() === templateLanguage,
  )
  if (byNameAndLanguage) {
    return byNameAndLanguage
  }

  return templateOptions.find((item) => item.name === templateName) ?? null
}

function getSelectedPage(
  bot: BotConfig,
  metaAssets: MetaAssetsPayload,
): LeadManagerPageOption | null {
  return metaAssets.page_options.find((item) => item.id === bot.lead_manager_page_id) ?? null
}

function isPageReservedForAnotherBot(page: LeadManagerPageOption, botId: string): boolean {
  return Boolean(page.qualifier_bot_id && page.qualifier_bot_id !== botId)
}

export function BotEditor({
  bot,
  cloudflareCrawlEnabled,
  crawlError,
  crawlNotice,
  editorError,
  editorNotice,
  isConnectingMeta,
  isCrawlingSite,
  isDeleting,
  isLoadingMetaAssets,
  isNew,
  isSaving,
  metaAssets,
  metaAssetsError,
  metaOauthEnabled,
  onChange,
  onConnectMeta,
  onCrawlSite,
  onDelete,
  onReloadMetaAssets,
  onSave,
}: BotEditorProps) {
  const selectedWaba = getSelectedWaba(bot, metaAssets)
  const selectedPage = getSelectedPage(bot, metaAssets)
  const phoneOptions = selectedWaba?.phone_numbers ?? []
  const templateOptions = selectedWaba?.templates ?? []
  const selectedTemplate = matchTemplate(bot, templateOptions)
  const selectedTemplateBody = selectedTemplate?.body_text || bot.default_template_body_text
  const hasPageOptions = metaAssets.page_options.length > 0

  function patch<K extends keyof BotConfig>(key: K, value: BotConfig[K]) {
    onChange({ ...bot, [key]: value })
  }

  function patchMany(nextPatch: Partial<BotConfig>) {
    onChange({ ...bot, ...nextPatch })
  }

  useEffect(() => {
    if (!selectedTemplate) {
      return
    }

    const nextPatch: Partial<BotConfig> = {}
    if (bot.default_template_id !== selectedTemplate.id) {
      nextPatch.default_template_id = selectedTemplate.id
    }
    if (bot.default_template_name !== selectedTemplate.name) {
      nextPatch.default_template_name = selectedTemplate.name
    }
    if (bot.default_template_body_text !== selectedTemplate.body_text) {
      nextPatch.default_template_body_text = selectedTemplate.body_text
    }
    if (bot.default_template_variable_count !== selectedTemplate.body_variable_count) {
      nextPatch.default_template_variable_count = selectedTemplate.body_variable_count
    }
    if (bot.template_language !== selectedTemplate.language) {
      nextPatch.template_language = selectedTemplate.language
    }

    if (Object.keys(nextPatch).length > 0) {
      patchMany(nextPatch)
    }
  }, [
    bot.default_template_body_text,
    bot.default_template_id,
    bot.default_template_name,
    bot.default_template_variable_count,
    bot.template_language,
    selectedTemplate,
  ])

  function handleWabaChange(wabaId: string) {
    if (!wabaId) {
      patchMany({
        meta_business_id: '',
        meta_business_name: '',
        meta_waba_id: '',
        meta_waba_name: '',
        phone_number_id: '',
        whatsapp_display_phone_number: '',
        default_template_id: '',
        default_template_name: '',
        default_template_body_text: '',
        default_template_variable_count: 0,
        template_language: 'it',
      })
      return
    }

    const nextWaba = metaAssets.waba_options.find((item) => item.id === wabaId)
    if (!nextWaba) {
      return
    }

    const nextPhone =
      nextWaba.phone_numbers.find((item) => item.id === bot.phone_number_id) ?? null
    const nextTemplate = matchTemplate(bot, nextWaba.templates)

    patchMany({
      meta_business_id: nextWaba.business_id,
      meta_business_name: nextWaba.business_name,
      meta_waba_id: nextWaba.id,
      meta_waba_name: nextWaba.name,
      phone_number_id: nextPhone?.id ?? '',
      whatsapp_display_phone_number: nextPhone?.display_phone_number ?? '',
      default_template_id: nextTemplate?.id ?? '',
      default_template_name: nextTemplate?.name ?? '',
      default_template_body_text: nextTemplate?.body_text ?? '',
      default_template_variable_count: nextTemplate?.body_variable_count ?? 0,
      template_language: nextTemplate?.language ?? 'it',
    })
  }

  function handlePhoneNumberChange(phoneNumberId: string) {
    const nextPhone =
      phoneOptions.find((item) => item.id === phoneNumberId) ?? null
    patchMany({
      phone_number_id: nextPhone?.id ?? '',
      whatsapp_display_phone_number: nextPhone?.display_phone_number ?? '',
    })
  }

  function handleTemplateChange(templateId: string) {
    const nextTemplate =
      templateOptions.find((item) => item.id === templateId) ?? null
    patchMany({
      default_template_id: nextTemplate?.id ?? '',
      default_template_name: nextTemplate?.name ?? '',
      default_template_body_text: nextTemplate?.body_text ?? '',
      default_template_variable_count: nextTemplate?.body_variable_count ?? 0,
      template_language: nextTemplate?.language ?? 'it',
    })
  }

  function handleLeadManagerPageChange(pageId: string) {
    const nextPage =
      metaAssets.page_options.find((item) => item.id === pageId) ?? null
    patchMany({
      lead_manager_page_id: nextPage?.id ?? '',
      lead_manager_page_name: nextPage?.name ?? '',
    })
  }

  return (
    <div className="grid gap-6">
      <div className="flex flex-col gap-3 rounded-xl border border-border/60 bg-card p-3 shadow-sm md:flex-row md:items-center md:justify-between">
        <div className="flex min-w-0 flex-1 flex-col gap-2">
          {editorNotice ? (
            <div className="flex items-center gap-2 rounded-xl border border-primary/20 bg-primary/5 px-3 py-2 text-sm font-medium text-primary">
              <svg className="h-4 w-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              {editorNotice}
            </div>
          ) : null}

          {editorError ? (
            <div className="rounded-xl border border-destructive/20 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              {editorError}
            </div>
          ) : null}
        </div>

        <div className="flex shrink-0 gap-2">
          {!isNew ? (
            <Button
              variant="destructive"
              className="rounded-xl"
              onClick={onDelete}
              disabled={isDeleting}
              type="button"
            >
              {isDeleting ? 'Eliminazione...' : 'Elimina'}
            </Button>
          ) : null}

          <Button
            onClick={onSave}
            disabled={isSaving}
            className="rounded-xl shadow-sm shadow-primary/20"
            type="button"
          >
            {isSaving ? 'Salvataggio...' : 'Salva'}
          </Button>
        </div>
      </div>

      <section className="grid gap-4 rounded-xl border border-border/60 bg-card p-4 shadow-sm">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div className="grid gap-1">
            <h2 className="text-sm font-semibold">Connessione Meta e routing lead</h2>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={metaAssets.connected ? 'default' : 'outline'}>
              {metaAssets.connected ? 'Facebook collegato' : 'Facebook non collegato'}
            </Badge>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          {metaOauthEnabled ? (
            <Button
              type="button"
              variant={metaAssets.connected ? 'outline' : 'default'}
              className="rounded-xl"
              onClick={onConnectMeta}
              disabled={isConnectingMeta}
            >
              {isConnectingMeta
                ? 'Reindirizzamento...'
                : metaAssets.connected
                  ? 'Ricollega Facebook'
                  : 'Collega Facebook'}
            </Button>
          ) : null}

          <Button
            type="button"
            variant="outline"
            className="rounded-xl"
            onClick={onReloadMetaAssets}
            disabled={isLoadingMetaAssets}
          >
            {isLoadingMetaAssets ? 'Aggiornamento...' : 'Ricarica asset'}
          </Button>
        </div>

        {!metaOauthEnabled ? (
            <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-sm text-amber-700">
            Per usare l'OAuth Meta devi configurare `META_APP_ID`, `META_APP_SECRET`, `APP_BASE_URL` e `OAUTH_STATE_SECRET` sul backend.
            </div>
        ) : null}

        {metaAssets.profile ? (
          <div className="rounded-xl border border-border/60 bg-muted/20 px-4 py-3 text-sm text-muted-foreground">
            <span className="font-semibold text-foreground">{metaAssets.profile.name}</span>
            {' '}· {formatDateTime(metaAssets.profile.token_expires_at)}
          </div>
        ) : null}

        {metaAssetsError ? (
          <div className="rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
            {metaAssetsError}
          </div>
        ) : null}

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="grid gap-2">
            <Label htmlFor="meta-waba" className="text-sm font-semibold">Account WhatsApp Business</Label>
            <select
              id="meta-waba"
              className={SELECT_CLASS_NAME}
              value={bot.meta_waba_id}
              onChange={(event) => handleWabaChange(event.target.value)}
              disabled={!metaAssets.waba_options.length}
            >
              <option value="">
                {metaAssets.waba_options.length ? 'Seleziona WABA' : 'Nessun WABA'}
              </option>
              {metaAssets.waba_options.map((waba) => (
                <option key={waba.id} value={waba.id}>
                  {waba.name} - {waba.business_name}
                </option>
              ))}
            </select>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="meta-phone-number" className="text-sm font-semibold">Numero invio WhatsApp</Label>
            <select
              id="meta-phone-number"
              className={SELECT_CLASS_NAME}
              value={bot.phone_number_id}
              onChange={(event) => handlePhoneNumberChange(event.target.value)}
              disabled={!selectedWaba}
            >
              <option value="">
                {selectedWaba ? 'Seleziona numero' : 'Seleziona WABA'}
              </option>
              {phoneOptions.map((phone) => (
                <option key={phone.id} value={phone.id}>
                  {phone.display_phone_number || phone.id}
                  {phone.verified_name ? ` - ${phone.verified_name}` : ''}
                </option>
              ))}
            </select>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="meta-template" className="text-sm font-semibold">Template iniziale</Label>
            <select
              id="meta-template"
              className={SELECT_CLASS_NAME}
              value={selectedTemplate?.id ?? bot.default_template_id}
              onChange={(event) => handleTemplateChange(event.target.value)}
              disabled={!selectedWaba}
            >
              <option value="">
                {selectedWaba ? 'Seleziona template' : 'Seleziona WABA'}
              </option>
              {templateOptions.map((template) => (
                <option key={template.id || `${template.name}-${template.language}`} value={template.id}>
                  {template.name} - {template.language}
                </option>
              ))}
            </select>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="lead-manager-page" className="text-sm font-semibold">Pagina lead-manager</Label>
            <select
              id="lead-manager-page"
              className={SELECT_CLASS_NAME}
              value={bot.lead_manager_page_id}
              onChange={(event) => handleLeadManagerPageChange(event.target.value)}
              disabled={!hasPageOptions}
            >
              <option value="">
                {hasPageOptions ? 'Seleziona pagina' : 'Nessuna pagina disponibile'}
              </option>
              {metaAssets.page_options.map((page) => {
                const disabled = isPageReservedForAnotherBot(page, bot.id)
                return (
                  <option key={page.id} value={page.id} disabled={disabled}>
                    {page.name}
                    {page.is_active === 'true' ? '' : ' - inattiva'}
                    {disabled ? ` - assegnata a ${page.qualifier_bot_name || page.qualifier_bot_id}` : ''}
                  </option>
                )
              })}
            </select>
          </div>
        </div>

        {selectedPage?.qualifier_bot_id && selectedPage.qualifier_bot_id !== bot.id ? (
          <div className="rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
            Pagina gia assegnata a {selectedPage.qualifier_bot_name || selectedPage.qualifier_bot_id}.
          </div>
        ) : null}

        {selectedTemplateBody ? (
          <div className="rounded-xl border border-border/60 bg-muted/20 px-4 py-3 text-sm text-muted-foreground">
            <div className="font-semibold text-foreground">Contenuto template nel contesto agente</div>
            <p className="mt-2 whitespace-pre-wrap">{selectedTemplateBody}</p>
          </div>
        ) : null}
      </section>

      <section className="grid gap-4 rounded-xl border border-border/60 bg-card p-4 shadow-sm sm:grid-cols-2 xl:grid-cols-3">
        <div className="grid gap-2">
          <Label htmlFor="bot-id" className="text-sm font-semibold">ID bot</Label>
          <Input
            id="bot-id"
            className="h-11 rounded-xl"
            value={bot.id}
            disabled={!isNew}
            onChange={(event) => patch('id', event.target.value)}
          />
        </div>

        <div className="grid gap-2">
          <Label htmlFor="bot-name" className="text-sm font-semibold">Nome bot</Label>
          <Input
            id="bot-name"
            className="h-11 rounded-xl"
            value={bot.name}
            onChange={(event) => patch('name', event.target.value)}
          />
        </div>

        <div className="grid gap-2">
          <Label htmlFor="company-name" className="text-sm font-semibold">Azienda</Label>
          <Input
            id="company-name"
            className="h-11 rounded-xl"
            value={bot.company_name}
            onChange={(event) => patch('company_name', event.target.value)}
          />
        </div>

        <div className="grid gap-2">
          <Label htmlFor="company-service-area" className="text-sm font-semibold">Area di servizio</Label>
          <Input
            id="company-service-area"
            className="h-11 rounded-xl"
            value={bot.service_area}
            onChange={(event) => patch('service_area', event.target.value)}
          />
        </div>

        <div className="grid gap-2">
          <Label htmlFor="agent-name" className="text-sm font-semibold">Nome agente</Label>
          <Input
            id="agent-name"
            className="h-11 rounded-xl"
            value={bot.agent_name}
            onChange={(event) => patch('agent_name', event.target.value)}
          />
        </div>

        <div className="grid gap-2">
          <Label htmlFor="booking-url" className="text-sm font-semibold">Booking URL</Label>
          <Input
            id="booking-url"
            className="h-11 rounded-xl"
            value={bot.booking_url}
            onChange={(event) => patch('booking_url', event.target.value)}
          />
        </div>

        <div className="grid gap-2 sm:col-span-2 xl:col-span-3">
          <Label htmlFor="company-description" className="text-sm font-semibold">Descrizione azienda</Label>
          <Textarea
            id="company-description"
            className="min-h-28 rounded-xl"
            value={bot.company_description}
            onChange={(event) => patch('company_description', event.target.value)}
          />
        </div>

        <div className="grid gap-2 sm:col-span-2 xl:col-span-3">
          <Label htmlFor="company-services" className="text-sm font-semibold">Servizi principali</Label>
          <Input
            id="company-services"
            className="h-11 rounded-xl"
            placeholder="Ristrutturazioni, Facciate, Tetti"
            value={listToCommaSeparated(bot.company_services)}
            onChange={(event) =>
              patch('company_services', commaSeparatedToList(event.target.value))
            }
          />
        </div>

        <div className="grid gap-2 sm:col-span-2 xl:col-span-3">
          <Label htmlFor="website-url" className="text-sm font-semibold">Sito aziendale</Label>
          <div className="flex flex-col gap-3 lg:flex-row">
            <Input
              id="website-url"
              className="h-11 rounded-xl"
              placeholder="https://www.example.com"
              value={bot.website_url}
              onChange={(event) => patch('website_url', event.target.value)}
            />
            <Button
              type="button"
              variant="outline"
              className="gap-2 rounded-xl lg:min-w-[12rem]"
              onClick={() => onCrawlSite(bot.website_url)}
              disabled={
                !cloudflareCrawlEnabled ||
                isNew ||
                isCrawlingSite ||
                !bot.website_url.trim()
              }
            >
              {isCrawlingSite ? 'Analisi in corso...' : 'Crawl + knowledge'}
            </Button>
          </div>
        </div>

        <div className="rounded-xl border border-border/60 bg-muted/20 px-4 py-3 text-sm text-muted-foreground sm:col-span-2 xl:col-span-3">
          <div className="font-semibold text-foreground">
            Sito + RAG
          </div>
          {!cloudflareCrawlEnabled ? (
            <p className="mt-2 text-amber-700">
              Configura Cloudflare.
            </p>
          ) : null}
          {isNew ? (
            <p className="mt-2">
              Salva prima.
            </p>
          ) : null}
          {crawlNotice ? (
            <p className="mt-2 text-primary">{crawlNotice}</p>
          ) : null}
          {crawlError ? (
            <p className="mt-2 text-destructive">{crawlError}</p>
          ) : null}
        </div>

        <div className="grid gap-2">
          <Label htmlFor="qualification-statuses" className="text-sm font-semibold">Stati</Label>
          <Input
            id="qualification-statuses"
            className="h-11 rounded-xl"
            placeholder="caldo, tiepido, freddo"
            value={listToCommaSeparated(bot.qualification_statuses)}
            onChange={(event) =>
              patch(
                'qualification_statuses',
                commaSeparatedToList(event.target.value),
              )
            }
          />
        </div>

        <div className="grid gap-2">
          <Label htmlFor="template-language-readonly" className="text-sm font-semibold">Lingua template attiva</Label>
          <Input
            id="template-language-readonly"
            className="h-11 rounded-xl"
            value={bot.template_language}
            onChange={(event) => patch('template_language', event.target.value)}
            readOnly
          />
        </div>

      </section>

      <FieldListEditor bot={bot} onChange={onChange} />
    </div>
  )
}
