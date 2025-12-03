-- Create the table to track active sessions
create table if not exists active_chat_locks (
  session_id uuid primary key,
  device_id text not null,
  last_active_at timestamptz default now()
);

-- Enable RLS (optional but good practice, though we might need public access if no auth)
alter table active_chat_locks enable row level security;

-- Policy: Allow anyone to read/write (since we are using device_id for auth)
create policy "Allow public access" on active_chat_locks
  for all using (true) with check (true);

-- Function to attempt to acquire a lock
create or replace function acquire_session_lock(p_session_id uuid, p_device_id text)
returns boolean
language plpgsql
security definer
as $$
declare
  v_current_device text;
  v_last_active timestamptz;
begin
  -- Check if a lock exists
  select device_id, last_active_at into v_current_device, v_last_active
  from active_chat_locks
  where session_id = p_session_id;

  -- Case 1: No lock exists -> Create one
  if not found then
    insert into active_chat_locks (session_id, device_id, last_active_at)
    values (p_session_id, p_device_id, now());
    return true;
  end if;

  -- Case 2: Lock exists but is stale (> 1 minute old) -> Steal it
  if v_last_active < (now() - interval '1 minute') then
    update active_chat_locks
    set device_id = p_device_id, last_active_at = now()
    where session_id = p_session_id;
    return true;
  end if;

  -- Case 3: Lock exists and belongs to this device -> Refresh it
  if v_current_device = p_device_id then
    update active_chat_locks
    set last_active_at = now()
    where session_id = p_session_id;
    return true;
  end if;

  -- Case 4: Lock exists, is active, and belongs to someone else -> Fail
  return false;
end;
$$;

-- Function to refresh the lock (heartbeat)
create or replace function refresh_session_lock(p_session_id uuid, p_device_id text)
returns void
language plpgsql
security definer
as $$
begin
  update active_chat_locks
  set last_active_at = now()
  where session_id = p_session_id and device_id = p_device_id;
end;
$$;

-- Function to release the lock (on exit)
create or replace function release_session_lock(p_session_id uuid, p_device_id text)
returns void
language plpgsql
security definer
as $$
begin
  delete from active_chat_locks
  where session_id = p_session_id and device_id = p_device_id;
end;
$$;
