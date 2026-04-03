import { Plus, Trash2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import {
  commaSeparatedToList,
  createEmptyField,
  listToCommaSeparated,
} from '@/lib/bot-config'
import type { BotConfig, BotFieldConfig } from '@/lib/types'

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
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-4">
          <CardTitle>Campi</CardTitle>
          <Button size="sm" type="button" onClick={addField}>
            <Plus />
            Aggiungi
          </Button>
        </div>
      </CardHeader>

      <CardContent className="grid gap-4">
        {bot.fields.map((field, index) => (
          <div
            key={`${field.key}-${index}`}
            className="rounded-lg border bg-background p-4"
          >
            <div className="mb-4 flex items-center justify-between gap-3">
              <div className="text-sm font-medium">Campo {index + 1}</div>
              <Button
                size="icon-sm"
                type="button"
                variant="ghost"
                onClick={() => removeField(index)}
                disabled={bot.fields.length === 1}
              >
                <Trash2 />
              </Button>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="grid gap-2">
                <Label htmlFor={`field-key-${index}`}>Chiave</Label>
                <Input
                  id={`field-key-${index}`}
                  value={field.key}
                  onChange={(event) =>
                    updateField(index, { key: event.target.value })
                  }
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor={`field-label-${index}`}>Etichetta</Label>
                <Input
                  id={`field-label-${index}`}
                  value={field.label}
                  onChange={(event) =>
                    updateField(index, { label: event.target.value })
                  }
                />
              </div>
            </div>

            <div className="mt-4 grid gap-2">
              <Label htmlFor={`field-description-${index}`}>Descrizione</Label>
              <Textarea
                id={`field-description-${index}`}
                value={field.description}
                onChange={(event) =>
                  updateField(index, { description: event.target.value })
                }
              />
            </div>

            <div className="mt-4 grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
              <div className="grid gap-2">
                <Label htmlFor={`field-options-${index}`}>Opzioni</Label>
                <Input
                  id={`field-options-${index}`}
                  placeholder="si, no, forse"
                  value={listToCommaSeparated(field.options)}
                  onChange={(event) =>
                    updateField(index, {
                      options: commaSeparatedToList(event.target.value),
                    })
                  }
                />
              </div>

              <div className="flex items-center gap-3 rounded-xl border border-foreground/10 bg-muted/60 px-4 py-2">
                <Switch
                  checked={field.required}
                  onCheckedChange={(checked) =>
                    updateField(index, { required: Boolean(checked) })
                  }
                />
                <Label>Richiesto</Label>
              </div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
