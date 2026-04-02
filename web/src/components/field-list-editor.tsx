import { Plus, Trash2 } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
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
    <Card className="border-none bg-card/90 shadow-lg">
      <CardHeader className="gap-4">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            <CardTitle>Campi da raccogliere</CardTitle>
            <CardDescription>
              Questi campi generano lo schema JSON e guidano il prompt di qualifica.
            </CardDescription>
          </div>
          <Button size="sm" type="button" onClick={addField}>
            <Plus />
            Aggiungi campo
          </Button>
        </div>
      </CardHeader>

      <CardContent className="grid gap-4">
        {bot.fields.map((field, index) => (
          <div
            key={`${field.key}-${index}`}
            className="rounded-2xl border border-foreground/10 bg-background/80 p-4"
          >
            <div className="mb-4 flex items-start justify-between gap-3">
              <div className="flex items-center gap-2">
                <Badge variant="outline">Campo {index + 1}</Badge>
                {field.required ? <Badge>richiesto</Badge> : null}
              </div>

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
                <Label htmlFor={`field-options-${index}`}>
                  Opzioni ammesse
                </Label>
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
                <div className="space-y-0.5">
                  <div className="text-sm font-medium">Richiesto</div>
                  <div className="text-xs text-muted-foreground">
                    Se spento, il bot puo ignorarlo.
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
