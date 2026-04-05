create extension if not exists pgcrypto;
create extension if not exists supabase_vault with schema vault;

create table if not exists public.meta_page_subscriptions (
    id uuid primary key default gen_random_uuid(),
    owner_user_id text not null,
    page_id text not null unique,
    page_name text not null,
    page_access_token_secret_id uuid not null,
    is_active boolean not null default true,
    subscribed_at timestamptz not null default timezone('utc', now()),
    unsubscribed_at timestamptz,
    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now()),
    last_token_sync_at timestamptz not null default timezone('utc', now()),
    slack_webhook_secret_id uuid,
    notion_api_key_secret_id uuid,
    notion_data_source_id text,
    notion_status_name text,
    slack_bot_access_token_secret_id uuid,
    slack_refresh_token_secret_id uuid,
    slack_token_expires_at timestamptz,
    slack_team_id text,
    slack_team_name text,
    slack_channel_id text,
    slack_channel_name text,
    slack_channel_is_private boolean,
    notion_access_token_secret_id uuid,
    notion_refresh_token_secret_id uuid,
    notion_token_expires_at timestamptz,
    notion_workspace_id text,
    notion_workspace_name text,
    notion_workspace_icon text,
    notion_data_source_name text,
    notion_title_property_name text,
    notion_phone_property_name text,
    notion_email_property_name text,
    notion_form_property_name text,
    notion_status_property_name text,
    notion_status_property_type text,
    qualifier_bot_id text not null default '',
    qualifier_bot_name text not null default '',
    qualifier_bridge_secret_id uuid,
    qualifier_assigned_at timestamptz
);

create index if not exists idx_meta_page_subscriptions_owner_user_id
    on public.meta_page_subscriptions (owner_user_id);

create index if not exists idx_meta_page_subscriptions_is_active
    on public.meta_page_subscriptions (is_active);

create unique index if not exists idx_meta_page_subscriptions_qualifier_bot_id
    on public.meta_page_subscriptions (qualifier_bot_id)
    where qualifier_bot_id <> '';

create or replace function public.touch_meta_page_subscriptions_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at := timezone('utc', now());
    return new;
end;
$$;

drop trigger if exists trg_meta_page_subscriptions_set_updated_at on public.meta_page_subscriptions;

create trigger trg_meta_page_subscriptions_set_updated_at
before update on public.meta_page_subscriptions
for each row
execute function public.touch_meta_page_subscriptions_updated_at();

alter table public.meta_page_subscriptions enable row level security;

grant select, update on public.meta_page_subscriptions to authenticated;

do $$
begin
    if not exists (
        select 1
        from pg_policies
        where schemaname = 'public'
          and tablename = 'meta_page_subscriptions'
          and policyname = 'Users can view own page subscriptions'
    ) then
        create policy "Users can view own page subscriptions"
            on public.meta_page_subscriptions
            for select
            to authenticated
            using (owner_user_id = auth.uid()::text);
    end if;
end $$;

do $$
begin
    if not exists (
        select 1
        from pg_policies
        where schemaname = 'public'
          and tablename = 'meta_page_subscriptions'
          and policyname = 'Users can update own page subscriptions'
    ) then
        create policy "Users can update own page subscriptions"
            on public.meta_page_subscriptions
            for update
            to authenticated
            using (owner_user_id = auth.uid()::text)
            with check (owner_user_id = auth.uid()::text);
    end if;
end $$;

create or replace function public.upsert_meta_page_subscription_config(
    p_owner_user_id text,
    p_page_id text,
    p_page_name text default null,
    p_page_access_token text default null,
    p_slack_webhook_url text default null,
    p_notion_api_key text default null,
    p_notion_data_source_id text default null,
    p_notion_status_name text default null
)
returns public.meta_page_subscriptions
language plpgsql
security definer
set search_path = public, vault
as $$
declare
    v_owner_user_id text := nullif(btrim(p_owner_user_id), '');
    v_page_id text := nullif(btrim(p_page_id), '');
    v_page_name text := coalesce(nullif(btrim(coalesce(p_page_name, '')), ''), nullif(btrim(coalesce(p_page_id, '')), ''));
    v_page_access_token text := nullif(btrim(coalesce(p_page_access_token, '')), '');
    v_slack_webhook_url text := nullif(btrim(coalesce(p_slack_webhook_url, '')), '');
    v_notion_api_key text := nullif(btrim(coalesce(p_notion_api_key, '')), '');
    v_notion_data_source_id text := nullif(btrim(coalesce(p_notion_data_source_id, '')), '');
    v_notion_status_name text := nullif(btrim(coalesce(p_notion_status_name, '')), '');
    v_existing public.meta_page_subscriptions%rowtype;
    v_result public.meta_page_subscriptions%rowtype;
    v_page_token_secret_id uuid;
    v_slack_webhook_secret_id uuid;
    v_notion_api_key_secret_id uuid;
    v_has_existing boolean := false;
