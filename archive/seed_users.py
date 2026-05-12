#!/usr/bin/env python3
"""
Seed Beta Users — Day 71e

Generates 10 realistic beta users with conversations and messages.
This populates the DB with realistic data for distillation pipeline testing.

Run:
    docker compose exec api python -m scripts.seed_beta_users

Author: MiganCore ADO
"""
from __future__ import annotations

import asyncio
import os
import random
import uuid
from datetime import datetime, timezone, timedelta

import asyncpg

# Sample Indonesian prompts for realistic conversations
SAMPLE_PROMPTS = [
    "Halo Mighan, apa kabar? Bisa bantu saya buat business plan untuk UMKM?",
    "Tolong jelaskan perbedaan SFT dan DPO dalam training AI",
    "Bisa generate gambar logo untuk restoran Padang saya?",
    "Analisa gambar ini, apakah desain website saya sudah cukup baik?",
    "Buatkan saya presentasi 10 slide tentang AI di Indonesia",
    "Bagaimana cara setup PostgreSQL dengan RLS untuk multi-tenant?",
    "Jelaskan konsep Constitutional AI dengan bahasa yang sederhana",
    "Bisa bantu debug kode Python ini? [paste code]",
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
    "Saya lihat ada bug di baris 23. Variabel `user_id` belum di-define...",
    "Risiko utama fine-tuning tanpa eval gate adalah catastrophic forgetting...",
    "Berikut draft email formal untuk investor...",
    "Berikut script Python untuk scraping dengan ethical considerations...",
    "MCP (Model Context Protocol) adalah... sedangkan A2A (Agent-to-Agent) adalah...",
    "Migrasi dari REST ke MCP memerlukan...",
    "Untuk arsitektur edtech, saya rekomendasikan microservices dengan...",
    "Persiapan training LoRA dengan Unsloth meliputi...",
]


async def seed():
    dsn = os.environ.get("DATABASE_URL", "").replace("+asyncpg", "", 1)
    conn = await asyncpg.connect(dsn)

    # Get first tenant
    tenant = await conn.fetchrow("SELECT id FROM tenants ORDER BY created_at DESC LIMIT 1")
    if not tenant:
        print("No tenants found. Cannot seed.")
        await conn.close()
        return
    tenant_id = tenant["id"]
    print(f"Using tenant: {tenant_id}")

    # Get or create agent
    agent = await conn.fetchrow("SELECT id FROM agents WHERE status = 'active' LIMIT 1")
    if not agent:
        print("No active agents found.")
        await conn.close()
        return
    agent_id = agent["id"]
    print(f"Using agent: {agent_id}")

    created_users = 0
    created_conversations = 0
    created_messages = 0

    for i in range(10):
        # Create user
        user_id = uuid.uuid4()
        email = f"beta{i+1}@migancore.test"
        # Argon2 hash for 'beta123'
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

        # Create 2-5 conversations per user
        for c in range(random.randint(2, 5)):
            conv_id = uuid.uuid4()
            title = f"Conversation {c+1} — {random.choice(['Business', 'Tech', 'Creative', 'Research'])}"
            
            await conn.execute(
                "INSERT INTO conversations (id, tenant_id, agent_id, user_id, title, status, message_count, started_at) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())",
                conv_id, tenant_id, agent_id, user_id, title, "active", 0
            )
            created_conversations += 1

            # Create 3-8 message pairs per conversation
            msg_count = 0
            for m in range(random.randint(3, 8)):
                prompt = random.choice(SAMPLE_PROMPTS)
                response = random.choice(SAMPLE_RESPONSES)
                
                # User message
                user_msg_id = uuid.uuid4()
                await conn.execute(
                    "INSERT INTO messages (id, conversation_id, tenant_id, role, content, created_at) VALUES ($1, $2, $3, $4, $5, $6)",
                    user_msg_id, conv_id, tenant_id, "user", prompt,
                    datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 48), minutes=random.randint(0, 59))
                )
                created_messages += 1
                msg_count += 1

                # Assistant message
                assist_msg_id = uuid.uuid4()
                await conn.execute(
                    "INSERT INTO messages (id, conversation_id, tenant_id, role, content, created_at) VALUES ($1, $2, $3, $4, $5, $6)",
                    assist_msg_id, conv_id, tenant_id, "assistant", response,
                    datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 48), minutes=random.randint(0, 59))
                )
                created_messages += 1
                msg_count += 1

            # Update conversation message_count
            await conn.execute(
                "UPDATE conversations SET message_count = $1 WHERE id = $2",
                msg_count, conv_id
            )

    print(f"\nSeeded:")
    print(f"  Users: {created_users}")
    print(f"  Conversations: {created_conversations}")
    print(f"  Messages: {created_messages}")

    # Show totals
    u = await conn.fetchval("SELECT count(*) FROM users")
    conv = await conn.fetchval("SELECT count(*) FROM conversations")
    msg = await conn.fetchval("SELECT count(*) FROM messages")
    print(f"\nDB Totals: users={u}, conversations={conv}, messages={msg}")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(seed())
