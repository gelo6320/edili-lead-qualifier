# WhatsApp Lead Qualifier Backend

Backend Python per qualificare lead edili via WhatsApp Cloud API usando Claude Sonnet 4.6.

Non c'e alcuna UI. Il servizio espone:
- webhook Meta per ricevere i messaggi WhatsApp
- endpoint admin protetto per inviare il primo template outbound
- storage production-grade su Supabase Postgres

## Stack di produzione

- App server: FastAPI + Uvicorn
- LLM: Anthropic `claude-sonnet-4-6`
- Canale messaggi: WhatsApp Cloud API
- Database: Supabase Postgres
- Deploy previsto: Railway

Progetto Supabase usato per questo prototipo:
- nome: `edili lead qualifier`
- project ref: `gracxyeruxrlqsgesjrt`
- URL progetto: `https://gracxyeruxrlqsgesjrt.supabase.co`

Schema DB applicativo:
- `lead_qualifier`

Migration locale nel repo:
- [20260402_210500_create_lead_qualifier_schema.sql](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/supabase/migrations/20260402_210500_create_lead_qualifier_schema.sql)

## Architettura

- [app.py](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/app.py): entrypoint ASGI minimale
- [app_factory.py](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/lead_qualifier/app_factory.py): bootstrap app, router, healthcheck e lifecycle
- [settings.py](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/lead_qualifier/settings.py): parsing env
- [prompting.py](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/lead_qualifier/prompting.py): schema JSON e prompt Claude con caching
- [anthropic_client.py](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/lead_qualifier/anthropic_client.py): chiamate Anthropic
- [whatsapp_client.py](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/lead_qualifier/whatsapp_client.py): invio text/template verso Meta
- [webhook_router.py](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/lead_qualifier/webhook_router.py): verify webhook + eventi inbound Meta
- [admin_router.py](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/lead_qualifier/admin_router.py): endpoint admin protetto per template outbound
- [postgres_store.py](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/lead_qualifier/postgres_store.py): persistenza Supabase Postgres
- [sqlite_store.py](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/lead_qualifier/sqlite_store.py): fallback locale
- [store_factory.py](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/lead_qualifier/store_factory.py): selezione store
- [message_service.py](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/lead_qualifier/message_service.py): logica di qualifica lead

## Env, una per una

File di esempio:
- [.env.example](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/.env.example)

### Anthropic

`ANTHROPIC_API_KEY`
- Obbligatoria.
- Valore: la tua API key Anthropic.
- Dove prenderla: console Anthropic.
- Esempio: `ANTHROPIC_API_KEY=sk-ant-...`

`ANTHROPIC_MODEL`
- Obbligatoria.
- Valore consigliato: `claude-sonnet-4-6`
- Non cambiarla finche non decidi di testare un altro modello.

### Identita business

`COMPANY_NAME`
- Obbligatoria.
- Nome reale dell'impresa cliente o del brand che sta scrivendo al lead.
- Esempio: `COMPANY_NAME=Edilnova Milano`

`AGENT_NAME`
- Obbligatoria.
- Nome che il modello usa per presentarsi.
- Esempio: `AGENT_NAME=Giulia`

`CALL_BOOKING_URL`
- Opzionale.
- Link da proporre quando il lead accetta una chiamata.
- Se vuota, il modello propone la chiamata senza link.
- Esempio: `CALL_BOOKING_URL=https://cal.com/edilnova/sopralluogo`

`ADMIN_API_KEY`
- Obbligatoria.
- Segreto bearer per chiamare l'endpoint interno `/admin/whatsapp/template`.
- Generane una lunga almeno 32 caratteri.
- Esempio: `ADMIN_API_KEY=7f2d7c8b6a3e...`

### Database

`DATABASE_URL`
- Obbligatoria in produzione.
- Usa la stringa `Session pooler` del progetto Supabase, non costruirla a mano.
- Dove prenderla: Supabase Dashboard > progetto `edili lead qualifier` > `Connect` > `Session pooler`.
- Per Railway questa e la scelta piu sicura, perche supporta IPv4 e connessioni persistenti.
- La stringa deve includere SSL. Se il valore copiato non contiene parametri, aggiungi `?sslmode=require`. Se ha gia parametri, aggiungi `&sslmode=require`.
- Formato tipico:
  `postgres://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require`

`DATABASE_POOL_MIN_SIZE`
- Obbligatoria in produzione.
- Valore consigliato per 1 istanza Railway: `1`