begin
    if v_owner_user_id is null then
        raise exception 'owner_user_id is required';
    end if;
    if v_page_id is null then
        raise exception 'page_id is required';
    end if;

    select *
    into v_existing
    from public.meta_page_subscriptions mps
    where mps.page_id = v_page_id
    for update;

    v_has_existing := found;

    if v_has_existing and v_existing.owner_user_id is distinct from v_owner_user_id then
        raise exception 'page subscription belongs to another user';
    end if;

    v_page_token_secret_id := v_existing.page_access_token_secret_id;
    if v_page_access_token is not null then
        select secret_id
        into v_page_token_secret_id
        from public.upsert_vault_secret(
            v_page_access_token,
            v_page_token_secret_id,
            format('meta-page-token-%s', v_page_id),
            format('Facebook page access token for page %s', v_page_id)
        );
    end if;

    v_slack_webhook_secret_id := v_existing.slack_webhook_secret_id;
    if v_slack_webhook_url is not null then
        select secret_id
        into v_slack_webhook_secret_id
        from public.upsert_vault_secret(
            v_slack_webhook_url,
            v_slack_webhook_secret_id,
            format('meta-page-slack-webhook-%s', v_page_id),
            format('Slack webhook URL for page %s', v_page_id)
        );
    end if;

    v_notion_api_key_secret_id := v_existing.notion_api_key_secret_id;
    if v_notion_api_key is not null then
        select secret_id
        into v_notion_api_key_secret_id
        from public.upsert_vault_secret(
            v_notion_api_key,
            v_notion_api_key_secret_id,
            format('meta-page-notion-api-key-%s', v_page_id),
            format('Notion API key for page %s', v_page_id)
        );
    end if;

    if v_has_existing then
        update public.meta_page_subscriptions mps
        set owner_user_id = v_owner_user_id,
            page_name = coalesce(v_page_name, v_existing.page_name, v_page_id),
            page_access_token_secret_id = coalesce(v_page_token_secret_id, v_existing.page_access_token_secret_id),
            slack_webhook_secret_id = coalesce(v_slack_webhook_secret_id, v_existing.slack_webhook_secret_id),
            notion_api_key_secret_id = coalesce(v_notion_api_key_secret_id, v_existing.notion_api_key_secret_id),
            notion_data_source_id = coalesce(v_notion_data_source_id, v_existing.notion_data_source_id),
            notion_status_name = coalesce(v_notion_status_name, v_existing.notion_status_name),
            last_token_sync_at = case
                when v_page_access_token is not null then timezone('utc', now())
                else v_existing.last_token_sync_at
            end
        where mps.id = v_existing.id
        returning * into v_result;

        return v_result;
    end if;

    if v_page_token_secret_id is null then
        raise exception 'page_access_token is required';
    end if;

    insert into public.meta_page_subscriptions (
        owner_user_id,
        page_id,
        page_name,
        page_access_token_secret_id,
        is_active,
        subscribed_at,
        unsubscribed_at,
        last_token_sync_at,
        slack_webhook_secret_id,
        notion_api_key_secret_id,
        notion_data_source_id,
        notion_status_name
    )
    values (
        v_owner_user_id,
        v_page_id,
        coalesce(v_page_name, v_page_id),
        v_page_token_secret_id,
        false,
        timezone('utc', now()),
        timezone('utc', now()),
        timezone('utc', now()),
        v_slack_webhook_secret_id,
        v_notion_api_key_secret_id,
        v_notion_data_source_id,
        v_notion_status_name
    )
    returning * into v_result;

    return v_result;
end;
$$;

create or replace function public.upsert_meta_page_subscription(
    p_owner_user_id text,
    p_page_id text,
    p_page_name text,
    p_page_access_token text,
    p_slack_webhook_url text default null,
    p_notion_api_key text default null,
    p_notion_data_source_id text default null,
    p_notion_status_name text default null
)
returns public.meta_page_subscriptions
language plpgsql
security definer
set search_path = public, vault
as $$
declare
    v_page_access_token text := nullif(btrim(coalesce(p_page_access_token, '')), '');
    v_result public.meta_page_subscriptions%rowtype;
begin
    if v_page_access_token is null then
        raise exception 'page_access_token is required';
    end if;

    select *
    into v_result
    from public.upsert_meta_page_subscription_config(
        p_owner_user_id,
        p_page_id,
        p_page_name,
        v_page_access_token,
        p_slack_webhook_url,
        p_notion_api_key,
        p_notion_data_source_id,
        p_notion_status_name
    );

    update public.meta_page_subscriptions mps
    set is_active = true,
        subscribed_at = timezone('utc', now()),
        unsubscribed_at = null,
        last_token_sync_at = timezone('utc', now())
    where mps.id = v_result.id
    returning * into v_result;

    return v_result;
