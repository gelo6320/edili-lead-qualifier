# Lead Qualifier Control

Backend FastAPI + dashboard React per gestire un singolo runtime WhatsApp multi-tenant.

Il runtime:
- riceve messaggi da WhatsApp Cloud API
- risolve il tenant in base al `phone_number_id`
- usa Claude Sonnet 4.6 con prompt dinamico e schema JSON generato dai campi del bot
- salva conversazioni, stato lead e configurazioni su Supabase

La dashboard:
- vive sulla root `/`
- usa Supabase Auth via email magic link
- amministra i bot in UI minimale con componenti shadcn

## Cosa e cambiato

- Nessuno schema lead hardcoded nel codice.
- Ogni bot definisce i propri campi richiesti e il proprio prompt.
- I file in [bot_configs](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/bot_configs) restano come seed/versioning.
- In produzione le configurazioni vengono persistite in `public.bot_configs` su Supabase.
- Le tabelle runtime multi-tenant sono in `public`, non piu nello schema legacy `lead_qualifier`.

## Architettura

- [app.py](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/app.py): entrypoint ASGI
- [lead_qualifier/app_factory.py](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/lead_qualifier/app_factory.py): bootstrap app, store, router, static dashboard
- [lead_qualifier/bot_config_store.py](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/lead_qualifier/bot_config_store.py): store ibrido config files -> Supabase runtime
- [lead_qualifier/prompting.py](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/lead_qualifier/prompting.py): prompt e schema JSON dinamici
- [lead_qualifier/message_service.py](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/lead_qualifier/message_service.py): pipeline inbound WhatsApp
- [lead_qualifier/postgres_store.py](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/lead_qualifier/postgres_store.py): persistenza lead runtime su Supabase Postgres
- [lead_qualifier/dashboard_api_router.py](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/lead_qualifier/dashboard_api_router.py): API dashboard
- [lead_qualifier/dashboard_auth.py](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/lead_qualifier/dashboard_auth.py): validazione sessione Supabase Auth
- [web/src/App.tsx](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/web/src/App.tsx): dashboard SPA
- [supabase/migrations/20260403_020000_create_multitenant_runtime.sql](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/supabase/migrations/20260403_020000_create_multitenant_runtime.sql): schema runtime multi-tenant

## Dati su Supabase

Tabelle nuove:
- `public.bot_configs`
- `public.conversation_messages`
- `public.lead_states`
- `public.inbound_messages`

Migrazione applicata sul progetto Supabase:
- project ref: `gracxyeruxrlqsgesjrt`
- nome migration: `create_multitenant_runtime`
- i dati legacy single-tenant sono stati copiati in `public.*` come `bot_id = 'default'`

Nota pratica:
- al primo avvio del nuovo backend, se `public.bot_configs` e vuota, le configurazioni presenti in [bot_configs](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/bot_configs) vengono seedate automaticamente nel database
- dopo il seed, la dashboard salva su Supabase, non sul filesystem locale

## Env

File esempio:
- [.env.example](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/.env.example)

### Anthropic

`ANTHROPIC_API_KEY`
- obbligatoria
- chiave API Anthropic reale

`ANTHROPIC_MODEL`
- consigliato: `claude-sonnet-4-6`

### Sicurezza admin legacy

`ADMIN_API_KEY`
- bearer secret per l'endpoint legacy `/admin/whatsapp/template`
- la dashboard non usa questa chiave; usa Supabase Auth

### Database

`DATABASE_URL`
- obbligatoria in produzione
- usa la `Session pooler` URI di Supabase

`DATABASE_SCHEMA`
- consigliato: `public`

`DATABASE_POOL_MIN_SIZE`
- consigliato: `1`

`DATABASE_POOL_MAX_SIZE`
- consigliato: `10`

`DATABASE_POOL_TIMEOUT_SECONDS`
- consigliato: `10`

`SQLITE_PATH`
- solo fallback locale

### Dashboard / Supabase Auth

`SUPABASE_URL`
- URL progetto Supabase, esempio `https://gracxyeruxrlqsgesjrt.supabase.co`

`SUPABASE_PUBLISHABLE_KEY`
- publishable key del progetto

`DASHBOARD_ALLOWED_EMAILS`
- opzionale ma fortemente consigliata
- lista email separate da virgola
- se valorizzata, solo queste email possono entrare in dashboard

### Config seed e asset dashboard

`BOT_CONFIG_DIR`
- default: `bot_configs`

