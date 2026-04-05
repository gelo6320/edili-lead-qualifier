alter table if exists public.bot_configs
    add column if not exists default_template_id text not null default '',
    add column if not exists default_template_body_text text not null default '';