end;
$$;

create or replace function public.upsert_meta_page_subscription_slack_oauth(
    p_owner_user_id text,
    p_page_id text,
    p_page_name text default null,
    p_page_access_token text default null,
    p_slack_bot_access_token text default null,
    p_slack_refresh_token text default null,
    p_slack_token_expires_at text default null,
    p_slack_team_id text default null,
    p_slack_team_name text default null
)
returns public.meta_page_subscriptions
language plpgsql
security definer
set search_path = public, vault
as $$
declare
    v_page_id text := nullif(btrim(coalesce(p_page_id, '')), '');
    v_page_name text := coalesce(nullif(btrim(coalesce(p_page_name, '')), ''), v_page_id);
    v_page_access_token text := nullif(btrim(coalesce(p_page_access_token, '')), '');
    v_slack_bot_access_token text := nullif(btrim(coalesce(p_slack_bot_access_token, '')), '');
    v_slack_refresh_token text := nullif(btrim(coalesce(p_slack_refresh_token, '')), '');
    v_slack_token_expires_at timestamptz := nullif(btrim(coalesce(p_slack_token_expires_at, '')), '')::timestamptz;
    v_slack_team_id text := nullif(btrim(coalesce(p_slack_team_id, '')), '');
    v_slack_team_name text := nullif(btrim(coalesce(p_slack_team_name, '')), '');
    v_existing public.meta_page_subscriptions%rowtype;
    v_result public.meta_page_subscriptions%rowtype;
    v_slack_bot_access_token_secret_id uuid;
    v_slack_refresh_token_secret_id uuid;
begin
    if v_slack_bot_access_token is null then
        raise exception 'slack_bot_access_token is required';
    end if;

    select *
    into v_result
    from public.upsert_meta_page_subscription_config(
        p_owner_user_id,
        v_page_id,
        v_page_name,
        v_page_access_token,
        null,
        null,
        null,
        null
    );

    select *
    into v_existing
    from public.meta_page_subscriptions mps
    where mps.id = v_result.id
    for update;

    select secret_id
    into v_slack_bot_access_token_secret_id
    from public.upsert_vault_secret(
        v_slack_bot_access_token,
        v_existing.slack_bot_access_token_secret_id,
        format('meta-page-slack-bot-token-%s', v_page_id),
        format('Slack bot token for page %s', v_page_id)
    );

    v_slack_refresh_token_secret_id := v_existing.slack_refresh_token_secret_id;
    if v_slack_refresh_token is not null then
        select secret_id
        into v_slack_refresh_token_secret_id
        from public.upsert_vault_secret(
            v_slack_refresh_token,
            v_slack_refresh_token_secret_id,
            format('meta-page-slack-refresh-token-%s', v_page_id),
            format('Slack refresh token for page %s', v_page_id)
        );
    end if;

    update public.meta_page_subscriptions mps
    set slack_bot_access_token_secret_id = v_slack_bot_access_token_secret_id,
        slack_refresh_token_secret_id = coalesce(v_slack_refresh_token_secret_id, v_existing.slack_refresh_token_secret_id),
        slack_token_expires_at = coalesce(v_slack_token_expires_at, v_existing.slack_token_expires_at),
        slack_team_id = coalesce(v_slack_team_id, v_existing.slack_team_id),
        slack_team_name = coalesce(v_slack_team_name, v_existing.slack_team_name)
    where mps.id = v_existing.id
    returning * into v_result;

    return v_result;
end;
$$;

create or replace function public.update_meta_page_subscription_slack_channel(
    p_owner_user_id text,
    p_page_id text,
    p_slack_channel_id text,
    p_slack_channel_name text default null,
    p_slack_channel_is_private boolean default null
)
returns public.meta_page_subscriptions
language plpgsql
security definer
set search_path = public, vault
as $$
declare
    v_owner_user_id text := nullif(btrim(coalesce(p_owner_user_id, '')), '');
    v_page_id text := nullif(btrim(coalesce(p_page_id, '')), '');
    v_slack_channel_id text := nullif(btrim(coalesce(p_slack_channel_id, '')), '');
    v_slack_channel_name text := nullif(btrim(coalesce(p_slack_channel_name, '')), '');
    v_existing public.meta_page_subscriptions%rowtype;
    v_result public.meta_page_subscriptions%rowtype;
