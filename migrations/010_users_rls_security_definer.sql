-- Migration 010: Re-enable RLS on users with SECURITY DEFINER login lookup
--
-- Problem: Login needs to find user by email without knowing tenant_id first.
-- Solution: Create a SECURITY DEFINER function owned by 'ado' (superuser)
-- that bypasses RLS for the narrow purpose of email lookup.
--
-- This is safer than disabling RLS on the entire users table.

-- Create login lookup function (bypasses RLS)
CREATE OR REPLACE FUNCTION auth_lookup_user_by_email(p_email VARCHAR)
RETURNS TABLE (
    id UUID,
    tenant_id UUID,
    email VARCHAR,
    password_hash VARCHAR,
    role VARCHAR,
    display_name VARCHAR,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ
) SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT u.id, u.tenant_id, u.email, u.password_hash, u.role,
           u.display_name, u.last_login_at, u.created_at
    FROM users u
    WHERE u.email = p_email;
END;
$$ LANGUAGE plpgsql;

-- Grant execute to the application role
GRANT EXECUTE ON FUNCTION auth_lookup_user_by_email(VARCHAR) TO ado_app;

-- Re-enable RLS on users
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Recreate policy with fail-closed NULLIF handling
DROP POLICY IF EXISTS tenant_isolation_users ON users;
CREATE POLICY tenant_isolation_users ON users
    USING (tenant_id = (NULLIF(current_setting('app.current_tenant'::text, true), ''))::uuid);

-- Force RLS for table owner too
ALTER TABLE users FORCE ROW LEVEL SECURITY;
