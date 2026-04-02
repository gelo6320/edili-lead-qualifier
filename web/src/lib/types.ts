export type BotFieldConfig = {
  key: string
  label: string
  description: string
  required: boolean
  options: string[]
}

export type BotConfig = {
  id: string
  name: string
  company_name: string
  agent_name: string
  phone_number_id: string
  default_template_name: string
  template_language: string
  booking_url: string
  prompt_preamble: string
  qualification_statuses: string[]
  fields: BotFieldConfig[]
}

export type DashboardAppConfig = {
  supabase_url: string
  supabase_publishable_key: string
}

export type DashboardUser = {
  id: string
  email: string
}

export type DashboardSessionPayload = {
  user: DashboardUser
}

export type TemplateSendRequest = {
  bot_id: string
  to: string
  template_name: string
  language_code?: string | null
  body_parameters: string[]
}
