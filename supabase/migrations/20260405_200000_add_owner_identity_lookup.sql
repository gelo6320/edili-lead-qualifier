create or replace function public.resolve_owner_user_ids_by_email(
  p_email text
)
returns table(owner_user_id uuid)
language sql
security definer
set search_path = auth, public
as $$
  select u.id as owner_user_id
  from auth.users u
  where lower(btrim(coalesce(u.email, ''))) = lower(btrim(coalesce(p_email, '')))
  order by u.created_at asc;
$$;

revoke all on function public.resolve_owner_user_ids_by_email(text) from public, anon, authenticated;
grant execute on function public.resolve_owner_user_ids_by_email(text) to service_role;
