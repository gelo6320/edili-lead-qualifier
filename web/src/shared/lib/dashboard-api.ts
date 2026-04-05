import type {
  BotConfig,
  ChatMessage,
  DashboardAppConfig,
  DashboardSessionPayload,
  LeadSummary,
  MetaAssetsPayload,
  SiteCrawlRequest,
  TemplateSendRequest,
  TemplateTestRequest,
} from '@/shared/lib/types'

export class DashboardApiError extends Error {
  readonly status: number
  readonly detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.status = status
    this.detail = detail
  }
}

async function parseJson<T>(response: Response): Promise<T> {
  const text = await response.text()
  const payload = text ? JSON.parse(text) : {}

  if (!response.ok) {
    const detail =
      typeof payload?.detail === 'string'
        ? payload.detail
        : `HTTP ${response.status}`
    throw new DashboardApiError(response.status, detail)
  }

  return payload as T
}

async function dashboardFetch<T>(
  path: string,
  init?: RequestInit,
  token?: string,
): Promise<T> {
  const headers = new Headers(init?.headers ?? {})
  if (!headers.has('Content-Type') && init?.body) {
    headers.set('Content-Type', 'application/json')
  }
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(path, {
    ...init,
    headers,
  })
  return parseJson<T>(response)
}

export function getDashboardAppConfig() {
  return dashboardFetch<DashboardAppConfig>('/api/dashboard/app-config')
}

export function getDashboardSession(token: string) {
  return dashboardFetch<DashboardSessionPayload>(
    '/api/dashboard/session',
    undefined,
    token,
  )
}

export function listBots(token: string) {
  return dashboardFetch<BotConfig[]>('/api/dashboard/bots', undefined, token)
}

export function createBot(token: string, payload: BotConfig) {
  return dashboardFetch<BotConfig>(
    '/api/dashboard/bots',
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    token,
  )
}

export function updateBot(token: string, payload: BotConfig) {
  return dashboardFetch<BotConfig>(
    `/api/dashboard/bots/${payload.id}`,
    {
      method: 'PUT',
      body: JSON.stringify(payload),
    },
    token,
  )
}

export function deleteBot(token: string, botId: string) {
  return dashboardFetch<{ status: string; bot_id: string }>(
    `/api/dashboard/bots/${botId}`,
    {
      method: 'DELETE',
    },
    token,
  )
}

export function sendTemplate(token: string, payload: TemplateSendRequest) {
  return dashboardFetch<{ status: string }>(
    '/api/dashboard/send-template',
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    token,
  )
}

export function sendTestTemplate(
  token: string,
  botId: string,
  payload: TemplateTestRequest,
) {
  return dashboardFetch<{ status: string }>(
    `/api/dashboard/bots/${botId}/test-template`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    token,
  )
}

export function listLeads(token: string, botId: string) {
  return dashboardFetch<LeadSummary[]>(
    `/api/dashboard/bots/${botId}/leads`,
    undefined,
    token,
  )
}

export function listLeadMessages(token: string, botId: string, waId: string) {
  return dashboardFetch<ChatMessage[]>(
    `/api/dashboard/bots/${botId}/leads/${waId}/messages`,
    undefined,
    token,
  )
}

export function deleteLeadConversation(token: string, botId: string, waId: string) {
  return dashboardFetch<{ status: string; bot_id: string; wa_id: string }>(
    `/api/dashboard/bots/${botId}/leads/${waId}`,
    {
      method: 'DELETE',
    },
    token,
  )
}

export function startMetaOAuth(token: string) {
  return dashboardFetch<{ authorize_url: string }>(
    '/api/dashboard/meta/oauth/start',
    undefined,
    token,
  )
}

export function getMetaAssets(token: string) {
  return dashboardFetch<MetaAssetsPayload>(
    '/api/dashboard/meta/assets',
    undefined,
    token,
  )
}

export function crawlSite(
  token: string,
  botId: string,
  payload: SiteCrawlRequest,
) {
  return dashboardFetch<{
    bot: BotConfig
    pages_crawled: number
    chunks_stored: number
    summary: {
      company_description: string
      service_area: string
      company_services: string[]
    }
  }>(
    `/api/dashboard/bots/${botId}/crawl-site`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    token,
  )
}
