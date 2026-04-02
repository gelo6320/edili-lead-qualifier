create table if not exists public.bot_configs (
    bot_id text primary key,
    name text not null,
    company_name text not null,
    agent_name text not null default 'Giulia',
    phone_number_id text not null default '',
    default_template_name text not null default '',
    template_language text not null default 'it',
    booking_url text not null default '',
    prompt_preamble text not null default '',
    qualification_statuses_json jsonb not null default '["new","in_progress","qualified","follow_up"]'::jsonb,
    fields_json jsonb not null,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now()),
    constraint bot_configs_qualification_statuses_json_array check (jsonb_typeof(qualification_statuses_json) = 'array'),
    constraint bot_configs_fields_json_array check (jsonb_typeof(fields_json) = 'array')
);

create unique index if not exists idx_bot_configs_phone_number_id
    on public.bot_configs (phone_number_id)
    where phone_number_id <> '';

create table if not exists public.conversation_messages (
    id bigint generated always as identity primary key,
    bot_id text not null,
    wa_id text not null,
    role text not null check (role in ('user', 'assistant')),
    display_text text not null,
    api_content text not null,
    created_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_conversation_messages_bot_wa_id_id
    on public.conversation_messages (bot_id, wa_id, id);

create table if not exists public.lead_states (
    bot_id text not null,
    wa_id text not null,
    field_values_json jsonb not null default '{}'::jsonb,
    qualification_status text not null,
    missing_fields_json jsonb not null default '[]'::jsonb,
    summary text not null default '',
    updated_at timestamptz not null default timezone('utc', now()),
    primary key (bot_id, wa_id),
    constraint lead_states_field_values_json_object check (jsonb_typeof(field_values_json) = 'object'),
    constraint lead_states_missing_fields_json_array check (jsonb_typeof(missing_fields_json) = 'array')
);

create table if not exists public.inbound_messages (
    message_id text primary key,
    bot_id text not null,
    wa_id text not null,
    status text not null check (status in ('processing', 'completed', 'failed')),
    error text not null default '',
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_inbound_messages_bot_wa_id_created_at
    on public.inbound_messages (bot_id, wa_id, created_at desc);

do $$
begin
    if exists (select 1 from pg_namespace where nspname = 'lead_qualifier') then
        if exists (
            select 1
            from information_schema.tables
            where table_schema = 'lead_qualifier' and table_name = 'conversation_messages'
        ) and not exists (
            select 1 from public.conversation_messages where bot_id = 'default'
        ) then
            insert into public.conversation_messages (bot_id, wa_id, role, display_text, api_content, created_at)
            select
                'default',
                wa_id,
                role,
                display_text,
                api_content,
                created_at
            from lead_qualifier.conversation_messages;
        end if;

        if exists (
            select 1
            from information_schema.tables
            where table_schema = 'lead_qualifier' and table_name = 'lead_states'
        ) and not exists (
            select 1 from public.lead_states where bot_id = 'default'
        ) then
            insert into public.lead_states (
                bot_id,
                wa_id,
                field_values_json,
                qualification_status,
                missing_fields_json,
                summary,
                updated_at
            )
            select
                'default',
                wa_id,
                jsonb_strip_nulls(
                    jsonb_build_object(
                        'zona_lavoro', nullif(zona_lavoro, ''),
                        'tipo_lavoro', nullif(tipo_lavoro, ''),
                        'tempistica', nullif(tempistica, ''),
                        'budget_indicativo', nullif(budget_indicativo, ''),
                        'disponibile_chiamata', case
                            when disponibile_chiamata = 'sconosciuto' then ''
                            else disponibile_chiamata
                        end
                    )
                ),
                case stato_qualifica
                    when 'nuovo' then 'new'
                    when 'in_qualifica' then 'in_progress'
                    when 'qualificato' then 'qualified'
                    when 'da_richiamare' then 'follow_up'
                    else 'new'
                end,
                coalesce(missing_fields_json, '[]'::jsonb),
                coalesce(summary, ''),
                updated_at
            from lead_qualifier.lead_states;
        end if;

        if exists (
            select 1
            from information_schema.tables
            where table_schema = 'lead_qualifier' and table_name = 'inbound_messages'
        ) and not exists (
            select 1 from public.inbound_messages where bot_id = 'default'
        ) then
            insert into public.inbound_messages (
                message_id,
                bot_id,
                wa_id,
                status,
                error,
                created_at,
                updated_at
            )
            select
                message_id,
                'default',
                wa_id,
                status,
                error,
                created_at,
                updated_at
            from lead_qualifier.inbound_messages;
        end if;
    end if;
end $$;
