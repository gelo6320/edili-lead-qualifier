alter table if exists public.bot_configs
    add column if not exists ghl_location_id text not null default '',
    add column if not exists qualified_lead_webhook_url text not null default '';

update public.bot_configs
set ghl_location_id = coalesce(ghl_location_id, ''),
    qualified_lead_webhook_url = coalesce(qualified_lead_webhook_url, '')
where ghl_location_id is null
   or qualified_lead_webhook_url is null;