begin
    if v_owner_user_id is null then
        raise exception 'owner_user_id is required';
    end if;
    if v_page_id is null then
        raise exception 'page_id is required';
    end if;
    if v_slack_channel_id is null then
        raise exception 'slack_channel_id is required';
    end if;

    select *
    into v_existing
    from public.meta_page_subscriptions mps
    where mps.owner_user_id = v_owner_user_id
      and mps.page_id = v_page_id
    for update;

    if not found then
        raise exception 'page config not found';
    end if;

    update public.meta_page_subscriptions mps
    set slack_channel_id = v_slack_channel_id,
        slack_channel_name = coalesce(v_slack_channel_name, v_existing.slack_channel_name, v_slack_channel_id),
        slack_channel_is_private = coalesce(p_slack_channel_is_private, v_existing.slack_channel_is_private)
    where mps.id = v_existing.id
    returning * into v_result;

    return v_result;
end;
$$;

create or replace function public.upsert_meta_page_subscription_notion_oauth(
    p_owner_user_id text,
    p_page_id text,
    p_page_name text default null,
    p_page_access_token text default null,
    p_notion_access_token text default null,
    p_notion_refresh_token text default null,
    p_notion_token_expires_at text default null,
    p_notion_workspace_id text default null,
    p_notion_workspace_name text default null,
    p_notion_workspace_icon text default null
)
returns public.meta_page_subscriptions
language plpgsql
security definer
set search_path = public, vault
as $$
declare
    v_page_id text := nullif(btrim(coalesce(p_page_id, '')), '');
    v_page_name text := coalesce(nullif(btrim(coalesce(p_page_name, '')), ''), v_page_id);
    v_page_access_token text := nullif(btrim(coalesce(p_page_access_token, '')), '');
    v_notion_access_token text := nullif(btrim(coalesce(p_notion_access_token, '')), '');
    v_notion_refresh_token text := nullif(btrim(coalesce(p_notion_refresh_token, '')), '');
    v_notion_token_expires_at timestamptz := nullif(btrim(coalesce(p_notion_token_expires_at, '')), '')::timestamptz;
    v_notion_workspace_id text := nullif(btrim(coalesce(p_notion_workspace_id, '')), '');
    v_notion_workspace_name text := nullif(btrim(coalesce(p_notion_workspace_name, '')), '');
    v_notion_workspace_icon text := nullif(btrim(coalesce(p_notion_workspace_icon, '')), '');
    v_existing public.meta_page_subscriptions%rowtype;
    v_result public.meta_page_subscriptions%rowtype;
    v_notion_access_token_secret_id uuid;
    v_notion_refresh_token_secret_id uuid;
begin
    if v_notion_access_token is null then
        raise exception 'notion_access_token is required';
    end if;

    select *
    into v_result
    from public.upsert_meta_page_subscription_config(
        p_owner_user_id,
        v_page_id,
        v_page_name,
        v_page_access_token,
        null,
        null,
        null,
        null
    );

    select *
    into v_existing
    from public.meta_page_subscriptions mps
    where mps.id = v_result.id
    for update;

    select secret_id
    into v_notion_access_token_secret_id
    from public.upsert_vault_secret(
        v_notion_access_token,
        v_existing.notion_access_token_secret_id,
        format('meta-page-notion-access-token-%s', v_page_id),
        format('Notion access token for page %s', v_page_id)
    );

    v_notion_refresh_token_secret_id := v_existing.notion_refresh_token_secret_id;
    if v_notion_refresh_token is not null then
        select secret_id
        into v_notion_refresh_token_secret_id
        from public.upsert_vault_secret(
            v_notion_refresh_token,
            v_notion_refresh_token_secret_id,
            format('meta-page-notion-refresh-token-%s', v_page_id),
            format('Notion refresh token for page %s', v_page_id)
        );
    end if;

    update public.meta_page_subscriptions mps
    set notion_access_token_secret_id = v_notion_access_token_secret_id,
        notion_refresh_token_secret_id = coalesce(v_notion_refresh_token_secret_id, v_existing.notion_refresh_token_secret_id),
        notion_token_expires_at = coalesce(v_notion_token_expires_at, v_existing.notion_token_expires_at),
        notion_workspace_id = coalesce(v_notion_workspace_id, v_existing.notion_workspace_id),
        notion_workspace_name = coalesce(v_notion_workspace_name, v_existing.notion_workspace_name),
        notion_workspace_icon = coalesce(v_notion_workspace_icon, v_existing.notion_workspace_icon)
    where mps.id = v_existing.id
    returning * into v_result;

    return v_result;
end;
$$;

create or replace function public.update_meta_page_subscription_notion_target(
    p_owner_user_id text,
    p_page_id text,
    p_notion_data_source_id text,
    p_notion_data_source_name text default null,
    p_notion_title_property_name text default null,
    p_notion_phone_property_name text default null,
    p_notion_email_property_name text default null,
    p_notion_form_property_name text default null,
    p_notion_status_property_name text default null,
    p_notion_status_property_type text default null,
    p_notion_status_name text default null
)
returns public.meta_page_subscriptions
language plpgsql
security definer
set search_path = public, vault
as $$
declare
    v_owner_user_id text := nullif(btrim(coalesce(p_owner_user_id, '')), '');
    v_page_id text := nullif(btrim(coalesce(p_page_id, '')), '');
    v_notion_data_source_id text := nullif(btrim(coalesce(p_notion_data_source_id, '')), '');
    v_existing public.meta_page_subscriptions%rowtype;
    v_result public.meta_page_subscriptions%rowtype;
