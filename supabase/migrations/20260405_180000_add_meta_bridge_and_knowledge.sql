create extension if not exists pgcrypto;
create extension if not exists vault with schema vault;

create or replace function public.upsert_vault_secret(
    p_secret text,
    p_secret_id uuid default null,
    p_name text default null,
    p_description text default null
)
returns table(secret_id uuid)
language plpgsql
security definer
set search_path = public, vault
as $$
declare
    v_secret_id uuid;
begin
    if coalesce(btrim(p_secret), '') = '' then
        raise exception 'Secret cannot be empty.';
    end if;

    if p_secret_id is not null then
        perform vault.update_secret(
            p_secret_id,
            p_secret,
            nullif(btrim(coalesce(p_name, '')), ''),
            nullif(btrim(coalesce(p_description, '')), '')
        );
        v_secret_id := p_secret_id;
    else
        select vault.create_secret(
            p_secret,
            nullif(btrim(coalesce(p_name, '')), ''),
            nullif(btrim(coalesce(p_description, '')), '')
        )
        into v_secret_id;
    end if;

    return query select v_secret_id;
end;
$$;

create or replace function public.read_vault_secret(
    p_secret_id uuid
)
returns table(secret text)
language plpgsql
security definer
set search_path = public, vault
as $$
begin
    return query
    select decrypted_secret::text
    from vault.decrypted_secrets
    where id = p_secret_id
    limit 1;
end;
$$;

create or replace function public.delete_vault_secret(
    p_secret_id uuid
)
returns table(deleted boolean)
language plpgsql
security definer
set search_path = public, vault
as $$
declare
    v_deleted boolean := false;
begin
    delete from vault.secrets
    where id = p_secret_id;

    v_deleted := found;
    return query select v_deleted;
end;
$$;

revoke all on function public.upsert_vault_secret(text, uuid, text, text) from public, anon, authenticated;
revoke all on function public.read_vault_secret(uuid) from public, anon, authenticated;
revoke all on function public.delete_vault_secret(uuid) from public, anon, authenticated;

grant execute on function public.upsert_vault_secret(text, uuid, text, text) to service_role;
grant execute on function public.read_vault_secret(uuid) to service_role;
grant execute on function public.delete_vault_secret(uuid) to service_role;

alter table if exists public.bot_configs
    add column if not exists owner_user_id text not null default '',
    add column if not exists website_url text not null default '',
    add column if not exists knowledge_last_crawled_at timestamptz,
    add column if not exists default_template_variable_count integer not null default 0,
    add column if not exists lead_manager_page_name text not null default '',
    add column if not exists whatsapp_display_phone_number text not null default '',
    add column if not exists meta_business_id text not null default '',
    add column if not exists meta_business_name text not null default '',
    add column if not exists meta_waba_id text not null default '',
    add column if not exists meta_waba_name text not null default '';

create index if not exists idx_bot_configs_owner_user_id
    on public.bot_configs (owner_user_id, name, bot_id);