`DASHBOARD_DIST_DIR`
- default: `web/dist`

### WhatsApp Cloud API

`WHATSAPP_API_BASE_URL`
- default: `https://graph.facebook.com`

`WHATSAPP_GRAPH_VERSION`
- verificato sui docs Meta il 3 aprile 2026: `v23.0`

`WHATSAPP_ACCESS_TOKEN`
- token permanente Meta del system user

`WHATSAPP_BUSINESS_ACCOUNT_ID`
- WABA id

`WHATSAPP_VERIFY_TOKEN`
- token configurato nel webhook Meta

### Sicurezza webhook Meta

`META_APP_SECRET`
- App Secret della stessa app Meta che invia i webhook

`META_ENFORCE_SIGNATURE`
- produzione: `true`

### Logging

`LOG_LEVEL`
- consigliato: `INFO`

## Config file bot

Ogni file JSON seed descrive un tenant.

Esempio:
- [bot_configs/default.json](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/bot_configs/default.json)

Campi principali:
- `id`
- `name`
- `company_name`
- `agent_name`
- `phone_number_id`
- `default_template_name`
- `template_language`
- `booking_url`
- `prompt_preamble`
- `qualification_statuses`
- `fields[]`

Ogni `field` contiene:
- `key`
- `label`
- `description`
- `required`
- `options`

## Setup locale

### Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Frontend

```bash
cd web
pnpm install
pnpm build
cd ..
```

### Env

```bash
cp .env.example .env
```

## Avvio locale

```bash
source .venv/bin/activate
/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/.venv/bin/uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Verifiche rapide:

```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/api/dashboard/app-config
curl "http://localhost:8000/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=dev-token&hub.challenge=12345"
```

## Setup Supabase per la dashboard

1. Apri il progetto Supabase.
2. Vai su `Authentication`.
3. Abilita email auth.
4. Imposta `Site URL` uguale al dominio della tua app Railway.
5. Aggiungi lo stesso dominio in `Redirect URLs`.
6. Crea o invita gli utenti admin che devono entrare in dashboard.
7. Metti le loro email in `DASHBOARD_ALLOWED_EMAILS`.

Nota:
- la dashboard usa `signInWithOtp(...shouldCreateUser: false...)`
- quindi l'utente deve gia esistere in Supabase Auth

## Setup Meta / WhatsApp

1. Configura l'app Meta con prodotto WhatsApp.
2. Registra il numero reale nel WABA corretto.
3. Imposta il webhook su:
   `https://<tuo-dominio>/webhooks/whatsapp`
4. Sottoscrivi almeno il campo `messages`.
5. Metti `phone_number_id` dentro il bot corretto dalla dashboard.

## Deploy Railway

Il repo include [nixpacks.toml](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/nixpacks.toml), quindi Railway puo:
- installare dipendenze Python
- installare e buildare il frontend in `web/`
- avviare `uvicorn`

Passi:
1. Collega il repo a Railway.
2. Imposta tutte le env.
3. Verifica che Railway usi Nixpacks.
4. Deploya.
5. Apri `/healthz`.
6. Apri `/`.
7. Fai login con email Supabase.
8. Compila o correggi i bot, soprattutto `phone_number_id`.

Start command atteso:

```bash
uvicorn app:app --host 0.0.0.0 --port $PORT
```

## Verifiche eseguite

- `python3 -m py_compile app.py lead_qualifier/*.py`
- `pnpm build` in [web](/Users/olegbolonniy/Desktop/CHAT-CLAUDE-EDILI/web)
- smoke test locale server:
  - `GET /healthz` -> `200`
  - `GET /api/dashboard/app-config` -> `200`
  - `GET /` -> `200` con `index.html` buildato
- migration Supabase applicata con successo

## Riferimenti ufficiali usati

- [Supabase passwordless email logins](https://supabase.com/docs/guides/auth/auth-email-passwordless)
- [Supabase JS `signInWithOtp`](https://supabase.com/docs/reference/javascript/auth-signinwithotp)
- [shadcn/ui CLI](https://ui.shadcn.com/docs/cli)
- [Tailwind CSS with Vite](https://tailwindcss.com/docs/installation/using-vite)
- [Meta WhatsApp Cloud API Get Started](https://developers.facebook.com/docs/whatsapp/cloud-api/get-started)
- [Meta Graph Webhooks Getting Started](https://developers.facebook.com/docs/graph-api/webhooks/getting-started)
- [Anthropic Prompt Caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- [Anthropic Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