begin
    if v_owner_user_id is null then
        raise exception 'owner_user_id is required';
    end if;
    if v_page_id is null then
        raise exception 'page_id is required';
    end if;
    if v_notion_data_source_id is null then
        raise exception 'notion_data_source_id is required';
    end if;

    select *
    into v_existing
    from public.meta_page_subscriptions mps
    where mps.owner_user_id = v_owner_user_id
      and mps.page_id = v_page_id
    for update;

    if not found then
        raise exception 'page config not found';
    end if;

    update public.meta_page_subscriptions mps
    set notion_data_source_id = v_notion_data_source_id,
        notion_data_source_name = coalesce(nullif(btrim(coalesce(p_notion_data_source_name, '')), ''), v_existing.notion_data_source_name, v_notion_data_source_id),
        notion_title_property_name = coalesce(nullif(btrim(coalesce(p_notion_title_property_name, '')), ''), v_existing.notion_title_property_name),
        notion_phone_property_name = coalesce(nullif(btrim(coalesce(p_notion_phone_property_name, '')), ''), v_existing.notion_phone_property_name),
        notion_email_property_name = coalesce(nullif(btrim(coalesce(p_notion_email_property_name, '')), ''), v_existing.notion_email_property_name),
        notion_form_property_name = coalesce(nullif(btrim(coalesce(p_notion_form_property_name, '')), ''), v_existing.notion_form_property_name),
        notion_status_property_name = coalesce(nullif(btrim(coalesce(p_notion_status_property_name, '')), ''), v_existing.notion_status_property_name),
        notion_status_property_type = coalesce(nullif(btrim(coalesce(p_notion_status_property_type, '')), ''), v_existing.notion_status_property_type),
        notion_status_name = coalesce(nullif(btrim(coalesce(p_notion_status_name, '')), ''), v_existing.notion_status_name)
    where mps.id = v_existing.id
    returning * into v_result;

    return v_result;
end;
$$;

create or replace function public.get_meta_page_subscription_runtime(
    p_page_id text
)
returns table(
    id uuid,
    owner_user_id text,
    page_id text,
    page_name text,
    is_active boolean,
    page_access_token text,
    slack_webhook_url text,
    slack_bot_access_token text,
    slack_refresh_token text,
    slack_team_id text,
    slack_team_name text,
    slack_channel_id text,
    slack_channel_name text,
    slack_channel_is_private boolean,
    slack_token_expires_at timestamptz,
    notion_api_key text,
    notion_access_token text,
    notion_refresh_token text,
    notion_workspace_id text,
    notion_workspace_name text,
    notion_workspace_icon text,
    notion_token_expires_at timestamptz,
    notion_data_source_id text,
    notion_data_source_name text,
    notion_title_property_name text,
    notion_phone_property_name text,
    notion_email_property_name text,
    notion_form_property_name text,
    notion_status_property_name text,
    notion_status_property_type text,
    notion_status_name text
)
language sql
security definer
set search_path = public, vault
as $$
    select
        mps.id,
        mps.owner_user_id,
        mps.page_id,
        mps.page_name,
        mps.is_active,
        page_token.decrypted_secret as page_access_token,
        slack_webhook_secret.decrypted_secret as slack_webhook_url,
        slack_bot_token.decrypted_secret as slack_bot_access_token,
        slack_refresh_token.decrypted_secret as slack_refresh_token,
        mps.slack_team_id,
        mps.slack_team_name,
        mps.slack_channel_id,
        mps.slack_channel_name,
        mps.slack_channel_is_private,
        mps.slack_token_expires_at,
        notion_api_key_secret.decrypted_secret as notion_api_key,
        notion_access_token_secret.decrypted_secret as notion_access_token,
        notion_refresh_token_secret.decrypted_secret as notion_refresh_token,
        mps.notion_workspace_id,
        mps.notion_workspace_name,
        mps.notion_workspace_icon,
        mps.notion_token_expires_at,
        mps.notion_data_source_id,
        mps.notion_data_source_name,
        mps.notion_title_property_name,
        mps.notion_phone_property_name,
        mps.notion_email_property_name,
        mps.notion_form_property_name,
        mps.notion_status_property_name,
        mps.notion_status_property_type,
        mps.notion_status_name
    from public.meta_page_subscriptions mps
    left join vault.decrypted_secrets page_token
        on page_token.id = mps.page_access_token_secret_id
    left join vault.decrypted_secrets slack_webhook_secret
        on slack_webhook_secret.id = mps.slack_webhook_secret_id
    left join vault.decrypted_secrets slack_bot_token
        on slack_bot_token.id = mps.slack_bot_access_token_secret_id
    left join vault.decrypted_secrets slack_refresh_token
        on slack_refresh_token.id = mps.slack_refresh_token_secret_id
    left join vault.decrypted_secrets notion_api_key_secret
        on notion_api_key_secret.id = mps.notion_api_key_secret_id
    left join vault.decrypted_secrets notion_access_token_secret
        on notion_access_token_secret.id = mps.notion_access_token_secret_id
    left join vault.decrypted_secrets notion_refresh_token_secret
        on notion_refresh_token_secret.id = mps.notion_refresh_token_secret_id
    where mps.page_id = nullif(btrim(coalesce(p_page_id, '')), '')
      and mps.is_active = true
    limit 1;