create table if not exists public.qualifier_meta_integrations (
    owner_user_id text primary key,
    meta_user_id text not null default '',
    meta_user_name text not null default '',
    access_token_secret_id uuid,
    token_expires_at timestamptz,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_qualifier_meta_integrations_expires_at
    on public.qualifier_meta_integrations (token_expires_at);

alter table if exists public.meta_page_subscriptions
    add column if not exists qualifier_bot_id text not null default '',
    add column if not exists qualifier_bot_name text not null default '',
    add column if not exists qualifier_bridge_secret_id uuid,
    add column if not exists qualifier_assigned_at timestamptz;

do $$
begin
    if exists (
        select 1
        from information_schema.tables
        where table_schema = 'public'
          and table_name = 'meta_page_subscriptions'
    ) then
        execute '
            create unique index if not exists idx_meta_page_subscriptions_qualifier_bot_id
            on public.meta_page_subscriptions (qualifier_bot_id)
            where qualifier_bot_id <> ''''''';
    end if;
end $$;

create or replace function public.assign_meta_page_qualifier(
    p_owner_user_id text,
    p_page_id text,
    p_bot_id text,
    p_bot_name text default null
)
returns table(
    page_id text,
    qualifier_bot_id text,
    qualifier_bot_name text,
    qualifier_bridge_secret_id uuid
)
language plpgsql
security definer
set search_path = public, vault
as $$
declare
    v_existing_secret_id uuid;
    v_secret_id uuid;
    v_secret_name text;
    v_secret_value text;
begin
    if coalesce(btrim(p_owner_user_id), '') = '' then
        raise exception 'owner_user_id is required.';
    end if;
    if coalesce(btrim(p_page_id), '') = '' then
        raise exception 'page_id is required.';
    end if;
    if coalesce(btrim(p_bot_id), '') = '' then
        raise exception 'bot_id is required.';
    end if;

    if not exists (
        select 1
        from public.bot_configs
        where bot_id = btrim(p_bot_id)
          and owner_user_id = btrim(p_owner_user_id)
    ) then
        raise exception 'Bot not found for owner.';
    end if;

    if not exists (
        select 1
        from public.meta_page_subscriptions
        where owner_user_id = btrim(p_owner_user_id)
          and page_id = btrim(p_page_id)
    ) then
        raise exception 'Page subscription not found for owner.';
    end if;

    update public.meta_page_subscriptions
    set qualifier_bot_id = '',
        qualifier_bot_name = '',
        qualifier_assigned_at = null
    where owner_user_id = btrim(p_owner_user_id)
      and qualifier_bot_id = btrim(p_bot_id)
      and page_id <> btrim(p_page_id);

    select qualifier_bridge_secret_id
    into v_existing_secret_id
    from public.meta_page_subscriptions
    where owner_user_id = btrim(p_owner_user_id)
      and page_id = btrim(p_page_id)
    limit 1;

    if v_existing_secret_id is not null then
        v_secret_id := v_existing_secret_id;
    else
        v_secret_name := format(
            'lead-bridge:%s:%s',
            btrim(p_owner_user_id),
            btrim(p_page_id)
        );
        v_secret_value := encode(gen_random_bytes(32), 'hex');
        select vault.create_secret(
            v_secret_value,
            v_secret_name,
            format('Lead bridge secret for owner %s page %s', btrim(p_owner_user_id), btrim(p_page_id))
        )
        into v_secret_id;
    end if;

    update public.meta_page_subscriptions
    set qualifier_bot_id = btrim(p_bot_id),
        qualifier_bot_name = coalesce(nullif(btrim(coalesce(p_bot_name, '')), ''), qualifier_bot_name),
        qualifier_bridge_secret_id = v_secret_id,
        qualifier_assigned_at = timezone('utc', now()),
        updated_at = timezone('utc', now())
    where owner_user_id = btrim(p_owner_user_id)
      and page_id = btrim(p_page_id);

    update public.bot_configs
    set lead_manager_page_id = btrim(p_page_id),
        lead_manager_page_name = coalesce(
            (
                select page_name
                from public.meta_page_subscriptions
                where owner_user_id = btrim(p_owner_user_id)
                  and page_id = btrim(p_page_id)
                limit 1
            ),
            lead_manager_page_name
        ),
        updated_at = timezone('utc', now())
    where bot_id = btrim(p_bot_id)
      and owner_user_id = btrim(p_owner_user_id);

    return query
    select
        mps.page_id,
        mps.qualifier_bot_id,
        mps.qualifier_bot_name,
        mps.qualifier_bridge_secret_id
    from public.meta_page_subscriptions mps
    where mps.owner_user_id = btrim(p_owner_user_id)
      and mps.page_id = btrim(p_page_id)
    limit 1;
end;
$$;

create or replace function public.clear_meta_page_qualifier(
    p_owner_user_id text,
    p_page_id text
)
returns table(
    page_id text,
    qualifier_bot_id text,
    qualifier_bot_name text,
    qualifier_bridge_secret_id uuid
)
language plpgsql
security definer
set search_path = public
as $$
declare
    v_previous_bot_id text;
begin
    if coalesce(btrim(p_owner_user_id), '') = '' then
        raise exception 'owner_user_id is required.';
    end if;
    if coalesce(btrim(p_page_id), '') = '' then
        raise exception 'page_id is required.';
    end if;

    select qualifier_bot_id
    into v_previous_bot_id
    from public.meta_page_subscriptions
    where owner_user_id = btrim(p_owner_user_id)
      and page_id = btrim(p_page_id)
    limit 1;

    update public.meta_page_subscriptions
    set qualifier_bot_id = '',
        qualifier_bot_name = '',
        qualifier_assigned_at = null,
        updated_at = timezone('utc', now())
    where owner_user_id = btrim(p_owner_user_id)
      and page_id = btrim(p_page_id);

    if coalesce(v_previous_bot_id, '') <> '' then
        update public.bot_configs
        set lead_manager_page_id = '',
            lead_manager_page_name = '',
            updated_at = timezone('utc', now())
        where owner_user_id = btrim(p_owner_user_id)
          and bot_id = btrim(v_previous_bot_id)
          and lead_manager_page_id = btrim(p_page_id);
    end if;

    return query
    select
        mps.page_id,
        mps.qualifier_bot_id,
        mps.qualifier_bot_name,
        mps.qualifier_bridge_secret_id
    from public.meta_page_subscriptions mps
    where mps.owner_user_id = btrim(p_owner_user_id)
      and mps.page_id = btrim(p_page_id)
    limit 1;
end;
$$;

revoke all on function public.assign_meta_page_qualifier(text, text, text, text) from public, anon, authenticated;
revoke all on function public.clear_meta_page_qualifier(text, text) from public, anon, authenticated;

grant execute on function public.assign_meta_page_qualifier(text, text, text, text) to service_role;
grant execute on function public.clear_meta_page_qualifier(text, text) to service_role;

create table if not exists public.bot_knowledge_chunks (
    id bigint generated always as identity primary key,
    owner_user_id text not null default '',
    bot_id text not null,
    source_url text not null default '',
    page_url text not null default '',
    page_title text not null default '',
    chunk_index integer not null default 0,
    chunk_text text not null default '',
    search_vector tsvector generated always as (
        to_tsvector(
            'simple',
            coalesce(page_title, '') || ' ' || coalesce(chunk_text, '')
        )
    ) stored,
    created_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_bot_knowledge_chunks_bot_id
    on public.bot_knowledge_chunks (bot_id, created_at desc);

create index if not exists idx_bot_knowledge_chunks_owner_bot
    on public.bot_knowledge_chunks (owner_user_id, bot_id);

create index if not exists idx_bot_knowledge_chunks_search_vector
    on public.bot_knowledge_chunks
    using gin (search_vector);
