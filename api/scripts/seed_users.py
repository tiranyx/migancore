#!/usr/bin/env python3
"""Seed Beta Users + Agent — Day 71e"""
import asyncio
import random
import uuid
from datetime import datetime, timezone, timedelta

import asyncpg

PG_PASSWORD = "gY2UkMePh,Zvt6)6"
DSN_SUPER = f"postgresql://ado:{PG_PASSWORD}@postgres:5432/ado"

SAMPLE_PROMPTS = [
    "Halo Mighan, apa kabar? Bisa bantu saya buat business plan untuk UMKM?",
    "Tolong jelaskan perbedaan SFT dan DPO dalam training AI",
    "Bisa generate gambar logo untuk restoran Padang saya?",
    "Analisa gambar ini, apakah desain website saya sudah cukup baik?",
    "Buatkan saya presentasi 10 slide tentang AI di Indonesia",
    "Bagaimana cara setup PostgreSQL dengan RLS untuk multi-tenant?",
    "Jelaskan konsep Constitutional AI dengan bahasa yang sederhana",
    "Bisa bantu debug kode Python ini?",
    "Apa saja risiko fine-tuning model tanpa eval gate?",
    "Tolong tulis email formal untuk investor dalam Bahasa Indonesia",
    "Buatkan saya script Python untuk scrape data dari website",
    "Jelaskan perbedaan MCP dan A2A protocol",
    "Bagaimana cara migrate dari REST API ke MCP server?",
    "Bantu saya buat arsitektur sistem untuk edtech startup",
    "Apa yang perlu dipersiapkan untuk training LoRA dengan Unsloth?",
]

SAMPLE_RESPONSES = [
    "Baik, saya siap membantu. Mari kita mulai dengan struktur business plan yang solid...",
    "SFT (Supervised Fine-Tuning) adalah... sedangkan DPO (Direct Preference Optimization)...",
    "Tentu, saya akan generate beberapa konsep logo dengan tema Minangkabau modern...",
    "Setelah menganalisa desain website Anda, berikut temuan saya...",
    "Baik, berikut outline presentasi 10 slide tentang AI di Indonesia...",
    "Untuk setup PostgreSQL dengan Row-Level Security (RLS), langkahnya adalah...",
    "Constitutional AI adalah pendekatan di mana model diajarkan prinsip-prinsip etis...",
    "Saya lihat ada bug di baris 23. Variabel user_id belum di-define...",
    "Risiko utama fine-tuning tanpa eval gate adalah catastrophic forgetting...",
    "Berikut draft email formal untuk investor...",
    "Berikut script Python untuk scraping dengan ethical considerations...",
    "MCP (Model Context Protocol) adalah... sedangkan A2A (Agent-to-Agent) adalah...",
    "Migrasi dari REST ke MCP memerlukan...",
    "Untuk arsitektur edtech, saya rekomendasikan microservices dengan...",
    "Persiapan training LoRA dengan Unsloth meliputi...",
]


async def seed():
    conn = await asyncpg.connect(DSN_SUPER)

    # Temporarily disable RLS on affected tables
    await conn.execute("ALTER TABLE agents DISABLE ROW LEVEL SECURITY")
    await conn.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY")
    await conn.execute("ALTER TABLE conversations DISABLE ROW LEVEL SECURITY")
    await conn.execute("ALTER TABLE messages DISABLE ROW LEVEL SECURITY")
    print("RLS temporarily disabled for seeding")

    tenant = await conn.fetchrow("SELECT id FROM tenants ORDER BY created_at DESC LIMIT 1")
    if not tenant:
        print("No tenants found")
        await conn.close()
        return
    tenant_id = tenant["id"]

    # Create agent if none exists
    agent = await conn.fetchrow("SELECT id FROM agents LIMIT 1")
    if not agent:
        agent_id = uuid.uuid4()
        await conn.execute(
            """INSERT INTO agents (id, tenant_id, name, slug, description, generation, model_version, system_prompt, persona_blob, persona_locked, visibility, status, interaction_count, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, NOW())""",
            agent_id, tenant_id, "Mighan-Core", "core_brain", "Orchestrator agent",
            0, "migancore:0.4", "You are Mighan-Core. Direct. Precise. Indonesian-first.",
            '{"identity": "Mighan-Core"}', True, "public", "active", 0
        )
        print(f"Created agent: {agent_id}")
    else:
        agent_id = agent["id"]
        print(f"Using existing agent: {agent_id}")

    # Update any inactive agents to active
    await conn.execute("UPDATE agents SET status = 'active' WHERE status != 'active'")

    created_users = 0
    created_conversations = 0
    created_messages = 0

    for i in range(10):
        user_id = uuid.uuid4()
        email = f"beta{i+1}@migancore.test"
        pw_hash = "$argon2id$v=19$m=65536,t=3,p=4$placeholder$placeholder"
        display = f"Beta User {i+1}"
        
        try:
            await conn.execute(
                "INSERT INTO users (id, tenant_id, email, password_hash, role, display_name, created_at) VALUES ($1, $2, $3, $4, $5, $6, NOW())",
                user_id, tenant_id, email, pw_hash, "member", display
            )
            created_users += 1
        except Exception as e:
            print(f"Skip user {email}: {e}")
            continue

        for c in range(random.randint(2, 5)):
            conv_id = uuid.uuid4()
            title = f"Conv {c+1} — {random.choice(['Business', 'Tech', 'Creative', 'Research'])}"
            
            await conn.execute(
                "INSERT INTO conversations (id, tenant_id, agent_id, user_id, title, status, message_count, started_at) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())",
                conv_id, tenant_id, agent_id, user_id, title, "active", 0
            )
            created_conversations += 1

            msg_count = 0
            for m in range(random.randint(3, 8)):
                prompt = random.choice(SAMPLE_PROMPTS)
                response = random.choice(SAMPLE_RESPONSES)
                
                user_msg_id = uuid.uuid4()
                await conn.execute(
                    "INSERT INTO messages (id, conversation_id, tenant_id, role, content, created_at) VALUES ($1, $2, $3, $4, $5, $6)",
                    user_msg_id, conv_id, tenant_id, "user", prompt,
                    datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 48), minutes=random.randint(0, 59))
                )
                created_messages += 1
                msg_count += 1

                assist_msg_id = uuid.uuid4()
                await conn.execute(
                    "INSERT INTO messages (id, conversation_id, tenant_id, role, content, created_at) VALUES ($1, $2, $3, $4, $5, $6)",
                    assist_msg_id, conv_id, tenant_id, "assistant", response,
                    datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 48), minutes=random.randint(0, 59))
                )
                created_messages += 1
                msg_count += 1

            await conn.execute(
                "UPDATE conversations SET message_count = $1 WHERE id = $2",
                msg_count, conv_id
            )

    print(f"\nSeeded: users={created_users}, conversations={created_conversations}, messages={created_messages}")

    u = await conn.fetchval("SELECT count(*) FROM users")
    conv = await conn.fetchval("SELECT count(*) FROM conversations")
    msg = await conn.fetchval("SELECT count(*) FROM messages")
    a = await conn.fetchval("SELECT count(*) FROM agents")
    print(f"DB Totals: users={u}, agents={a}, conversations={conv}, messages={msg}")

    # Re-enable RLS
    await conn.execute("ALTER TABLE agents ENABLE ROW LEVEL SECURITY")
    await conn.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    await conn.execute("ALTER TABLE conversations ENABLE ROW LEVEL SECURITY")
    await conn.execute("ALTER TABLE messages ENABLE ROW LEVEL SECURITY")
    print("RLS re-enabled")

    await conn.close()


asyncio.run(seed())
