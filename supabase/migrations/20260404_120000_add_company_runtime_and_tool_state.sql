alter table if exists public.bot_configs
    add column if not exists company_description text not null default '',
    add column if not exists service_area text not null default '',
    add column if not exists company_services_json jsonb not null default '[]'::jsonb,
    add column if not exists lead_manager_page_id text not null default '';

alter table if exists public.bot_configs
    alter column company_description set default '',
    alter column service_area set default '',
    alter column company_services_json set default '[]'::jsonb,
    alter column lead_manager_page_id set default '';

do $$
begin
    if exists (
        select 1
        from information_schema.columns
        where table_schema = 'public'
          and table_name = 'bot_configs'
          and column_name = 'company_services_json'
    ) then
        alter table public.bot_configs
            drop constraint if exists bot_configs_company_services_json_array;
        alter table public.bot_configs
            add constraint bot_configs_company_services_json_array
            check (jsonb_typeof(company_services_json) = 'array');
    end if;
end $$;

alter table if exists public.lead_states
    add column if not exists metadata_json jsonb not null default '{}'::jsonb;

alter table if exists public.lead_states
    alter column metadata_json set default '{}'::jsonb;

do $$
begin
    if exists (
        select 1
        from information_schema.columns
        where table_schema = 'public'
          and table_name = 'lead_states'
          and column_name = 'metadata_json'
    ) then
        alter table public.lead_states
            drop constraint if exists lead_states_metadata_json_object;
        alter table public.lead_states
            add constraint lead_states_metadata_json_object
            check (jsonb_typeof(metadata_json) = 'object');
    end if;
end $$;
