import { X } from 'lucide-react'
import {
  commaSeparatedToList,
  createEmptyField,
  listToCommaSeparated,
} from '@/shared/lib/bot-config'
import type { BotConfig, BotFieldConfig } from '@/shared/lib/types'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Label } from '@/shared/ui/label'
import { Switch } from '@/shared/ui/switch'
import { Textarea } from '@/shared/ui/textarea'

type FieldListEditorProps = {
  bot: BotConfig
  onChange: (bot: BotConfig) => void
}

export function FieldListEditor({ bot, onChange }: FieldListEditorProps) {
  function updateField(index: number, patch: Partial<BotFieldConfig>) {
    const nextFields = bot.fields.map((field, currentIndex) =>
      currentIndex === index ? { ...field, ...patch } : field,
    )
    onChange({ ...bot, fields: nextFields })
  }

  function addField() {
    onChange({
      ...bot,
      fields: [...bot.fields, createEmptyField()],
    })
  }

  function removeField(index: number) {
    if (bot.fields.length === 1) {
      return
    }

    onChange({
      ...bot,
      fields: bot.fields.filter((_, currentIndex) => currentIndex !== index),
    })
  }

  return (
    <section className="rounded-md border border-border bg-card">
      <header className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold leading-tight">Campi di qualificazione</h2>
          <span className="rounded-sm bg-muted px-1.5 py-0.5 text-[11px] font-medium text-muted-foreground">
            {bot.fields.length}
          </span>
        </div>
        <Button size="sm" type="button" onClick={addField}>
          + Aggiungi
        </Button>
      </header>

      <div className="divide-y divide-border">
        {bot.fields.map((field, index) => (
          <div key={field.editor_id ?? `field-${index}`} className="p-4">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground">
                Campo {index + 1}
              </span>
              <Button
                size="icon-sm"
                type="button"
                variant="ghost"
                className="text-muted-foreground hover:text-destructive"
                onClick={() => removeField(index)}
                disabled={bot.fields.length === 1}
                aria-label="Rimuovi campo"
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>

            <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_auto]">
              <div className="grid gap-1.5">
                <Label
                  htmlFor={`field-key-${index}`}
                  className="text-xs font-medium text-muted-foreground"
                >
                  Chiave
                </Label>
                <Input
                  id={`field-key-${index}`}
                  className="h-9 rounded-md"
                  value={field.key}
                  onChange={(event) => updateField(index, { key: event.target.value })}
                />
              </div>

              <div className="grid gap-1.5">
                <Label
                  htmlFor={`field-label-${index}`}
                  className="text-xs font-medium text-muted-foreground"
                >
                  Etichetta
                </Label>
                <Input
                  id={`field-label-${index}`}
                  className="h-9 rounded-md"
                  value={field.label}
                  onChange={(event) => updateField(index, { label: event.target.value })}
                />
              </div>

              <div className="grid gap-1.5">
                <Label
                  htmlFor={`field-options-${index}`}
                  className="text-xs font-medium text-muted-foreground"
                >
                  Opzioni
                </Label>
                <Input
                  id={`field-options-${index}`}
                  className="h-9 rounded-md"
                  placeholder="si, no, forse"
                  value={listToCommaSeparated(field.options)}
                  onChange={(event) =>
                    updateField(index, {
                      options: commaSeparatedToList(event.target.value),
                    })
                  }
                />
              </div>

              <div className="flex items-center gap-2 md:self-end md:pb-1">
                <Switch
                  checked={field.required}
                  onCheckedChange={(checked) =>
                    updateField(index, { required: Boolean(checked) })
                  }
                />
                <Label className="text-xs font-medium">Richiesto</Label>
              </div>

              <div className="grid gap-1.5 md:col-span-4">
                <Label
                  htmlFor={`field-description-${index}`}
                  className="text-xs font-medium text-muted-foreground"
                >
                  Descrizione
                </Label>
                <Textarea
                  id={`field-description-${index}`}
                  className="min-h-20 rounded-md"
                  value={field.description}
                  onChange={(event) => updateField(index, { description: event.target.value })}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
