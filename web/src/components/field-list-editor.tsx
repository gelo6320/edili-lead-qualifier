import { List, Plus, Trash2 } from 'lucide-react'

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
    <Card className="border-border/60 shadow-sm">
      <CardHeader className="border-b">
        <div className="flex items-center justify-between gap-4">
          <CardTitle className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
              <List className="h-4 w-4 text-primary" />
            </div>
            Campi
          </CardTitle>
          <Button size="sm" type="button" onClick={addField} className="gap-1.5 rounded-xl">
            <Plus className="h-3.5 w-3.5" />
            Aggiungi
          </Button>
        </div>
      </CardHeader>

      <CardContent className="grid gap-4 pt-4">
        {bot.fields.map((field, index) => (
          <div
            key={`${field.key}-${index}`}
            className="rounded-xl border border-border/60 bg-muted/20 p-5 transition-colors hover:bg-muted/30"
          >
            <div className="mb-4 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary/10 text-xs font-bold text-primary">
                  {index + 1}
                </div>
                <span className="text-sm font-semibold">Campo {index + 1}</span>
              </div>
              <Button
                size="icon-sm"
                type="button"
                variant="ghost"
                className="rounded-lg text-muted-foreground hover:text-destructive"
                onClick={() => removeField(index)}
                disabled={bot.fields.length === 1}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
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
            </div>

            <div className="mt-4 grid gap-2">
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

            <div className="mt-4 grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
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

              <div className="flex items-center gap-3 rounded-xl border border-border/60 bg-background px-4 py-2.5">
                <Switch
                  checked={field.required}
                  onCheckedChange={(checked) =>
                    updateField(index, { required: Boolean(checked) })
                  }
                />
                <Label className="text-sm font-semibold">Richiesto</Label>
              </div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
