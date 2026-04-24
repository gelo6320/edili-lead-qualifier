import { useEffect, useMemo } from 'react'
import { Check } from 'lucide-react'
import { FieldListEditor } from '@/features/bots/components/field-list-editor'
import {
  commaSeparatedToList,
  listToCommaSeparated,
} from '@/shared/lib/bot-config'
import type {
  BotConfig,
  MetaAssetsPayload,
  MetaWabaOption,
} from '@/shared/lib/types'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Label } from '@/shared/ui/label'
import { Textarea } from '@/shared/ui/textarea'

const SELECT_CLASS_NAME =
  'h-9 w-full cursor-pointer appearance-none rounded-md border border-border bg-background px-2.5 pr-8 text-sm transition-colors hover:border-foreground/30 focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30 disabled:cursor-not-allowed disabled:opacity-60'

const INPUT_CLASS_NAME = 'h-9 rounded-md'

const DATE_TIME_FORMATTER = new Intl.DateTimeFormat('it-IT', {
  dateStyle: 'medium',
  timeStyle: 'short',
})
const EMPTY_PHONE_OPTIONS: MetaWabaOption['phone_numbers'] = []
const EMPTY_TEMPLATE_OPTIONS: MetaWabaOption['templates'] = []

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

  return DATE_TIME_FORMATTER.format(date)
}

function getSelectedWaba(
  metaWabaId: string,
  metaAssets: MetaAssetsPayload,
): MetaWabaOption | null {
  return metaAssets.waba_options.find((item) => item.id === metaWabaId) ?? null
}

function matchTemplate(
  defaultTemplateId: string,
  defaultTemplateName: string,
  templateLanguage: string,
  templateOptions: MetaWabaOption['templates'],
) {
  if (defaultTemplateId.trim()) {
    const byId = templateOptions.find((item) => item.id === defaultTemplateId)
    if (byId) {
      return byId
    }
  }

  const templateName = defaultTemplateName.trim()
  if (!templateName) {
    return null
  }

  const normalizedTemplateLanguage = templateLanguage.trim().toLowerCase()
  const byNameAndLanguage = templateOptions.find(
    (item) =>
      item.name === templateName &&
      item.language.trim().toLowerCase() === normalizedTemplateLanguage,
  )
  if (byNameAndLanguage) {
    return byNameAndLanguage
  }

  return templateOptions.find((item) => item.name === templateName) ?? null
}

type SectionProps = {
  title: string
  description?: string
  action?: React.ReactNode
  children: React.ReactNode
}

function Section({ title, description, action, children }: SectionProps) {
  return (
    <section className="rounded-md border border-border bg-card [content-visibility:auto] [contain-intrinsic-size:220px]">
      <header className="flex items-start justify-between gap-3 border-b border-border px-4 py-3">
        <div className="min-w-0">
          <h2 className="text-sm font-semibold leading-tight">{title}</h2>
          {description ? (
            <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>
          ) : null}
        </div>
        {action ? <div className="flex-shrink-0">{action}</div> : null}
      </header>
      <div className="p-4">{children}</div>
    </section>
  )
}

type FieldProps = {
  id: string
  label: string
  children: React.ReactNode
  className?: string
}

