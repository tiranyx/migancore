"""
Scope resolver: derive JWT scopes from user role and tenant plan.
Replaces hardcoded scope strings across the auth router.
"""


# Base scopes per role
ROLE_SCOPES = {
    "owner":   ["agents:read", "agents:write", "chat:write", "training:trigger", "admin:read"],
    "admin":   ["agents:read", "agents:write", "chat:write", "admin:read"],
    "member":  ["agents:read", "agents:write", "chat:write"],
    "readonly": ["agents:read"],
}

# Plan modifiers
PLAN_MODIFIERS = {
    "free":      ["quota:limited"],
    "starter":   ["quota:standard"],
    "pro":       ["quota:unlimited"],
    "enterprise": ["quota:unlimited", "priority:support"],
}


def resolve_scopes(role: str, plan: str) -> str:
    """Return a space-separated scope string for JWT.

    Args:
        role: User role (owner, admin, member, readonly)
        plan: Tenant plan (free, starter, pro, enterprise)

    Returns:
        Space-separated OAuth2-style scope string.
    """
    base = ROLE_SCOPES.get(role, ROLE_SCOPES["readonly"]).copy()
    modifiers = PLAN_MODIFIERS.get(plan, [])
    base.extend(modifiers)
    return " ".join(base)
