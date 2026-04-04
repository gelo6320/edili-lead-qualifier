import { Save, Trash2 } from 'lucide-react'

import { FieldListEditor } from '@/components/field-list-editor'
import { Button } from '@/components/ui/button'
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
      <div className="flex flex-col gap-3 rounded-xl border border-border/60 bg-card p-3 shadow-sm md:flex-row md:items-center md:justify-between">
        <div className="flex min-w-0 flex-1 flex-col gap-2">
          {editorNotice ? (
            <div className="flex items-center gap-2 rounded-xl border border-primary/20 bg-primary/5 px-3 py-2 text-sm font-medium text-primary">
              <svg className="h-4 w-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              {editorNotice}
            </div>
          ) : null}

          {editorError ? (
            <div className="rounded-xl border border-destructive/20 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              {editorError}
            </div>
          ) : null}
        </div>

        <div className="flex shrink-0 gap-2">
          {!isNew ? (
            <Button
              variant="destructive"
              className="gap-1.5 rounded-xl"
              onClick={onDelete}
              disabled={isDeleting}
            >
              <Trash2 className="h-3.5 w-3.5" />
              {isDeleting ? 'Eliminazione...' : 'Elimina'}
            </Button>
          ) : null}

          <Button
            onClick={onSave}
            disabled={isSaving}
            className="gap-1.5 rounded-xl shadow-sm shadow-primary/20"
          >
            <Save className="h-3.5 w-3.5" />
            {isSaving ? 'Salvataggio...' : 'Salva'}
          </Button>
        </div>
      </div>

      <section className="grid gap-4 rounded-xl border border-border/60 bg-card p-4 shadow-sm sm:grid-cols-2 xl:grid-cols-3">
        <div className="grid gap-2">
          <Label htmlFor="bot-id" className="text-sm font-semibold">ID bot</Label>
          <Input
            id="bot-id"
            className="h-11 rounded-xl"
            value={bot.id}
            disabled={!isNew}
            onChange={(event) => patch('id', event.target.value)}
          />
        </div>

        <div className="grid gap-2">
          <Label htmlFor="bot-name" className="text-sm font-semibold">Nome bot</Label>
          <Input
            id="bot-name"
            className="h-11 rounded-xl"
            value={bot.name}
            onChange={(event) => patch('name', event.target.value)}
          />
        </div>

        <div className="grid gap-2">
          <Label htmlFor="company-name" className="text-sm font-semibold">Azienda</Label>
          <Input
            id="company-name"
            className="h-11 rounded-xl"
            value={bot.company_name}
            onChange={(event) => patch('company_name', event.target.value)}
          />
        </div>

        <div className="grid gap-2">
          <Label htmlFor="agent-name" className="text-sm font-semibold">Nome agente</Label>
          <Input
            id="agent-name"
            className="h-11 rounded-xl"
            value={bot.agent_name}
            onChange={(event) => patch('agent_name', event.target.value)}
          />
        </div>

        <div className="grid gap-2">
          <Label htmlFor="phone-number-id" className="text-sm font-semibold">Meta phone_number_id</Label>
          <Input
            id="phone-number-id"
            className="h-11 rounded-xl font-mono text-xs"
            value={bot.phone_number_id}
            onChange={(event) =>
              patch('phone_number_id', event.target.value)
            }
          />
        </div>

        <div className="grid gap-2">
          <Label htmlFor="booking-url" className="text-sm font-semibold">Booking URL</Label>
          <Input
            id="booking-url"
            className="h-11 rounded-xl"
            value={bot.booking_url}
            onChange={(event) => patch('booking_url', event.target.value)}
          />
        </div>

        <div className="grid gap-2">
          <Label htmlFor="default-template-name" className="text-sm font-semibold">Template di default</Label>
          <Input
            id="default-template-name"
            className="h-11 rounded-xl"
            value={bot.default_template_name}
            onChange={(event) =>
              patch('default_template_name', event.target.value)
            }
          />
        </div>

        <div className="grid gap-2">
          <Label htmlFor="template-language" className="text-sm font-semibold">Lingua template</Label>
          <Input
            id="template-language"
            className="h-11 rounded-xl"
            value={bot.template_language}
            onChange={(event) =>
              patch('template_language', event.target.value)
            }
          />
        </div>

        <div className="grid gap-2">
          <Label htmlFor="qualification-statuses" className="text-sm font-semibold">Stati</Label>
          <Input
            id="qualification-statuses"
            className="h-11 rounded-xl"
            placeholder="caldo, tiepido, freddo"
            value={listToCommaSeparated(bot.qualification_statuses)}
            onChange={(event) =>
              patch(
                'qualification_statuses',
                commaSeparatedToList(event.target.value),
              )
            }
          />
        </div>

        <div className="grid gap-2 sm:col-span-2 xl:col-span-3">
          <Label htmlFor="prompt-preamble" className="text-sm font-semibold">Prompt</Label>
          <Textarea
            id="prompt-preamble"
            className="min-h-40 rounded-xl"
            value={bot.prompt_preamble}
            onChange={(event) => patch('prompt_preamble', event.target.value)}
          />
        </div>
      </section>

      <FieldListEditor bot={bot} onChange={onChange} />
    </div>
  )
}