`DATABASE_POOL_MAX_SIZE`
- Obbligatoria in produzione.
- Valore consigliato per 1 istanza Railway: `10`
- Se aumenti le repliche Railway, rivaluta questo numero.

`DATABASE_POOL_TIMEOUT_SECONDS`
- Obbligatoria in produzione.
- Timeout di acquisizione connessione dal pool.
- Valore consigliato: `10`

`SQLITE_PATH`
- Solo fallback locale.
- In produzione con Supabase puoi lasciarla presente ma non viene usata se `DATABASE_URL` e valorizzata.
- Valore consigliato locale: `data/lead_qualifier.sqlite3`

### WhatsApp Cloud API

`WHATSAPP_API_BASE_URL`
- Obbligatoria.
- Valore: `https://graph.facebook.com`

`WHATSAPP_GRAPH_VERSION`
- Obbligatoria.
- Valore verificato nei docs Meta il 2 aprile 2026: `v23.0`

`WHATSAPP_ACCESS_TOKEN`
- Obbligatoria.
- Deve essere il token permanente del System User Meta.
- Non usare il token temporaneo del quickstart in produzione.

`WHATSAPP_PHONE_NUMBER_ID`
- Obbligatoria.
- Valore preso dal quickstart/configurazione WhatsApp Cloud API nel portale Meta.

`WHATSAPP_BUSINESS_ACCOUNT_ID`
- Obbligatoria.
- Valore del WABA.
- Oggi viene mantenuta a config per completezza operativa, anche se il runtime attuale non la usa direttamente nelle query.

`WHATSAPP_VERIFY_TOKEN`
- Obbligatoria.
- Stringa arbitraria scelta da te.
- Deve combaciare esattamente con il valore configurato nel webhook Meta.
- Esempio: `WHATSAPP_VERIFY_TOKEN=edili-webhook-prod-01`

`WHATSAPP_TEMPLATE_LANGUAGE`
- Obbligatoria.
- Deve combaciare con la lingua del template approvato in Meta.
- Usa esattamente il codice mostrato nel template approvato, per esempio `it` oppure `it_IT`.

### Sicurezza webhook Meta

`META_APP_SECRET`
- Obbligatoria in produzione.
- App Secret dell'app Meta.
- Serve per verificare la firma `X-Hub-Signature-256`.

`META_ENFORCE_SIGNATURE`
- Obbligatoria.
- Produzione: `true`
- Solo test locali con curl manuali: puoi metterla temporaneamente a `false`

### Logging

`LOG_LEVEL`
- Obbligatoria.
- Valore consigliato: `INFO`

## Setup locale

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Per avvio locale rapido senza Supabase puoi lasciare `DATABASE_URL` vuota.

## Avvio locale

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Controlli base:

```bash
curl http://localhost:8000/healthz
curl "http://localhost:8000/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=dev-token&hub.challenge=12345"
```

## Flusso applicativo

1. Meta verifica il webhook con `GET /webhooks/whatsapp`.
2. Meta invia gli eventi con `POST /webhooks/whatsapp`.
3. Il backend verifica la firma con `META_APP_SECRET`.
4. Il messaggio inbound viene salvato nel database Supabase.
5. Claude legge la cronologia e restituisce JSON strutturato.
6. Il backend aggiorna lo stato del lead.
7. Il backend risponde su WhatsApp.
8. Se devi contattare tu per primo il lead, usi `/admin/whatsapp/template`.

## Step by step produzione

### 1. Meta

Crea o completa la configurazione della tua app Meta:
- use case: `Connettiti con i clienti tramite WhatsApp`
- collega il tuo account WhatsApp Business
- annota `WHATSAPP_PHONE_NUMBER_ID`
- annota `WHATSAPP_BUSINESS_ACCOUNT_ID`
- invia il template `hello_world` dal quickstart e rispondi una volta

