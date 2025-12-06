-- Create session_locks table to manage active client sessions
create table if not exists public.session_locks (
    session_id text not null primary key,
    device_id text not null,
    last_active_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable RLS (even if we allow all for now)
alter table public.session_locks enable row level security;

-- Policies
create policy "Enable read access for all users" on public.session_locks for select using (true);
create policy "Enable insert access for all users" on public.session_locks for insert with check (true);
create policy "Enable update access for all users" on public.session_locks for update using (true);
create policy "Enable delete access for all users" on public.session_locks for delete using (true);

-- Function to refresh (acquire/keep) the lock
create or replace function public.refresh_session_lock(p_session_id text, p_device_id text)
returns void as $$
begin
    insert into public.session_locks (session_id, device_id, last_active_at)
    values (p_session_id, p_device_id, now())
    on conflict (session_id) 
    do update set 
        last_active_at = now(),
        device_id = p_device_id;
end;
$$ language plpgsql security definer;

-- Function to release the lock
create or replace function public.release_session_lock(p_session_id text, p_device_id text)
returns void as $$
begin
    delete from public.session_locks 
    where session_id = p_session_id and device_id = p_device_id;
end;
$$ language plpgsql security definer;