$$;

create or replace function public.get_meta_page_subscription_runtime_for_owner(
    p_owner_user_id text,
    p_page_id text
)
returns table(
    id uuid,
    owner_user_id text,
    page_id text,
    page_name text,
    is_active boolean,
    page_access_token text,
    slack_webhook_url text,
    slack_bot_access_token text,
    slack_refresh_token text,
    slack_team_id text,
    slack_team_name text,
    slack_channel_id text,
    slack_channel_name text,
    slack_channel_is_private boolean,
    slack_token_expires_at timestamptz,
    notion_api_key text,
    notion_access_token text,
    notion_refresh_token text,
    notion_workspace_id text,
    notion_workspace_name text,
    notion_workspace_icon text,
    notion_token_expires_at timestamptz,
    notion_data_source_id text,
    notion_data_source_name text,
    notion_title_property_name text,
    notion_phone_property_name text,
    notion_email_property_name text,
    notion_form_property_name text,
    notion_status_property_name text,
    notion_status_property_type text,
    notion_status_name text
)
language sql
security definer
set search_path = public, vault
as $$
    select
        mps.id,
        mps.owner_user_id,
        mps.page_id,
        mps.page_name,
        mps.is_active,
        page_token.decrypted_secret as page_access_token,
        slack_webhook_secret.decrypted_secret as slack_webhook_url,
        slack_bot_token.decrypted_secret as slack_bot_access_token,
        slack_refresh_token.decrypted_secret as slack_refresh_token,
        mps.slack_team_id,
        mps.slack_team_name,
        mps.slack_channel_id,
        mps.slack_channel_name,
        mps.slack_channel_is_private,
        mps.slack_token_expires_at,
        notion_api_key_secret.decrypted_secret as notion_api_key,
        notion_access_token_secret.decrypted_secret as notion_access_token,
        notion_refresh_token_secret.decrypted_secret as notion_refresh_token,
        mps.notion_workspace_id,
        mps.notion_workspace_name,
        mps.notion_workspace_icon,
        mps.notion_token_expires_at,
        mps.notion_data_source_id,
        mps.notion_data_source_name,
        mps.notion_title_property_name,
        mps.notion_phone_property_name,
        mps.notion_email_property_name,
        mps.notion_form_property_name,
        mps.notion_status_property_name,
        mps.notion_status_property_type,
        mps.notion_status_name
    from public.meta_page_subscriptions mps
    left join vault.decrypted_secrets page_token
        on page_token.id = mps.page_access_token_secret_id
    left join vault.decrypted_secrets slack_webhook_secret
        on slack_webhook_secret.id = mps.slack_webhook_secret_id
    left join vault.decrypted_secrets slack_bot_token
        on slack_bot_token.id = mps.slack_bot_access_token_secret_id
    left join vault.decrypted_secrets slack_refresh_token
        on slack_refresh_token.id = mps.slack_refresh_token_secret_id
    left join vault.decrypted_secrets notion_api_key_secret
        on notion_api_key_secret.id = mps.notion_api_key_secret_id
    left join vault.decrypted_secrets notion_access_token_secret
        on notion_access_token_secret.id = mps.notion_access_token_secret_id
    left join vault.decrypted_secrets notion_refresh_token_secret
        on notion_refresh_token_secret.id = mps.notion_refresh_token_secret_id
    where mps.owner_user_id = nullif(btrim(coalesce(p_owner_user_id, '')), '')
      and mps.page_id = nullif(btrim(coalesce(p_page_id, '')), '')
    limit 1;
$$;

