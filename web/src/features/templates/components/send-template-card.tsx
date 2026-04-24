import { useEffect, useState } from 'react'
import { Check } from 'lucide-react'
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
  const [templateValues, setTemplateValues] = useState<string[]>([])
  const [bodyParametersRaw, setBodyParametersRaw] = useState('')
  const expectedBodyParameterCount = Math.max(bot.default_template_variable_count ?? 0, 0)
  const isDefaultTemplateSelected =
    bot.default_template_name.trim().length > 0 &&
    templateName.trim() === bot.default_template_name.trim()
  const hasStructuredTemplateValues =
    isDefaultTemplateSelected && expectedBodyParameterCount > 0
  const normalizedTemplateValues = templateValues.map((value) => value.trim())
  const hasMissingTemplateValue =
    hasStructuredTemplateValues &&
    normalizedTemplateValues.length === expectedBodyParameterCount &&
    normalizedTemplateValues.some((value) => !value)

  useEffect(() => {
    setTemplateName(bot.default_template_name)
    setLanguageCode(bot.template_language)
    setTemplateValues(
      Array.from(
        { length: Math.max(bot.default_template_variable_count ?? 0, 0) },
        () => '',
      ),
    )
    setBodyParametersRaw('')
  }, [bot.default_template_name, bot.template_language, bot.id])

  useEffect(() => {
    if (!isDefaultTemplateSelected) return
    setTemplateValues((current) =>
      Array.from({ length: expectedBodyParameterCount }, (_, index) => current[index] ?? ''),
    )
  }, [expectedBodyParameterCount, isDefaultTemplateSelected])

  function patchTemplateValue(index: number, value: string) {
    setTemplateValues((current) =>
      current.map((item, currentIndex) => (currentIndex === index ? value : item)),
    )
  }

  async function submit() {
    await onSend({
      to: to.trim(),
      template_name: templateName.trim(),
      language_code: languageCode.trim() || null,
      body_parameters: hasStructuredTemplateValues
        ? normalizedTemplateValues.filter(Boolean)
        : bodyParametersRaw
            .split('\n')
            .map((item) => item.trim())
            .filter(Boolean),
    })
  }

  return (
    <section className="rounded-md border border-border bg-card">
      <header className="border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold leading-tight">Invio test template</h2>
        <p className="mt-0.5 text-xs text-muted-foreground">
          Invia un template WhatsApp a un numero per verificare la configurazione.
        </p>
      </header>

      <div className="grid gap-4 p-4">
        <div className="grid gap-3 md:grid-cols-3">
          <div className="grid gap-1.5">
            <Label htmlFor="template-to" className="text-xs font-medium text-muted-foreground">
              Numero lead
            </Label>
            <Input
              id="template-to"
              className="h-9 rounded-md font-mono text-xs"
              placeholder="393401234567"
              value={to}
              onChange={(event) => setTo(event.target.value)}
            />
          </div>

          <div className="grid gap-1.5">
            <Label htmlFor="template-name" className="text-xs font-medium text-muted-foreground">
              Template
            </Label>
            <Input
              id="template-name"
              className="h-9 rounded-md"
              value={templateName}
              onChange={(event) => setTemplateName(event.target.value)}
            />
          </div>

          <div className="grid gap-1.5">
            <Label
              htmlFor="template-language"
              className="text-xs font-medium text-muted-foreground"
            >
              Lingua
            </Label>
            <Input
              id="template-language"
              className="h-9 rounded-md"
              value={languageCode}
              onChange={(event) => setLanguageCode(event.target.value)}
            />
          </div>
        </div>

        {isDefaultTemplateSelected ? (
          expectedBodyParameterCount > 0 ? (
            <div className="grid gap-2">
              <div>
                <Label className="text-xs font-medium text-muted-foreground">
                  Valori del messaggio
                </Label>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  Compila i valori inseriti nel testo del template.
                </p>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                {templateValues.map((value, index) => (
                  <div key={`${bot.id}-template-value-${index}`} className="grid gap-1.5">
                    <Label
                      htmlFor={`template-value-${index}`}
                      className="text-xs font-medium text-muted-foreground"
                    >
                      Valore {index + 1}
                    </Label>
                    <Input
                      id={`template-value-${index}`}
                      className="h-9 rounded-md"
                      placeholder={`Valore ${index + 1}`}
                      value={value}
                      onChange={(event) => patchTemplateValue(index, event.target.value)}
                    />
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="rounded-md bg-muted/50 px-3 py-2 text-xs text-muted-foreground">
              Questo template non richiede valori da inserire.
            </p>
          )
        ) : (
          <div className="grid gap-1.5">
            <Label
              htmlFor="body-parameters"
              className="text-xs font-medium text-muted-foreground"
            >
              Valori del template
            </Label>
            <p className="text-xs text-muted-foreground">Una riga per ogni variabile.</p>
            <Textarea
              id="body-parameters"
              className="min-h-24 rounded-md"
              placeholder={'Valore 1\nValore 2'}
              value={bodyParametersRaw}
              onChange={(event) => setBodyParametersRaw(event.target.value)}
            />
          </div>
        )}

        {notice ? (
          <div className="inline-flex items-center gap-1.5 rounded-md bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary">
            <Check className="h-3.5 w-3.5" />
            {notice}
          </div>
        ) : null}

        {error ? (
          <div className="rounded-md bg-destructive/10 px-2.5 py-1 text-xs font-medium text-destructive">
            {error}
          </div>
        ) : null}

        <div className="flex justify-end">
          <Button
            size="sm"
            onClick={submit}
            disabled={
              !to.trim() || !templateName.trim() || pending || hasMissingTemplateValue
            }
          >
            {pending ? 'Invio...' : 'Invia test'}
          </Button>
        </div>
      </div>
    </section>
  )
}
