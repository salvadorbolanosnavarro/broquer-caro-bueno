"""Bootstrap only the disposable PostgreSQL service in CI, never a Supabase project."""
import os
import psycopg
if os.environ.get('BROQUER_CI_DISPOSABLE') != 'true':
    raise SystemExit('Requires explicitly disposable CI database')
with psycopg.connect(os.environ['MIGRATIONS_DATABASE_URL']) as db:
    db.execute('CREATE SCHEMA auth')
    db.execute('CREATE TABLE auth.users(id uuid PRIMARY KEY,email text,email_confirmed_at timestamptz)')
