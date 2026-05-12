import asyncio
exec(open("/app/workspace/seed_beta_users.py").read())
asyncio.run(seed())
