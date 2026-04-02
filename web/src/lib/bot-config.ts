import type { BotConfig, BotFieldConfig } from '@/lib/types'

const DEFAULT_STATUSES = ['new', 'in_progress', 'qualified', 'follow_up']

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
    agent_name: 'Giulia',
    phone_number_id: '',
    default_template_name: '',
    template_language: 'it',
    booking_url: '',
    prompt_preamble: '',
    qualification_statuses: [...DEFAULT_STATUSES],
    fields: [createEmptyField()],
  }
}

export function cloneBotConfig(bot: BotConfig): BotConfig {
  return {
    ...bot,
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
