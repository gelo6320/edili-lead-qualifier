import { useEffect, useState } from 'react'
import { Send } from 'lucide-react'

import type { BotConfig, TemplateTestRequest } from '@/shared/lib/types'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Label } from '@/shared/ui/label'
import { Textarea } from '@/shared/ui/textarea'

type SendTemplateCardProps = {
  bot: BotConfig
  pending: boolean
  notice: string
  error: string
  onSend: (payload: TemplateTestRequest) => Promise<void>
}

export function SendTemplateCard({
  bot,
  error,
  notice,
  onSend,
  pending,
}: SendTemplateCardProps) {
  const [to, setTo] = useState('')
  const [templateName, setTemplateName] = useState(bot.default_template_name)
  const [languageCode, setLanguageCode] = useState(bot.template_language)
  const [bodyParametersRaw, setBodyParametersRaw] = useState('')

  useEffect(() => {
    setTemplateName(bot.default_template_name)
    setLanguageCode(bot.template_language)
  }, [bot.default_template_name, bot.template_language, bot.id])

  async function submit() {
    await onSend({
      to: to.trim(),
      template_name: templateName.trim(),
      language_code: languageCode.trim() || null,
      body_parameters: bodyParametersRaw
        .split('\n')
        .map((item) => item.trim())
        .filter(Boolean),
    })
  }

  return (
    <section className="grid gap-5 rounded-xl border border-border/60 bg-card p-4 shadow-sm">
      <div className="grid gap-4 md:grid-cols-3">
        <div className="grid gap-2">
          <Label htmlFor="template-to" className="text-sm font-semibold">Numero lead</Label>
          <Input
            id="template-to"
            className="h-11 rounded-xl font-mono text-xs"
            placeholder="393401234567"
            value={to}
            onChange={(event) => setTo(event.target.value)}
          />
        </div>

        <div className="grid gap-2">
          <Label htmlFor="template-name" className="text-sm font-semibold">Template</Label>
          <Input
            id="template-name"
            className="h-11 rounded-xl"
            value={templateName}
            onChange={(event) => setTemplateName(event.target.value)}
          />
        </div>

        <div className="grid gap-2">
          <Label htmlFor="template-language" className="text-sm font-semibold">Lingua</Label>
          <Input
            id="template-language"
            className="h-11 rounded-xl"
            value={languageCode}
            onChange={(event) => setLanguageCode(event.target.value)}
          />
        </div>
      </div>

      <div className="grid gap-2">
        <Label htmlFor="body-parameters" className="text-sm font-semibold">
          Parametri body
        </Label>
        <Textarea
          id="body-parameters"
          className="min-h-28 rounded-xl"
          placeholder={'Impresa Demo\nMilano'}
          value={bodyParametersRaw}
          onChange={(event) => setBodyParametersRaw(event.target.value)}
        />
      </div>

      {notice ? (
        <div className="flex items-center gap-2 rounded-xl border border-primary/20 bg-primary/5 px-4 py-3 text-sm font-medium text-primary">
          <svg className="h-4 w-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
          {notice}
        </div>
      ) : null}

      <div className="rounded-xl border border-border/60 bg-muted/20 px-4 py-3 text-sm text-muted-foreground">
        L'invio del template crea subito la conversazione e inizializza il contesto agente per quel numero.
      </div>

      {error ? (
        <div className="rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      ) : null}

      <div className="flex justify-end">
        <Button
          className="gap-2 rounded-xl shadow-sm shadow-primary/20"
          onClick={submit}
          disabled={!to.trim() || !templateName.trim() || pending}
        >
          <Send className="h-3.5 w-3.5" />
          {pending ? 'Invio...' : 'Invia test'}
        </Button>
      </div>
    </section>
  )
}
