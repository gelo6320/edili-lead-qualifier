# SOP — Onboarding nuovo cliente

Procedura operativa per collegare un nuovo cliente al Lead Qualifier.

Architettura minima:
- **Meta / WhatsApp Cloud API** → invia messaggi al bot + riceve risposte
- **GoHighLevel (Lead Connector)** → invia lead nuovi al bot + riceve lead qualificati

Tempo stimato: **20–30 minuti** a cliente, se tutte le credenziali sono pronte.

---

## 0. Cosa serve dal cliente prima di iniziare

Raccogli queste informazioni **prima** di entrare in dashboard:

| Cosa | Dove si trova | Obbligatorio |
|---|---|---|
| Nome azienda, descrizione sintetica, zona operativa, servizi | Intervista cliente | Sì |
| Sito web pubblico (per crawl RAG) | Cliente | Consigliato |
| Accesso al Business Manager Meta del cliente (admin) | Meta Business Suite | Sì |
| Numero WhatsApp registrato nel WABA del cliente | WhatsApp Manager | Sì |
| Template WhatsApp approvato per il primo contatto | WhatsApp Manager | Sì |
| Location ID GoHighLevel del cliente | GHL → Settings → Company | Sì |
| Webhook URL in ingresso GHL (per ricevere lead qualificati) | GHL → Workflow → Inbound Webhook | Sì |
| URL di booking (Calendly/Cal/GHL) | Cliente | Opzionale |
| Campi lead da qualificare (tipo lavoro, zona, urgenza, ecc.) | Intervista cliente | Sì |

---

## 1. Accedi alla dashboard

1. Apri `https://<dominio-prod>/` (la URL che hai messo in `APP_BASE_URL`).
2. Login con email in `DASHBOARD_ALLOWED_EMAILS`.
3. Se l'email non è abilitata:
   - aggiungila in `.env` → `DASHBOARD_ALLOWED_EMAILS=mail1@x,mail2@x`
   - crea l'utente in Supabase → Authentication → Users → Invite
   - redeploy

---

## 2. Crea il bot del cliente

In dashboard, sezione **Bots**:

1. Clicca **Nuovo bot**.
2. Compila:
   - **id** → slug univoco, lowercase, es. `acme_edile` (va in PK della tabella, **non modificabile dopo**)
   - **name** → nome interno leggibile
   - **company_name** → ragione sociale mostrata al lead
   - **company_description** → 1–3 frasi. Viene iniettata nel system prompt
   - **service_area** → es. `Milano e provincia`
   - **company_services** → lista (es. `Ristrutturazioni, Tetti, Bagni`)
   - **agent_name** → nome della "persona" che parla in chat (es. `Giulia`)
   - **booking_url** → opzionale
3. Salva. Il bot viene persistito in `public.bot_configs` su Supabase.

> Il record eredita `owner_user_id = <tuo user supabase>`. Solo tu e bot "unowned" sono visibili nella tua dashboard.

---

## 3. Definisci i campi da qualificare

Sezione **Fields** dentro il bot.

Ogni campo è quello che Claude deve **estrarre dalla conversazione**. Regole:

- `key` → snake_case, univoco (es. `tipo_lavoro`)
- `label` → leggibile (es. "Tipo di lavoro")
- `description` → **importante**: finisce nel prompt. Scrivi *cosa* Claude deve cercare/chiedere (es. "Tipo di intervento richiesto: ristrutturazione, tetto, facciata, bagno…")
- `required` → true/false. I campi required sono l'obiettivo della qualifica
- `options` → valori ammessi opzionali (es. `["ricevute", "da inviare", "non disponibili"]`). Se vuoto, campo libero

**Minimo consigliato per un cliente edile/servizi:** tipo lavoro, zona, tempistica, orario richiamo, disponibilità sopralluogo.

Salva.

---

## 4. Collega Meta / WhatsApp

### 4a. Collega Facebook via OAuth

1. Dentro il bot, clicca **Collega Facebook**.
2. Autenticati con un account admin del Business Manager del cliente.
3. Autorizza gli scope richiesti (Business Management, WhatsApp Business Management, WhatsApp Business Messaging).
4. Dopo il redirect, il token utente del cliente è in **Supabase Vault** (non in chiaro).