create or replace function public.get_meta_page_subscription_config(
    p_owner_user_id text,
    p_page_id text
)
returns table(
    id uuid,
    page_id text,
    page_name text,
    is_active boolean,
    subscribed_at timestamptz,
    unsubscribed_at timestamptz,
    updated_at timestamptz,
    last_token_sync_at timestamptz,
    slack_team_id text,
    slack_team_name text,
    slack_channel_id text,
    slack_channel_name text,
    slack_channel_is_private boolean,
    slack_token_expires_at timestamptz,
    notion_workspace_id text,
    notion_workspace_name text,
    notion_workspace_icon text,
    notion_token_expires_at timestamptz,
    notion_data_source_id text,
    notion_data_source_name text,
    notion_title_property_name text,
    notion_phone_property_name text,
    notion_email_property_name text,
    notion_form_property_name text,
    notion_status_property_name text,
    notion_status_property_type text,
    notion_status_name text,
    qualifier_bot_id text,
    qualifier_bot_name text,
    qualifier_bridge_secret_id uuid,
    slack_webhook_secret_id uuid,
    notion_api_key_secret_id uuid,
    slack_bot_access_token_secret_id uuid,
    notion_access_token_secret_id uuid
)
language sql
security definer
set search_path = public, vault
as $$
    select
        mps.id,
        mps.page_id,
        mps.page_name,
        mps.is_active,
        mps.subscribed_at,
        mps.unsubscribed_at,
        mps.updated_at,
        mps.last_token_sync_at,
        mps.slack_team_id,
        mps.slack_team_name,
        mps.slack_channel_id,
        mps.slack_channel_name,
        mps.slack_channel_is_private,
        mps.slack_token_expires_at,
        mps.notion_workspace_id,
        mps.notion_workspace_name,
        mps.notion_workspace_icon,
        mps.notion_token_expires_at,
        mps.notion_data_source_id,
        mps.notion_data_source_name,
        mps.notion_title_property_name,
        mps.notion_phone_property_name,
        mps.notion_email_property_name,
        mps.notion_form_property_name,
        mps.notion_status_property_name,
        mps.notion_status_property_type,
        mps.notion_status_name,
        mps.qualifier_bot_id,
        mps.qualifier_bot_name,
        mps.qualifier_bridge_secret_id,
        mps.slack_webhook_secret_id,
        mps.notion_api_key_secret_id,
        mps.slack_bot_access_token_secret_id,
        mps.notion_access_token_secret_id
    from public.meta_page_subscriptions mps
    where mps.owner_user_id = nullif(btrim(coalesce(p_owner_user_id, '')), '')
      and mps.page_id = nullif(btrim(coalesce(p_page_id, '')), '')
    limit 1;
$$;

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
    v_owner_user_id text := nullif(btrim(coalesce(p_owner_user_id, '')), '');
    v_page_id text := nullif(btrim(coalesce(p_page_id, '')), '');
    v_bot_id text := nullif(btrim(coalesce(p_bot_id, '')), '');
    v_bot_name text := nullif(btrim(coalesce(p_bot_name, '')), '');
    v_existing public.meta_page_subscriptions%rowtype;
    v_secret_id uuid;
begin
    if v_owner_user_id is null then
        raise exception 'owner_user_id is required.';
    end if;
    if v_page_id is null then
        raise exception 'page_id is required.';
    end if;
    if v_bot_id is null then
        raise exception 'bot_id is required.';
    end if;

    if not exists (
        select 1
        from public.bot_configs bc
        where bc.bot_id = v_bot_id
          and bc.owner_user_id = v_owner_user_id
    ) then
        raise exception 'Bot not found for owner.';
    end if;

    select *
    into v_existing
    from public.meta_page_subscriptions mps
    where mps.owner_user_id = v_owner_user_id
      and mps.page_id = v_page_id
    for update;

    if not found then
        raise exception 'Page subscription not found for owner.';
    end if;

    update public.meta_page_subscriptions mps
    set qualifier_bot_id = '',
        qualifier_bot_name = '',
        qualifier_assigned_at = null
    where mps.owner_user_id = v_owner_user_id
      and mps.qualifier_bot_id = v_bot_id
      and mps.page_id <> v_page_id;

    if coalesce(v_existing.qualifier_bot_id, '') <> ''
       and v_existing.qualifier_bot_id <> v_bot_id then
        update public.bot_configs bc
        set lead_manager_page_id = '',
            lead_manager_page_name = '',
            updated_at = timezone('utc', now())
        where bc.owner_user_id = v_owner_user_id
          and bc.bot_id = v_existing.qualifier_bot_id
          and bc.lead_manager_page_id = v_page_id;
    end if;

    if v_existing.qualifier_bridge_secret_id is not null then
        v_secret_id := v_existing.qualifier_bridge_secret_id;
    else
        select secret_id
        into v_secret_id
        from public.upsert_vault_secret(
            encode(extensions.gen_random_bytes(32), 'hex'),
            null,
            format('lead-bridge:%s:%s', v_owner_user_id, v_page_id),
            format('Lead bridge secret for owner %s page %s', v_owner_user_id, v_page_id)
        );
    end if;

    update public.meta_page_subscriptions mps
    set qualifier_bot_id = v_bot_id,
        qualifier_bot_name = coalesce(v_bot_name, nullif(mps.qualifier_bot_name, ''), v_bot_id),
        qualifier_bridge_secret_id = v_secret_id,
        qualifier_assigned_at = timezone('utc', now())
    where mps.id = v_existing.id;

    update public.bot_configs bc
    set lead_manager_page_id = v_page_id,
        lead_manager_page_name = coalesce(nullif(v_existing.page_name, ''), bc.lead_manager_page_name, v_page_id),
        updated_at = timezone('utc', now())
    where bc.bot_id = v_bot_id
      and bc.owner_user_id = v_owner_user_id;

    return query
    select
        mps.page_id,
        mps.qualifier_bot_id,
        mps.qualifier_bot_name,
        mps.qualifier_bridge_secret_id
    from public.meta_page_subscriptions mps
    where mps.id = v_existing.id
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
    v_owner_user_id text := nullif(btrim(coalesce(p_owner_user_id, '')), '');
    v_page_id text := nullif(btrim(coalesce(p_page_id, '')), '');
    v_previous_bot_id text;
    v_result public.meta_page_subscriptions%rowtype;
