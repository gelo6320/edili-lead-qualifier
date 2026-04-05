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
    <section className="rounded-xl border border-border/60 bg-card p-4 shadow-sm">
      <div className="mb-4 flex items-center justify-between gap-4">
        <span className="rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground">
          {bot.fields.length} campi
        </span>
        <Button size="sm" type="button" onClick={addField} className="rounded-xl">
          + Aggiungi
        </Button>
      </div>

      <div className="grid gap-4">
        {bot.fields.map((field, index) => (
          <div
            key={`${field.key}-${index}`}
            className="rounded-xl border border-border/60 bg-muted/20 p-4 transition-colors hover:bg-muted/30"
          >
            <div className="mb-4 flex items-center justify-between gap-3">
              <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10 text-xs font-bold text-primary">
                {index + 1}
              </div>
              <Button
                size="icon-sm"
                type="button"
                variant="ghost"
                className="rounded-lg text-muted-foreground hover:text-destructive"
                onClick={() => removeField(index)}
                disabled={bot.fields.length === 1}
              >
                ✕
              </Button>
            </div>

            <div className="grid gap-4 lg:grid-cols-2 2xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_auto]">
              <div className="grid gap-2">
                <Label htmlFor={`field-key-${index}`} className="text-sm font-semibold">Chiave</Label>
                <Input
                  id={`field-key-${index}`}
                  className="h-10 rounded-xl"
                  value={field.key}
                  onChange={(event) =>
                    updateField(index, { key: event.target.value })
                  }
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor={`field-label-${index}`} className="text-sm font-semibold">Etichetta</Label>
                <Input
                  id={`field-label-${index}`}
                  className="h-10 rounded-xl"
                  value={field.label}
                  onChange={(event) =>
                    updateField(index, { label: event.target.value })
                  }
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor={`field-options-${index}`} className="text-sm font-semibold">Opzioni</Label>
                <Input
                  id={`field-options-${index}`}
                  className="h-10 rounded-xl"
                  placeholder="si, no, forse"
                  value={listToCommaSeparated(field.options)}
                  onChange={(event) =>
                    updateField(index, {
                      options: commaSeparatedToList(event.target.value),
                    })
                  }
                />
              </div>

              <div className="flex items-center gap-3 rounded-xl border border-border/60 bg-background px-4 py-2.5 lg:self-end 2xl:min-w-[9rem]">
                <Switch
                  checked={field.required}
                  onCheckedChange={(checked) =>
                    updateField(index, { required: Boolean(checked) })
                  }
                />
                <Label className="text-sm font-semibold">Richiesto</Label>
              </div>

              <div className="grid gap-2 lg:col-span-2 2xl:col-span-4">
                <Label htmlFor={`field-description-${index}`} className="text-sm font-semibold">Descrizione</Label>
                <Textarea
                  id={`field-description-${index}`}
                  className="rounded-xl"
                  value={field.description}
                  onChange={(event) =>
                    updateField(index, { description: event.target.value })
                  }
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
