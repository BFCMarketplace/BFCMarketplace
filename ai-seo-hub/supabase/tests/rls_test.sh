#!/usr/bin/env bash
# Verifies migrations + Row Level Security on a throwaway local PostgreSQL.
# Usage: supabase/tests/rls_test.sh   (needs postgres 16 binaries; run as non-root-capable)
set -euo pipefail
cd "$(dirname "$0")/.."
PGBIN=$(ls -d /usr/lib/postgresql/*/bin | tail -1)
DIR=$(mktemp -d); PORT=54999
chmod 755 "$DIR"; chown postgres "$DIR" 2>/dev/null || true
run_pg() { if [ "$(id -u)" = 0 ]; then su postgres -c "$*"; else bash -c "$*"; fi; }
run_pg "$PGBIN/initdb -D $DIR/data -A trust >/dev/null"
run_pg "$PGBIN/pg_ctl -D $DIR/data -o '-p $PORT -k $DIR' -l $DIR/log -w start >/dev/null"
trap 'run_pg "$PGBIN/pg_ctl -D $DIR/data -m immediate stop >/dev/null" || true' EXIT
PSQL="psql -h $DIR -p $PORT -U postgres -v ON_ERROR_STOP=1 -q -X"
# Minimal Supabase auth stub (real Supabase provides this)
$PSQL -d postgres <<'SQL'
create role anon nologin; create role authenticated nologin;
create schema auth;
create table auth.users(id uuid primary key);
create function auth.uid() returns uuid language sql stable as
 $$ select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
grant usage on schema auth to anon, authenticated;
grant execute on function auth.uid() to anon, authenticated;
SQL
for f in migrations/*.sql; do $PSQL -d postgres -f "$f"; done
$PSQL -d postgres <<'SQL'
grant usage on schema public to anon, authenticated;
grant select, insert, update, delete on all tables in schema public to authenticated;
grant usage on all sequences in schema public to authenticated;
SQL
$PSQL -d postgres -f tests/rls_test.sql
echo "RLS TESTS PASSED"
