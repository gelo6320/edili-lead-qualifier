import type { BotConfig, BotFieldConfig } from '@/shared/lib/types'

const DEFAULT_STATUSES = ['new', 'in_progress', 'qualified', 'follow_up']

function createConstructionDefaults(): BotFieldConfig[] {
  return [
    {
      key: 'zona_lavoro',
      label: 'Zona del lavoro',
      description:
        'Comune, quartiere, CAP o provincia in cui si trova il cantiere.',
      required: true,
      options: [],
    },
    {
      key: 'tipo_lavoro',
      label: 'Tipo di lavoro richiesto',
      description:
        'Tipo di intervento richiesto dal lead, ad esempio ristrutturazione, cappotto, tetto, bagno, facciata o impianti.',
      required: true,
      options: [],
    },
    {
      key: 'immagini_situazione_attuale',
      label: 'Foto o immagini della situazione attuale',
      description:
        'Richiedi foto o immagini utili per capire la situazione attuale e valutare il lavoro. Se arrivano, registra che sono state ricevute.',
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
      key: 'budget_indicativo',
      label: 'Budget indicativo',
      description: 'Budget o fascia di spesa indicativa, anche approssimativa.',
      required: true,
      options: [],
    },
    {
      key: 'disponibile_chiamata',
      label: 'Disponibilita alla chiamata',
      description:
        'Disponibilita del lead a fissare una chiamata per approfondire e organizzare il sopralluogo.',
      required: true,
      options: ['si', 'no', 'forse'],
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
    name: 'Nuovo bot',
    company_name: '',
    company_description: '',
    service_area: '',
    company_services: [],
    agent_name: 'Giulia',
    phone_number_id: '',
    default_template_name: '',
    template_language: 'it',
    booking_url: '',
    lead_manager_page_id: '',
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
