import type { BotConfig, BotFieldConfig } from '@/shared/lib/types'

const DEFAULT_STATUSES = ['new', 'in_progress', 'qualified', 'follow_up']

function createConstructionDefaults(): BotFieldConfig[] {
  return [
    {
      key: 'tipo_lavoro',
      label: 'Tipo di lavoro',
      description:
        'Tipo di intervento richiesto dal lead, ad esempio ristrutturazione, facciata, tetto, bagno o manutenzione.',
      required: true,
      options: [],
    },
    {
      key: 'zona_lavoro',
      label: 'Zona del lavoro',
      description:
        'Comune, quartiere, CAP o provincia in cui si trova il cantiere.',
      required: true,
      options: [],
    },
    {
      key: 'tempistica',
      label: 'Tempistica',
      description:
        'Quando il lead vuole eseguire il lavoro, con data, urgenza o finestra temporale.',
      required: true,
      options: [],
    },
    {
      key: 'immagini_situazione_attuale',
      label: 'Foto o immagini della situazione attuale',
      description:
        'Chiedi molto presto se il lead ha gia foto utili. Se non le ha, chiedi se puo scattarle e inviarle. Se non riesce, registra non disponibili e continua senza bloccare la qualifica.',
      required: true,
      options: ['ricevute', 'da inviare', 'non disponibili'],
    },
    {
      key: 'orario_preferito_richiamo',
      label: 'Ora preferita per il richiamo',
      description:
        'Orario o fascia oraria preferita dal lead per essere richiamato.',
      required: true,
      options: [],
    },
    {
      key: 'disponibilita_sopralluogo',
      label: 'Disponibilita per il sopralluogo',
      description:
        'Giorni o fasce orarie in cui il lead e disponibile per fissare il sopralluogo.',
      required: true,
      options: [],
    },
  ]
}

export function createEmptyField(): BotFieldConfig {
  const suffix = crypto.randomUUID().split('-')[0]
  return {
    key: `campo_${suffix}`,
    label: 'Nuovo campo',
    description: '',
    required: true,
    options: [],
  }
}

export function createEmptyBotConfig(): BotConfig {
  const suffix = crypto.randomUUID().split('-')[0]
  return {
    id: `bot_${suffix}`,
    owner_user_id: '',
    name: 'Nuovo bot',
    company_name: '',
    company_description: '',
    service_area: '',
    company_services: [],
    website_url: '',
    agent_name: 'Giulia',
    phone_number_id: '',
    whatsapp_display_phone_number: '',
    meta_business_id: '',
    meta_business_name: '',
    meta_waba_id: '',
    meta_waba_name: '',
    default_template_id: '',
    default_template_name: '',
    default_template_body_text: '',
    default_template_variable_count: 0,
    template_language: 'it',
    booking_url: '',
    lead_manager_page_id: '',
    lead_manager_page_name: '',
    qualification_statuses: [...DEFAULT_STATUSES],
    fields: createConstructionDefaults(),
  }
}

export function cloneBotConfig(bot: BotConfig): BotConfig {
  return {
    ...bot,
    company_services: [...bot.company_services],
    qualification_statuses: [...bot.qualification_statuses],
    fields: bot.fields.map((field) => ({
      ...field,
      options: [...field.options],
    })),
  }
}

export function commaSeparatedToList(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

export function listToCommaSeparated(values: string[]): string {
  return values.join(', ')
}