begin
    if v_owner_user_id is null then
        raise exception 'owner_user_id is required.';
    end if;
    if v_page_id is null then
        raise exception 'page_id is required.';
    end if;

    select mps.qualifier_bot_id
    into v_previous_bot_id
    from public.meta_page_subscriptions mps
    where mps.owner_user_id = v_owner_user_id
      and mps.page_id = v_page_id
    limit 1;

    update public.meta_page_subscriptions mps
    set qualifier_bot_id = '',
        qualifier_bot_name = '',
        qualifier_assigned_at = null
    where mps.owner_user_id = v_owner_user_id
      and mps.page_id = v_page_id
    returning * into v_result;

    if coalesce(v_previous_bot_id, '') <> '' then
        update public.bot_configs bc
        set lead_manager_page_id = '',
            lead_manager_page_name = '',
            updated_at = timezone('utc', now())
        where bc.owner_user_id = v_owner_user_id
          and bc.bot_id = v_previous_bot_id
          and bc.lead_manager_page_id = v_page_id;
    end if;

    if v_result.id is null then
        return;
    end if;

    return query
    select
        v_result.page_id,
        v_result.qualifier_bot_id,
        v_result.qualifier_bot_name,
        v_result.qualifier_bridge_secret_id;
end;
$$;

revoke all on function public.upsert_meta_page_subscription_config(text, text, text, text, text, text, text, text) from public, anon, authenticated;
revoke all on function public.upsert_meta_page_subscription(text, text, text, text, text, text, text, text) from public, anon, authenticated;
revoke all on function public.upsert_meta_page_subscription_slack_oauth(text, text, text, text, text, text, text, text, text) from public, anon, authenticated;
revoke all on function public.update_meta_page_subscription_slack_channel(text, text, text, text, boolean) from public, anon, authenticated;
revoke all on function public.upsert_meta_page_subscription_notion_oauth(text, text, text, text, text, text, text, text, text, text) from public, anon, authenticated;
revoke all on function public.update_meta_page_subscription_notion_target(text, text, text, text, text, text, text, text, text, text, text) from public, anon, authenticated;
revoke all on function public.get_meta_page_subscription_runtime(text) from public, anon, authenticated;
revoke all on function public.get_meta_page_subscription_runtime_for_owner(text, text) from public, anon, authenticated;
revoke all on function public.get_meta_page_subscription_config(text, text) from public, anon, authenticated;
revoke all on function public.assign_meta_page_qualifier(text, text, text, text) from public, anon, authenticated;
revoke all on function public.clear_meta_page_qualifier(text, text) from public, anon, authenticated;

grant execute on function public.upsert_meta_page_subscription_config(text, text, text, text, text, text, text, text) to service_role;
grant execute on function public.upsert_meta_page_subscription(text, text, text, text, text, text, text, text) to service_role;
grant execute on function public.upsert_meta_page_subscription_slack_oauth(text, text, text, text, text, text, text, text, text) to service_role;
grant execute on function public.update_meta_page_subscription_slack_channel(text, text, text, text, boolean) to service_role;
grant execute on function public.upsert_meta_page_subscription_notion_oauth(text, text, text, text, text, text, text, text, text, text) to service_role;
grant execute on function public.update_meta_page_subscription_notion_target(text, text, text, text, text, text, text, text, text, text, text) to service_role;
grant execute on function public.get_meta_page_subscription_runtime(text) to service_role;
grant execute on function public.get_meta_page_subscription_runtime_for_owner(text, text) to service_role;
grant execute on function public.get_meta_page_subscription_config(text, text) to service_role;
grant execute on function public.assign_meta_page_qualifier(text, text, text, text) to service_role;
grant execute on function public.clear_meta_page_qualifier(text, text) to service_role;
