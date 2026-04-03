import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import type { BotConfig, TemplateSendRequest } from '@/lib/types'

type SendTemplateCardProps = {
  bot: BotConfig
  pending: boolean
  notice: string
  error: string
  onSend: (payload: TemplateSendRequest) => Promise<void>
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
      bot_id: bot.id,
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
    <Card>
      <CardHeader>
        <CardTitle>Template</CardTitle>
      </CardHeader>

      <CardContent className="grid gap-4">
        <div className="grid gap-4 md:grid-cols-3">
          <div className="grid gap-2">
            <Label htmlFor="template-to">Numero lead</Label>
            <Input
              id="template-to"
              placeholder="393401234567"
              value={to}
              onChange={(event) => setTo(event.target.value)}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="template-name">Template</Label>
            <Input
              id="template-name"
              value={templateName}
              onChange={(event) => setTemplateName(event.target.value)}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="template-language">Lingua</Label>
            <Input
              id="template-language"
              value={languageCode}
              onChange={(event) => setLanguageCode(event.target.value)}
            />
          </div>
        </div>

        <div className="grid gap-2">
          <Label htmlFor="body-parameters">
            Parametri body, uno per riga
          </Label>
          <Textarea
            id="body-parameters"
            className="min-h-28"
            placeholder={'Impresa Demo\nMilano'}
            value={bodyParametersRaw}
            onChange={(event) => setBodyParametersRaw(event.target.value)}
          />
        </div>

        {notice ? (
          <div className="rounded-lg border bg-muted/30 px-3 py-2 text-sm">
            {notice}
          </div>
        ) : null}

        {error ? (
          <div className="rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 text-sm text-destructive">
            {error}
          </div>
        ) : null}

        <div className="flex justify-end">
          <Button
            onClick={submit}
            disabled={!to.trim() || !templateName.trim() || pending}
          >
            {pending ? 'Invio...' : 'Invia template'}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
