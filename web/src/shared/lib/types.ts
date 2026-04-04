export type BotFieldConfig = {
  key: string
  label: string
  description: string
  required: boolean
  options: string[]
}

export type BotConfig = {
  id: string
  owner_user_id: string
  name: string
  company_name: string
  company_description: string
  service_area: string
  company_services: string[]
  website_url: string
  agent_name: string
  phone_number_id: string
  whatsapp_display_phone_number: string
  meta_business_id: string
  meta_business_name: string
  meta_waba_id: string
  meta_waba_name: string
  default_template_name: string
  default_template_variable_count: number
  template_language: string
  booking_url: string
  lead_manager_page_id: string
  lead_manager_page_name: string
  qualification_statuses: string[]
  fields: BotFieldConfig[]
}

export type DashboardAppConfig = {
  supabase_url: string
  supabase_publishable_key: string
  meta_oauth_enabled: boolean
  cloudflare_crawl_enabled: boolean
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

export type TemplateTestRequest = {
  to: string
  template_name?: string | null
  language_code?: string | null
  body_parameters: string[]
}

export type LeadSummary = {
  wa_id: string
  qualification_status: string
  summary: string
  message_count: number
  last_message_at: string
}

export type ChatMessage = {
  role: 'user' | 'assistant'
  display: string
}

export type LeadManagerPageOption = {
  id: string
  name: string
  is_active: string
  qualifier_bot_id: string
  qualifier_bot_name: string
}

export type MetaTemplateOption = {
  id: string
  name: string
  language: string
  status: string
  category: string
  body_variable_count: number
}

export type MetaPhoneNumberOption = {
  id: string
  display_phone_number: string
  verified_name: string
  name_status: string
}

export type MetaWabaOption = {
  id: string
  name: string
  business_id: string
  business_name: string
  phone_numbers: MetaPhoneNumberOption[]
  templates: MetaTemplateOption[]
}

export type MetaAssetsPayload = {
  connected: boolean
  profile: {
    id: string
    name: string
    token_expires_at: string
  } | null
  page_options: LeadManagerPageOption[]
  waba_options: MetaWabaOption[]
}

export type SiteCrawlRequest = {
  site_url: string
}