function Field({ id, label, children, className }: FieldProps) {
  return (
    <div className={`grid gap-1.5 ${className ?? ''}`}>
      <Label htmlFor={id} className="text-xs font-medium text-muted-foreground">
        {label}
      </Label>
      {children}
    </div>
  )
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
  const selectedWaba = useMemo(
    () => getSelectedWaba(bot.meta_waba_id, metaAssets),
    [bot.meta_waba_id, metaAssets],
  )
  const phoneOptions = selectedWaba?.phone_numbers ?? EMPTY_PHONE_OPTIONS
  const templateOptions = selectedWaba?.templates ?? EMPTY_TEMPLATE_OPTIONS
  const selectedTemplate = useMemo(
    () =>
      matchTemplate(
        bot.default_template_id,
        bot.default_template_name,
        bot.template_language,
        templateOptions,
      ),
    [
      bot.default_template_id,
      bot.default_template_name,
      bot.template_language,
      templateOptions,
    ],
  )
  const selectedTemplateBody = selectedTemplate?.body_text || bot.default_template_body_text

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
      onChange({ ...bot, ...nextPatch })
    }
  }, [bot, onChange, selectedTemplate])

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
    const nextTemplate = matchTemplate(
      bot.default_template_id,
      bot.default_template_name,
      bot.template_language,
      nextWaba.templates,
    )

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
    const nextPhone = phoneOptions.find((item) => item.id === phoneNumberId) ?? null
    patchMany({
      phone_number_id: nextPhone?.id ?? '',
      whatsapp_display_phone_number: nextPhone?.display_phone_number ?? '',
    })
  }

  function handleTemplateChange(templateId: string) {
    const nextTemplate = templateOptions.find((item) => item.id === templateId) ?? null
    patchMany({
      default_template_id: nextTemplate?.id ?? '',
      default_template_name: nextTemplate?.name ?? '',
      default_template_body_text: nextTemplate?.body_text ?? '',
      default_template_variable_count: nextTemplate?.body_variable_count ?? 0,
      template_language: nextTemplate?.language ?? 'it',
    })
  }

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
          {editorNotice ? (
            <div className="inline-flex items-center gap-1.5 rounded-md bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary">
              <Check className="h-3.5 w-3.5" />
              {editorNotice}
            </div>
          ) : null}
          {editorError ? (
            <div className="rounded-md bg-destructive/10 px-2.5 py-1 text-xs font-medium text-destructive">
              {editorError}
            </div>
          ) : null}
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {!isNew ? (
            <Button
              variant="destructive"
              size="sm"
              onClick={onDelete}
              disabled={isDeleting}
              type="button"
            >
              {isDeleting ? 'Eliminazione...' : 'Elimina'}
            </Button>
          ) : null}
          <Button onClick={onSave} disabled={isSaving} size="sm" type="button">
            {isSaving ? 'Salvataggio...' : 'Salva'}
          </Button>
        </div>
      </div>

      <Section
        title="Connessione Meta"
        description="Collega il WABA e il routing dei lead qualificati."
        action={
          <Badge variant={metaAssets.connected ? 'default' : 'outline'}>
            {metaAssets.connected ? 'Collegato' : 'Non collegato'}
          </Badge>
        }
      >
        <div className="grid gap-4">
          <div className="flex flex-wrap gap-2">
            {metaOauthEnabled ? (
              <Button
                type="button"
                variant={metaAssets.connected ? 'outline' : 'default'}
                size="sm"
                onClick={onConnectMeta}
                disabled={isConnectingMeta}
              >
                {isConnectingMeta
                  ? 'Reindirizzamento...'
                  : metaAssets.connected
                    ? 'Ricollega'
                    : 'Collega Facebook'}
              </Button>
            ) : null}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onReloadMetaAssets}
              disabled={isLoadingMetaAssets}
            >
              {isLoadingMetaAssets ? 'Aggiornamento...' : 'Ricarica asset'}
            </Button>
          </div>

          {!metaOauthEnabled ? (
            <p className="rounded-md bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-400">
              Configura <code className="font-mono">META_APP_ID</code>,{' '}
              <code className="font-mono">META_APP_SECRET</code>,{' '}
              <code className="font-mono">APP_BASE_URL</code>,{' '}
              <code className="font-mono">OAUTH_STATE_SECRET</code> sul backend.
            </p>
          ) : null}

          {metaAssets.profile ? (
            <p className="text-xs text-muted-foreground">
              <span className="font-medium text-foreground">{metaAssets.profile.name}</span>{' '}
              · {formatDateTime(metaAssets.profile.token_expires_at)}
            </p>
          ) : null}

          {metaAssetsError ? (
            <p className="rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive">
              {metaAssetsError}
            </p>
          ) : null}

          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            <Field id="meta-waba" label="Account WhatsApp Business">
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
                    {waba.name} · {waba.business_name}
                  </option>
                ))}
              </select>
            </Field>

            <Field id="meta-phone-number" label="Numero invio WhatsApp">
              <select
                id="meta-phone-number"
                className={SELECT_CLASS_NAME}
                value={bot.phone_number_id}
                onChange={(event) => handlePhoneNumberChange(event.target.value)}
                disabled={!selectedWaba}
              >
                <option value="">{selectedWaba ? 'Seleziona numero' : 'Seleziona WABA'}</option>
                {phoneOptions.map((phone) => (
                  <option key={phone.id} value={phone.id}>
                    {phone.display_phone_number || phone.id}
                    {phone.verified_name ? ` · ${phone.verified_name}` : ''}
                  </option>
                ))}
              </select>
            </Field>

            <Field id="meta-template" label="Template iniziale">
              <select
                id="meta-template"
                className={SELECT_CLASS_NAME}
                value={selectedTemplate?.id ?? bot.default_template_id}
                onChange={(event) => handleTemplateChange(event.target.value)}
                disabled={!selectedWaba}
              >
                <option value="">{selectedWaba ? 'Seleziona template' : 'Seleziona WABA'}</option>
                {templateOptions.map((template) => (
                  <option
                    key={template.id || `${template.name}-${template.language}`}
                    value={template.id}
                  >
                    {template.name} · {template.language}
                  </option>
                ))}
              </select>
            </Field>

            <Field id="ghl-location-id" label="GHL location ID">
              <Input
                id="ghl-location-id"
                className={INPUT_CLASS_NAME}
                value={bot.ghl_location_id}
                onChange={(event) => patch('ghl_location_id', event.target.value)}
                placeholder="es. abc123location"
              />
            </Field>

            <Field
              id="qualified-lead-webhook-url"
              label="Webhook lead qualificato"
              className="md:col-span-2"
            >
              <Input
                id="qualified-lead-webhook-url"
                className={INPUT_CLASS_NAME}
                value={bot.qualified_lead_webhook_url}
                onChange={(event) => patch('qualified_lead_webhook_url', event.target.value)}
                placeholder="https://services.leadconnectorhq.com/..."
              />
            </Field>
          </div>

          {selectedTemplateBody ? (
            <div className="rounded-md bg-muted/50 px-3 py-2.5 text-xs">
              <div className="mb-1 font-medium">Contenuto template</div>
              <p className="whitespace-pre-wrap text-muted-foreground">{selectedTemplateBody}</p>
            </div>
          ) : null}
        </div>
      </Section>

      <Section title="Identità bot">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <Field id="bot-id" label="ID bot">
            <Input
              id="bot-id"
              className={INPUT_CLASS_NAME}
              value={bot.id}
              disabled={!isNew}
              onChange={(event) => patch('id', event.target.value)}
            />
          </Field>
          <Field id="bot-name" label="Nome bot">
            <Input
              id="bot-name"
              className={INPUT_CLASS_NAME}
              value={bot.name}
              onChange={(event) => patch('name', event.target.value)}
            />
          </Field>
          <Field id="agent-name" label="Nome agente">
            <Input
              id="agent-name"
              className={INPUT_CLASS_NAME}
              value={bot.agent_name}
              onChange={(event) => patch('agent_name', event.target.value)}
            />
          </Field>
        </div>
      </Section>

      <Section title="Azienda">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <Field id="company-name" label="Nome azienda">
            <Input
              id="company-name"
              className={INPUT_CLASS_NAME}
              value={bot.company_name}
              onChange={(event) => patch('company_name', event.target.value)}
            />
          </Field>
          <Field id="company-service-area" label="Area di servizio">
            <Input
              id="company-service-area"
              className={INPUT_CLASS_NAME}
              value={bot.service_area}
              onChange={(event) => patch('service_area', event.target.value)}
            />
          </Field>
          <Field id="company-services" label="Servizi principali">
            <Input
              id="company-services"
              className={INPUT_CLASS_NAME}
              placeholder="Ristrutturazioni, Facciate, Tetti"
              value={listToCommaSeparated(bot.company_services)}
              onChange={(event) =>
                patch('company_services', commaSeparatedToList(event.target.value))
              }
            />
          </Field>
          <Field
            id="company-description"
            label="Descrizione azienda"
            className="sm:col-span-2 xl:col-span-3"
          >
            <Textarea
              id="company-description"
              className="min-h-24 rounded-md"
              value={bot.company_description}
              onChange={(event) => patch('company_description', event.target.value)}
            />
          </Field>
        </div>
      </Section>

      <Section
        title="Sito web e knowledge base"
        description="Crawla le pagine del sito per alimentare il contesto dell'agente."
      >
        <div className="grid gap-3">
          <Field id="website-url" label="Sito aziendale">
            <div className="flex flex-col gap-2 sm:flex-row">
              <Input
                id="website-url"
                className={INPUT_CLASS_NAME}
                placeholder="https://www.example.com"
                value={bot.website_url}
                onChange={(event) => patch('website_url', event.target.value)}
              />
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-9 sm:min-w-[10rem]"
                onClick={() => onCrawlSite(bot.website_url)}
                disabled={
                  !cloudflareCrawlEnabled ||
                  isNew ||
                  isCrawlingSite ||
                  !bot.website_url.trim()
                }
              >
                {isCrawlingSite ? 'Analisi...' : 'Crawl + knowledge'}
              </Button>
            </div>
          </Field>

          {!cloudflareCrawlEnabled ? (
            <p className="text-xs text-amber-700 dark:text-amber-400">Configura Cloudflare.</p>
          ) : null}
          {isNew ? <p className="text-xs text-muted-foreground">Salva prima.</p> : null}
          {crawlNotice ? <p className="text-xs text-primary">{crawlNotice}</p> : null}
          {crawlError ? <p className="text-xs text-destructive">{crawlError}</p> : null}
        </div>
      </Section>

      <Section title="Qualificazione e prenotazione">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <Field id="qualification-statuses" label="Stati qualificazione">
            <Input
              id="qualification-statuses"
              className={INPUT_CLASS_NAME}
              placeholder="caldo, tiepido, freddo"
              value={listToCommaSeparated(bot.qualification_statuses)}
              onChange={(event) =>
                patch('qualification_statuses', commaSeparatedToList(event.target.value))
              }
            />
          </Field>
          <Field id="booking-url" label="Booking URL">
            <Input
              id="booking-url"
              className={INPUT_CLASS_NAME}
              value={bot.booking_url}
              onChange={(event) => patch('booking_url', event.target.value)}
            />
          </Field>
          <Field id="template-language-readonly" label="Lingua template attiva">
            <Input
              id="template-language-readonly"
              className={INPUT_CLASS_NAME}
              value={bot.template_language}
              onChange={(event) => patch('template_language', event.target.value)}
              readOnly
            />
          </Field>
        </div>
      </Section>

      <FieldListEditor bot={bot} onChange={onChange} />
    </div>
  )
}