Doc ufficiale:
- [WhatsApp Cloud API Get Started](https://developers.facebook.com/docs/whatsapp/cloud-api/get-started)

### 2. Token permanente Meta

Crea un System User in Business Settings e genera un token con:
- `business_management`
- `whatsapp_business_messaging`
- `whatsapp_business_management`

### 3. Template di primo contatto

Per scrivere tu per primo a un lead fuori dalla finestra di 24 ore devi usare un template approvato.

Per il tuo caso partirei con un template `utility`, ad esempio:
- nome: `lead_primo_contatto`
- lingua: `it`
- body: `Ciao, ti contatto da {{1}} per la richiesta che ci hai inviato. Ti va di dirci in quale zona si trova il lavoro?`

Docs ufficiali:
- [WhatsApp Templates Overview](https://developers.facebook.com/documentation/business-messaging/whatsapp/templates/overview)
- [WhatsApp Template Categorization](https://developers.facebook.com/documentation/business-messaging/whatsapp/templates/template-categorization)
- [WhatsApp Template Components](https://developers.facebook.com/documentation/business-messaging/whatsapp/templates/components)

### 4. Supabase

Il database di produzione e il progetto:
- `edili lead qualifier`
- ref `gracxyeruxrlqsgesjrt`

La migration del servizio crea queste tabelle nello schema privato `lead_qualifier`:
- `conversation_messages`
- `lead_states`
- `inbound_messages`

### 5. Railway

Deploy come servizio web Python standard.

Start command:

```bash
uvicorn app:app --host 0.0.0.0 --port $PORT
```

Il repo include anche [Procfile](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/Procfile).

### 6. Variabili Railway

Imposta almeno:
- `ANTHROPIC_API_KEY`
- `ANTHROPIC_MODEL=claude-sonnet-4-6`
- `COMPANY_NAME`
- `AGENT_NAME`
- `CALL_BOOKING_URL`
- `ADMIN_API_KEY`
- `DATABASE_URL`
- `DATABASE_POOL_MIN_SIZE=1`
- `DATABASE_POOL_MAX_SIZE=10`
- `DATABASE_POOL_TIMEOUT_SECONDS=10`
- `WHATSAPP_API_BASE_URL=https://graph.facebook.com`
- `WHATSAPP_GRAPH_VERSION=v23.0`
- `WHATSAPP_ACCESS_TOKEN`
- `WHATSAPP_PHONE_NUMBER_ID`
- `WHATSAPP_BUSINESS_ACCOUNT_ID`
- `WHATSAPP_VERIFY_TOKEN`
- `WHATSAPP_TEMPLATE_LANGUAGE`
- `META_APP_SECRET`
- `META_ENFORCE_SIGNATURE=true`
- `LOG_LEVEL=INFO`

### 7. Webhook Meta

Quando Railway ti assegna il dominio pubblico:
- Callback URL: `https://tuo-dominio.up.railway.app/webhooks/whatsapp`
- Verify token: stesso valore di `WHATSAPP_VERIFY_TOKEN`
- Sottoscrivi il campo `messages`

Doc ufficiale:
- [Graph API Webhooks Getting Started](https://developers.facebook.com/docs/graph-api/webhooks/getting-started)

### 8. Primo messaggio outbound

Per iniziare la conversazione:

```bash
curl -X POST "https://tuo-dominio.up.railway.app/admin/whatsapp/template" \
  -H "Authorization: Bearer LA_TUA_ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "39XXXXXXXXXX",
    "template_name": "lead_primo_contatto",
    "language_code": "it",
    "body_parameters": ["Edilnova Milano"]
  }'
```

Se il lead risponde, da quel momento il flusso inbound passa automaticamente sul webhook.

## Note database

Supabase raccomanda:
- direct connection per backend persistenti solo se la rete supporta IPv6
- session pooler per backend persistenti che devono funzionare bene anche su IPv4
- transaction pooler per workload serverless e temporanei

Per Railway, qui ho impostato il progetto per usare `DATABASE_URL` del `Session pooler`.

Doc ufficiale Supabase:
- [Connect to your database](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [Using SQLAlchemy with Supabase](https://supabase.com/docs/guides/troubleshooting/using-sqlalchemy-with-supabase-FUqebT)
- [Postgres SSL Enforcement](https://supabase.com/docs/guides/platform/ssl-enforcement)

## Note Anthropic

Ottimizzazioni attive:
- modello `claude-sonnet-4-6`
- output strutturato con JSON schema
- prompt caching esplicito sugli esempi statici
- request-level cache control `ephemeral`

Docs ufficiali:
- [Claude 4.6](https://platform.claude.com/docs/en/about-claude/models/whats-new-claude-4-6)
- [Prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- [Structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)

## Limiti correnti

- nessun pannello operatore
- nessun handoff umano
- nessun CRM collegato
- endpoint admin pronto, ma non ancora collegato a un form o a un gestionale
