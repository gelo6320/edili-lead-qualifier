create schema if not exists lead_qualifier;

create table if not exists lead_qualifier.conversation_messages (
    id bigint generated always as identity primary key,
    wa_id text not null,
    role text not null check (role in ('user', 'assistant')),
    display_text text not null,
    api_content text not null,
    created_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_conversation_messages_wa_id_id
    on lead_qualifier.conversation_messages (wa_id, id);

create table if not exists lead_qualifier.lead_states (
    wa_id text primary key,
    zona_lavoro text not null,
    tipo_lavoro text not null,
    tempistica text not null,
    budget_indicativo text not null,
    disponibile_chiamata text not null check (disponibile_chiamata in ('si', 'no', 'forse', 'sconosciuto')),
    disponibile_sopralluogo text not null check (disponibile_sopralluogo in ('si', 'no', 'forse', 'sconosciuto')),
    stato_qualifica text not null check (stato_qualifica in ('nuovo', 'in_qualifica', 'qualificato', 'da_richiamare')),
    missing_fields_json jsonb not null default '[]'::jsonb,
    summary text not null,
    updated_at timestamptz not null default timezone('utc', now()),
    constraint lead_states_missing_fields_json_array
        check (jsonb_typeof(missing_fields_json) = 'array')
);

create table if not exists lead_qualifier.inbound_messages (
    message_id text primary key,
    wa_id text not null,
    status text not null check (status in ('processing', 'completed', 'failed')),
    error text not null default '',
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_inbound_messages_wa_id_created_at
    on lead_qualifier.inbound_messages (wa_id, created_at desc);