### 4b. Seleziona gli asset WhatsApp

Dalla dropdown popolata automaticamente:

1. Seleziona il **Business** del cliente
2. Seleziona il **WABA** (WhatsApp Business Account)
3. Seleziona il **Phone Number** registrato del cliente
4. La dashboard salva:
   - `meta_business_id`, `meta_business_name`
   - `meta_waba_id`, `meta_waba_name`
   - `phone_number_id` ← **critico**, è la chiave di routing inbound
   - `whatsapp_display_phone_number` (solo display)

### 4c. Seleziona il template di default

Dropdown **Template di default** (popolata dai template approvati nel WABA):

1. Scegli il template per il **primo contatto** (stato `APPROVED`)
2. Imposta `template_language` (es. `it`)
3. La dashboard sincronizza automaticamente:
   - `default_template_id`
   - `default_template_name`
   - `default_template_body_text` (il body con `{{1}}`, `{{2}}`…)
   - `default_template_variable_count` (es. 2 se ci sono `{{1}}` e `{{2}}`)

> Se il template richiede **N** variabili, il runtime le popola così, nell'ordine: `full_name`, `company_name`, `service_area`, `booking_url`. Se ne servono di più o in ordine diverso → usa un template con meno variabili.

### 4d. Configura il webhook Meta (una sola volta per cliente)

Nella app Meta del cliente (o nella tua app Meta condivisa, dipende da setup):

1. Prodotto **WhatsApp** → Configuration → Webhooks
2. Callback URL: `https://<dominio-prod>/webhooks/whatsapp`
3. Verify Token: stesso valore in `.env` → `WHATSAPP_VERIFY_TOKEN`
4. Sottoscrivi almeno il campo `messages`
5. Verifica → deve tornare verde

> Se usi **un'unica app Meta** per tutti i clienti, il webhook va configurato **una volta sola**. Il routing per cliente avviene via `phone_number_id` (messaggio inbound → `BotConfigStore.get_by_phone_number_id()`).

### 4e. Test template

Sezione **Test template** del bot:

1. Inserisci il tuo numero personale in formato internazionale senza `+` (es. `393331234567`)
2. Compila i parametri body
3. Invia. Devi ricevere il messaggio WhatsApp in ~5 secondi
4. Rispondi al messaggio → arriva al bot → Claude risponde

Se fallisce con 401/403 → token scaduto: rifai 4a.
Se fallisce con "template not found" → ricontrolla nome/lingua e che sia `APPROVED`.

---

## 5. Collega GoHighLevel (Lead Connector)

### 5a. Routing inbound: GHL → Qualifier

Nel bot, sezione **Integrazioni**:

- **ghl_location_id** → Location ID del sub-account cliente in GHL (Settings → Company → Location ID)

In GHL, crea un **Workflow** che parte quando nasce un nuovo lead:

1. Trigger: **Contact Created** (o form submission, ads, ecc.)
2. Action: **Webhook** → URL: `https://<dominio-prod>/webhooks/ghl/qualification-start`
3. Method: `POST`
4. Body JSON — includi almeno:
   ```json
   {
     "location": { "id": "{{location.id}}" },
     "phone": "{{contact.phone}}",
     "full_name": "{{contact.name}}"
   }
   ```
5. (Opzionale, **solo se lo stesso `location.id` ha più bot**): aggiungi `custom_data.bot_id` con lo slug del bot.

Il qualifier risolve il bot così (vedi `lead_qualifier/services/ghl_bot_resolver.py`):
- priorità 1 → `custom_data.bot_id`
- priorità 2 → `location.id` → lookup per `ghl_location_id`

Risposta attesa (200):
```json
{ "status": "started", "bot_id": "acme_edile", "matched_by": "ghl_location_id", ... }
```

### 5b. Routing outbound: Qualifier → GHL

Quando Claude qualifica il lead, il tool di handoff fa `POST` al webhook del cliente.

In GHL, crea un **Inbound Webhook** (workflow separato):

1. Trigger: **Inbound Webhook**
2. Copia l'URL generato
3. Mappa i campi che ti servono dal payload JSON (vedi sotto)
4. Action: aggiornamento contatto, notifica, tag, whatever

Nel bot della dashboard, incolla l'URL in:
- **qualified_lead_webhook_url**

