import { Save, Trash2 } from 'lucide-react'

import { FieldListEditor } from '@/components/field-list-editor'
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
import {
  commaSeparatedToList,
  listToCommaSeparated,
} from '@/lib/bot-config'
import type { BotConfig } from '@/lib/types'

type BotEditorProps = {
  bot: BotConfig
  isNew: boolean
  isSaving: boolean
  isDeleting: boolean
  editorNotice: string
  editorError: string
  onChange: (bot: BotConfig) => void
  onSave: () => void
  onDelete: () => void
}

export function BotEditor({
  bot,
  editorError,
  editorNotice,
  isDeleting,
  isNew,
  isSaving,
  onChange,
  onDelete,
  onSave,
}: BotEditorProps) {
  function patch<K extends keyof BotConfig>(key: K, value: BotConfig[K]) {
    onChange({ ...bot, [key]: value })
  }

  return (
    <div className="grid gap-6">
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <CardTitle>{isNew ? 'Nuovo bot' : 'Configurazione'}</CardTitle>
            <div className="flex gap-2">
              {!isNew ? (
                <Button
                  variant="destructive"
                  onClick={onDelete}
                  disabled={isDeleting}
                >
                  <Trash2 />
                  {isDeleting ? 'Eliminazione...' : 'Elimina'}
                </Button>
              ) : null}

              <Button onClick={onSave} disabled={isSaving}>
                <Save />
                {isSaving ? 'Salvataggio...' : 'Salva'}
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent className="grid gap-6">
          {editorNotice ? (
            <div className="rounded-lg border bg-muted/30 px-3 py-2 text-sm">
              {editorNotice}
            </div>
          ) : null}

          {editorError ? (
            <div className="rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              {editorError}
            </div>
          ) : null}

          <div className="grid gap-4 md:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="bot-id">ID bot</Label>
              <Input
                id="bot-id"
                value={bot.id}
                disabled={!isNew}
                onChange={(event) => patch('id', event.target.value)}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="bot-name">Nome bot</Label>
              <Input
                id="bot-name"
                value={bot.name}
                onChange={(event) => patch('name', event.target.value)}
              />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="company-name">Azienda</Label>
              <Input
                id="company-name"
                value={bot.company_name}
                onChange={(event) => patch('company_name', event.target.value)}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="agent-name">Nome agente</Label>
              <Input
                id="agent-name"
                value={bot.agent_name}
                onChange={(event) => patch('agent_name', event.target.value)}
              />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="phone-number-id">Meta phone_number_id</Label>
              <Input
                id="phone-number-id"
                value={bot.phone_number_id}
                onChange={(event) =>
                  patch('phone_number_id', event.target.value)
                }
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="booking-url">Booking URL</Label>
              <Input
                id="booking-url"
                value={bot.booking_url}
                onChange={(event) => patch('booking_url', event.target.value)}
              />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="default-template-name">Template outbound di default</Label>
              <Input
                id="default-template-name"
                value={bot.default_template_name}
                onChange={(event) =>
                  patch('default_template_name', event.target.value)
                }
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="template-language">Lingua template</Label>
              <Input
                id="template-language"
                value={bot.template_language}
                onChange={(event) =>
                  patch('template_language', event.target.value)
                }
              />
            </div>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="qualification-statuses">Stati di qualifica</Label>
            <Input
              id="qualification-statuses"
              value={listToCommaSeparated(bot.qualification_statuses)}
              onChange={(event) =>
                patch(
                  'qualification_statuses',
                  commaSeparatedToList(event.target.value),
                )
              }
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="prompt-preamble">Prompt</Label>
            <Textarea
              id="prompt-preamble"
              className="min-h-36"
              value={bot.prompt_preamble}
              onChange={(event) => patch('prompt_preamble', event.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      <FieldListEditor bot={bot} onChange={onChange} />
    </div>
  )
}