Payload inviato (riferimento: `integrations/qualified_lead_webhook/client.py`):
```json
{
  "wa_id": "393331234567",
  "contact_name": "Mario Rossi",
  "phone_number_id": "...",
  "field_values": { "tipo_lavoro": "ristrutturazione", "zona_lavoro": "Milano", ... },
  "qualification_status": "qualified",
  "missing_fields": [],
  "summary": "...",
  "images": ["https://..."],
  "conversation": [...]
}
```

---

## 6. (Opzionale) Crawl del sito cliente per RAG

Se il cliente ha un sito web:

1. Nel bot, campo **website_url**: incolla URL homepage
2. Clicca **Crawl sito**
3. Il sistema chiama Cloudflare Browser Rendering `/crawl`, estrae testo, lo spezza in chunks e salva in `public.bot_knowledge_chunks`
4. Output: numero pagine + chunks salvati + sommario

A runtime, ogni messaggio inbound fa una search RAG e inietta il contesto nel prompt di Claude.

Prerequisito env: `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_API_TOKEN` configurati. Se non lo sono, il bottone è nascosto (vedi `/api/dashboard/app-config`).

---

## 7. Checklist finale prima di consegnare al cliente

Da verificare **in quest'ordine**:

- [ ] `GET /healthz` → `200`
- [ ] Bot visibile in dashboard con **phone_number_id** non vuoto
- [ ] **default_template_name** valorizzato e matcha un template `APPROVED`
- [ ] **default_template_variable_count** corretto (confrontalo col body Meta)
- [ ] **ghl_location_id** valorizzato
- [ ] **qualified_lead_webhook_url** valorizzato e URL risponde 200 (test in GHL)
- [ ] Tab **Test template** → messaggio arriva sul tuo WhatsApp
- [ ] Rispondi → arriva in dashboard sotto il lead, Claude risponde
- [ ] Webhook GHL outbound → manda lead fake → verifica risposta `{"status":"started"}` e arrivo del template sul WhatsApp del lead fake
- [ ] Simula qualifica completa in chat → verifica payload arrivato al webhook GHL inbound

---

## 8. Troubleshooting rapido

| Sintomo | Causa probabile | Fix |
|---|---|---|
| Webhook Meta rifiuta con 403 | `META_APP_SECRET` mancante o `META_ENFORCE_SIGNATURE=true` con secret sbagliato | Allinea secret all'app Meta del webhook |
| Webhook Meta 403 "verify token" | `WHATSAPP_VERIFY_TOKEN` diverso tra env e Meta | Allinea stringa esatta |
| Template send → 401/403 | Token Meta scaduto / revocato | Rifai OAuth dashboard (step 4a) |
| Template send → "template not found" | Nome o lingua non coincidono con Meta | Ricontrolla spelling/case, stato `APPROVED` |
| GHL webhook → 404 "bot non trovato" | `ghl_location_id` non matcha | Verifica valore in GHL Settings → Company |
| Inbound WhatsApp non genera risposta | `phone_number_id` del bot non matcha il messaggio | Copia il phone_number_id esatto da Meta, senza spazi |
| Claude non estrae un campo | `description` del field troppo vaga | Riscrivi `description` dettagliata e specifica |
| Lead non arriva al webhook GHL outbound | `qualified_lead_webhook_url` vuoto o 4xx | Verifica URL in GHL, manda POST curl di test |

---

## 9. Riepilogo campi bot (reference veloce)

Chiavi gestite in dashboard (vedi `lead_qualifier/domain/bot_config.py`):

**Identità & azienda**
`id`, `name`, `company_name`, `company_description`, `service_area`, `company_services`, `agent_name`, `website_url`, `booking_url`

**Meta / WhatsApp** (popolati da OAuth)
`meta_business_id`, `meta_business_name`, `meta_waba_id`, `meta_waba_name`, `phone_number_id`, `whatsapp_display_phone_number`

**Template outbound** (popolati da OAuth + selezione)
`default_template_id`, `default_template_name`, `default_template_body_text`, `default_template_variable_count`, `template_language`

**GHL / Lead Connector**
`ghl_location_id`, `qualified_lead_webhook_url`

**Qualifica**
`qualification_statuses`, `fields[]`
