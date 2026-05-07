# ADO FOUNDATION V2 — Complete Baseline Capability
**Dibuat:** 2026-05-09 | **Tujuan:** Satu dokumen untuk bangun ADO yang benar dari fondasi
**Prinsip:** ADO adalah Sovereign AI — otak, orkestrasi, tools, MCP, memori semua milik ADO sendiri.
**Timeline:** 5 sprint × 1 minggu = 35 hari (Day 68–103)

---

## PRINSIP ARSITEKTUR — SOVEREIGN AI

```
ADO SOVEREIGN CORE (tidak bisa dikompromikan):
  Otak        = Qwen3 fine-tuned, milik ADO — TIDAK ada routing ke Claude/GPT untuk jawab user
  Memori      = Qdrant episodic + semantic, self-hosted
  Orkestrasi  = LangGraph director, milik ADO
  Tools       = 35+ tools, ADO yang kontrol interface dan logika
  MCP Server  = ADO MCP di Smithery, standar terbuka
  Identitas   = license + persona system
  KB          = Indonesia KB, auto-update setiap hari
  Training    = ORPO/GRPO pipeline, autonomous nightly

TEACHER API (Claude/Gemini/Kimi) — OFFLINE ONLY:
  → Generate training pairs saat tidak ada user aktif
  → Seperti buku pelajaran — ADO belajar DARI mereka
  → Tidak pernah menjawab user, tidak pernah ada di runtime
  → Pengetahuan masuk ke bobot model ADO, bukan diforward

EXTERNAL RESOURCE (bukan otak, ADO tetap kontrol):
  fal.ai  → render image  (ADO yang prompt + proses output)
  Kling   → render video  (ADO yang prompt + proses output)
  Suno    → render musik  (ADO yang prompt + proses output)
  BPS/IDX → data feed     (ADO yang baca + analisa + jawab)
  Slack/WA→ channel saja  (ADO yang jawab, bukan mereka)
```

**Analogi:** Seperti dokter ahli. Pengetahuan = miliknya sendiri.
Stetoskop, X-Ray = tools. Lab eksternal = data feed.
Yang menjawab pasien = tetap dokternya. Bukan mesin X-Ray-nya.

---

## GAMBARAN BESAR

Fahmi mau ADO punya **baseline capability** yang solid dan scalable:

```
┌──────────────────────────────────────────────────────────────┐
│                   ADO FOUNDATION V2                          │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  LAYER 4 — COGNITIVE ENGINE                         │    │
│  │  Intent understanding · Synthesis · Self-correction  │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  LAYER 3 — CREATION SUITE                           │    │
│  │  Image · Video · Audio · Code · Web · Data · Report  │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  LAYER 2 — TOOL ECOSYSTEM (reliable, 95%+ accuracy) │    │
│  │  23+ tools existing + 12 tools baru                  │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  LAYER 1 — HYBRID BRAIN (fondasi semua)             │    │
│  │  Local: Qwen3-8B (identity, privacy, domain)         │    │
│  │  Cloud: Claude/Gemini (coding berat, math, creative) │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

---

## STATUS SEKARANG vs TARGET

| Capability | Sekarang | Target Foundation V2 |
|-----------|----------|---------------------|
| **Coding / Engineering** | Sedang (7B tanpa routing) | Kuat — hybrid route ke Claude Sonnet |
| **Creative writing** | 72% (di bawah gate) | Kuat — 95%+ via fine-tune + routing |
| **Cognitive / Reasoning** | Lemah (7B) | Kuat — Qwen3-8B + GRPO + routing |
| **Intent understanding** | Generik | Tajam — intent classifier + context |
| **Image generation** | ✅ Ada (fal.ai basic) | Advanced — FLUX 1.1 Pro, multi-style |
| **Video generation** | ❌ Tidak ada | Kling AI / Wan2.1 |
| **Audio / Music** | TTS basic saja | TTS + music gen + sound FX |
| **Artifact (code rendered)** | ❌ Tidak ada | HTML/React rendered live di chat |
| **Script / App generator** | ❌ Tidak ada | Generate + preview + deploy |
| **Web generator** | ❌ Tidak ada | Landing page → deploy Vercel/Netlify |
| **Data analysis** | ❌ Tidak ada | CSV upload → chart → insight → PDF |
| **Report generator** | PDF basic saja | Full report: data + chart + narasi |
| **Tool reliability** | 74% | 95%+ |
| **Latency** | 3–8s CPU | < 2s (hybrid routing + caching) |

---

## SPRINT F1 — BRAIN UPGRADE + ORCHESTRATION (Fondasi Semua)
**Timeline:** Day 68–74 (1 minggu)
**Kenapa pertama:** Semua capability lain bergantung pada kualitas otak ADO sendiri.
**Prinsip:** 100% ADO brain untuk runtime. Teacher API hanya offline untuk training.

### Yang Dibangun

**1. Upgrade ke Qwen3-8B — Thinking Mode**
```bash
# Pull model baru
docker exec ado-ollama-1 ollama pull qwen3:8b-q4_K_M

# Qwen3-8B keunggulan vs Qwen2.5-7B:
# - Hybrid thinking mode: bisa berpikir step-by-step sebelum jawab
# - MMLU: 74% → 81% (lebih pintar)
# - HumanEval coding: 56% → 71% (lebih bisa coding)
# - Math: 62% → 75%
# - Context: 128K token (sama)
# - VRAM: 4.5GB → 5.2GB (masih muat di VPS)
```

**Cara aktifkan thinking mode di Ollama:**
```python
# Di api/services/ollama_client.py
async def generate_with_thinking(prompt: str, use_thinking: bool = False) -> str:
    if use_thinking:
        # Qwen3 thinking mode: tambahkan /think di awal
        # Model akan "berpikir dulu" sebelum jawab
        full_prompt = f"/think\n{prompt}"
    else:
        full_prompt = f"/no_think\n{prompt}"  # Cepat, untuk task sederhana
    
    return await ollama_generate(model="qwen3:8b-q4_K_M", prompt=full_prompt)

# Kapan pakai thinking mode:
# ON  → coding, math, analisa kompleks, debugging
# OFF → greet, recall, simple Q&A, tool calls
```

**2. Intent Classifier (`api/services/intent_classifier.py`)**

```python
INTENTS = {
    "code_generate": ["buat kode", "buatkan script", "generate function", "implementasi"],
    "code_debug": ["kenapa error", "debug", "fix bug", "tidak berjalan"],
    "creative_write": ["tulis", "buat cerita", "copywriting", "tagline"],
    "data_analyze": ["analisa", "olah data", "visualisasi", "chart", "grafik"],
    "image_generate": ["buat gambar", "generate image", "ilustrasi"],
    "video_generate": ["buat video", "generate video", "animasi"],
    "web_generate": ["buat website", "landing page", "web app"],
    "report_generate": ["buat laporan", "report", "rekap"],
    "domain_query": ["hukum", "pajak", "regulasi", "peraturan"],
    "general": []  # fallback
}

def classify(message: str) -> str:
    message_lower = message.lower()
    for intent, keywords in INTENTS.items():
        if any(kw in message_lower for kw in keywords):
            return intent
    return "general"
```

**Gate Sprint F1:**
- [ ] Routing berjalan: 10 test messages, 9/10 route ke tempat yang benar
- [ ] 0 PII leak ke cloud brain (test dengan NIK/nomor HP di pesan)
- [ ] Qwen3-8B pull dan bisa dipanggil
- [ ] Intent classifier: 15 test messages, 13/15 correct intent

---

## SPRINT F2 — CODING & ENGINEERING SUITE
**Timeline:** Day 75–81 (1 minggu)
**Output:** ADO bisa jadi coding partner yang benar-benar berguna

### Yang Dibangun

**1. Code Executor (`api/tools/code_executor.py`)**
```python
# Sandboxed execution pakai Docker-in-Docker
# Support: Python, JavaScript (Node), Bash, SQL
# Timeout: 30 detik
# Output: stdout + stderr + files generated

async def execute_code(lang: str, code: str) -> dict:
    container = docker_client.containers.run(
        image=f"code-sandbox-{lang}",  # Pre-built lightweight image
        command=["timeout", "30", "run_code.sh"],
        volumes={"/tmp/sandbox": {"bind": "/workspace", "mode": "rw"}},
        mem_limit="256m", cpu_period=100000, cpu_quota=50000,  # 0.5 core
        network_disabled=True,  # NO internet access
        remove=True
    )
    return {"stdout": container.decode(), "files": list_generated_files()}
```

**2. Artifact Renderer (chat UI)**
```javascript
// Di chat.html: detect jika response mengandung HTML/React/code block
// Render dalam iframe sandboxed langsung di chat

function renderArtifact(content, type) {
    if (type === 'html') {
        const iframe = document.createElement('iframe');
        iframe.srcdoc = content;
        iframe.sandbox = 'allow-scripts';
        iframe.style = 'width:100%; height:400px; border:1px solid #333; border-radius:8px';
        return iframe;
    }
    if (type === 'react') {
        // Compile dengan Babel standalone, render di iframe
    }
}

// Trigger: ketika ADO response mengandung ```html atau ```jsx
// Tampilkan toggle: [Kode] [Preview]
```

**3. Web App Generator (`api/tools/web_generator.py`)**
```python
# Input: deskripsi dari user ("buat landing page untuk toko online sepatu")
# Output: folder dengan index.html + style.css + script.js
# Deploy: auto-push ke Netlify/Vercel via API

async def generate_web_app(description: str) -> dict:
    # 1. ADO (via cloud brain) generate kode
    code_prompt = f"""
    Buat landing page lengkap untuk: {description}
    Output: 3 file — index.html, style.css, script.js
    Style: modern, responsive, Indonesia-friendly
    Format output: JSON dengan key html, css, js
    """
    result = await cloud_brain.generate(code_prompt, task_type="code")
    
    # 2. Parse dan validasi
    files = parse_code_response(result)
    
    # 3. Deploy ke Netlify
    deploy_url = await netlify_deploy(files)
    
    return {"files": files, "preview_url": deploy_url}
```

**4. Fine-tune Cycle 7 — Coding Pairs (200 pairs)**
```
Focus:
- Python: FastAPI, asyncio, pandas, SQLAlchemy
- JavaScript: React, Next.js, Tailwind
- SQL: PostgreSQL, query optimization
- Docker: Dockerfile, compose
- Debug: error messages → solution step-by-step
Format: semua pakai "buat kode untuk..." atau "kenapa error ini..." Indonesia
```

**Gate Sprint F2:**
- [ ] execute_code: Python + JS berjalan dalam sandbox, 0 escape
- [ ] Artifact renderer: HTML di-render di chat, React di-compile
- [ ] Web generator: bisa generate + preview dalam 60 detik
- [ ] Coding eval: 10 pertanyaan coding, 8/10 correct (via hybrid routing)

---

## SPRINT F3 — CREATION SUITE (IMAGE / VIDEO / AUDIO / MUSIC)
**Timeline:** Day 82–88 (1 minggu)
**Output:** ADO jadi creative AI, bukan hanya text AI

### Yang Dibangun

**1. Image Generation — Upgrade ke FLUX 1.1 Pro**
```python
# Sekarang: fal.ai basic
# Upgrade: FLUX 1.1 Pro (photorealistic) + FLUX Schnell (fast, 4 step)
# Tambah: style selector (photorealistic / anime / illustration / logo)

async def generate_image_v2(prompt: str, style: str = "photorealistic") -> dict:
    style_prefixes = {
        "photorealistic": "RAW photo, 8k resolution, detailed, ",
        "anime": "anime style, vibrant colors, Studio Ghibli inspired, ",
        "illustration": "digital illustration, flat design, vector art, ",
        "logo": "minimalist logo design, professional, SVG-style, ",
        "infographic": "infographic design, data visualization, clean layout, "
    }
    enhanced_prompt = style_prefixes.get(style, "") + prompt
    return await fal_client.generate(model="fal-ai/flux-pro/v1.1", prompt=enhanced_prompt)
```

**2. Video Generation (`api/tools/video_generator.py`)**
```python
# Provider: Kling AI (terbaik untuk konten Indonesia, murah)
# Alternative: Wan2.1 open source (self-hosted tapi butuh GPU)
# Input: text prompt atau image + motion description
# Output: MP4 5-10 detik

async def generate_video(prompt: str, duration: int = 5) -> dict:
    response = await kling_client.post("/v1/videos/text2video", json={
        "model": "kling-v1",
        "prompt": prompt,
        "duration": duration,
        "aspect_ratio": "16:9"
    })
    task_id = response["task_id"]
    # Poll sampai selesai (biasanya 60-120 detik)
    return await poll_video_result(task_id)
```

**3. Music & Sound Generator (`api/tools/audio_generator.py`)**
```python
# Music: Suno API (generate full song dengan lirik)
# Sound FX: ElevenLabs Sound Generation
# Voice clone: ElevenLabs (untuk TTS dengan suara custom klien)

async def generate_music(prompt: str, duration: int = 30) -> dict:
    # "buat musik background untuk presentasi bisnis, energetik"
    return await suno_client.generate(prompt=prompt, duration=duration)

async def generate_sound_fx(description: str) -> dict:
    # "suara notifikasi aplikasi, modern, subtle"
    return await elevenlabs_client.sound_generation(text=description)

async def tts_advanced(text: str, voice_id: str = "default") -> dict:
    # Per-client voice: klien BERLIAN bisa clone suara sendiri
    return await elevenlabs_client.tts(text=text, voice_id=voice_id)
```

**4. Fine-tune — Creative Pairs (100 pairs)**
```
Focus:
- Copywriting Indonesia: tagline, headline, body copy
- Storytelling: cerita brand, narrative bisnis
- Deskripsi visual: describe gambar yang akan di-generate
- Direktif kreatif: prompt engineering untuk image/video
```

**Gate Sprint F3:**
- [ ] Image: 5 style berbeda berjalan, latency < 15s
- [ ] Video: generate 5s video dari text prompt
- [ ] Music: generate 30s music dari deskripsi
- [ ] Sound FX: generate dari deskripsi teks
- [ ] TTS: upgrade latency < 2s, lebih natural

---

## SPRINT F4 — DATA ANALYSIS & REPORT SUITE
**Timeline:** Day 89–95 (1 minggu)
**Output:** ADO bisa analisa data, buat chart, tulis laporan profesional

### Yang Dibangun

**1. Data Analyzer (`api/tools/data_analyzer.py`)**
```python
# Input: upload CSV/Excel via chat
# Process: Python pandas + matplotlib di sandbox
# Output: statistik deskriptif + chart PNG + narasi insight

async def analyze_data(file_path: str, question: str) -> dict:
    # 1. Load file
    df = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path)
    
    # 2. Generate analysis code via cloud brain
    code_prompt = f"""
    DataFrame info: {df.dtypes.to_string()}, {len(df)} rows
    Pertanyaan user: {question}
    Buat kode Python untuk analisa dan visualisasi. Output: kode saja.
    """
    analysis_code = await cloud_brain.generate(code_prompt, task_type="data_analysis")
    
    # 3. Execute di sandbox
    result = await execute_code("python", analysis_code)
    
    # 4. Narasi insight via ADO
    narrative = await local_brain.generate(f"Jelaskan insight dari: {result['stdout']}")
    
    return {"chart": result.get("chart_path"), "stats": result["stdout"], "insight": narrative}
```

**2. Report Generator (`api/tools/report_generator.py`)**
```python
# Input: topik + data (opsional) + template
# Output: PDF laporan profesional dengan cover, TOC, charts, narasi

REPORT_TEMPLATES = {
    "business": "template laporan bisnis: executive summary, analisa pasar, rekomendasi",
    "financial": "template laporan keuangan: pendapatan, pengeluaran, proyeksi",
    "research": "template riset: metodologi, temuan, kesimpulan, referensi",
    "proposal": "template proposal: latar belakang, tujuan, anggaran, timeline",
}

async def generate_report(topic: str, data: dict, template: str) -> dict:
    # 1. Generate konten via cloud brain (panjang, kompleks)
    content = await cloud_brain.generate(
        f"Buat laporan {template} tentang: {topic}\nData: {data}",
        task_type="report"
    )
    
    # 2. Convert ke PDF dengan styling profesional
    pdf_path = await render_pdf(content, template=template)
    
    return {"pdf_path": pdf_path, "preview": content[:500]}
```

**3. File Upload Handler (chat UI)**
```javascript
// Drag & drop CSV/Excel ke chat
// Preview tabel 5 baris pertama
// Tombol "Analisa" → trigger data_analyzer tool
// Hasil: chart inline di chat + insight teks + tombol "Download Report"

chatInput.addEventListener('drop', async (e) => {
    const file = e.dataTransfer.files[0];
    if (['csv', 'xlsx', 'xls'].includes(file.name.split('.').pop())) {
        const formData = new FormData();
        formData.append('file', file);
        const result = await uploadFile(formData);
        showFilePreview(result.preview);
        addChip('📊 Analisa data ini');
    }
});
```

**Gate Sprint F4:**
- [ ] Upload CSV → analisa → chart → insight dalam < 30s
- [ ] Report 5 halaman generate dalam < 60s, layout rapi
- [ ] 3 template report: bisnis, keuangan, proposal
- [ ] Chart 5 tipe: bar, line, pie, scatter, heatmap

---

## SPRINT F5 — COGNITIVE ENGINE (Penalaran & Relevansi)
**Timeline:** Day 96–103 (1 minggu)
**Output:** ADO paham maksud user lebih baik, jawab lebih relevan

### Yang Dibangun

**1. Context-Aware System Prompt (`api/services/context_builder.py`)**

```python
# Bukan satu system prompt generik — tapi dynamically built per conversation

def build_system_prompt(agent: Agent, user_history: list, intent: str) -> str:
    base = f"""Kamu adalah {agent.name}, AI asisten untuk {agent.org_name}.
    
IDENTITAS: {agent.persona_description}
DOMAIN UTAMA: {agent.primary_domains}
BAHASA: Bahasa Indonesia, langsung dan tidak bertele-tele.
"""
    
    # Inject context sesuai intent
    if intent == "code_generate":
        base += """
MODE: Coding Assistant
- Langsung ke kode, minimal penjelasan kecuali diminta
- Selalu sertakan error handling
- Gunakan best practices bahasa yang diminta
- Jika tidak yakin, tanya clarification sebelum generate
"""
    elif intent == "creative_write":
        base += """
MODE: Creative Partner  
- Sesuaikan tone dengan brand klien
- Berikan 2-3 variasi jika relevan
- Singkat tapi impactful
"""
    elif intent == "data_analyze":
        base += """
MODE: Data Analyst
- Fokus ke insight yang actionable
- Gunakan angka konkret
- Rekomendasikan langkah selanjutnya
"""
    
    # Inject relevant memories
    if user_history:
        base += f"\nKONTEKS PERCAKAPAN SEBELUMNYA: {summarize_history(user_history)}"
    
    return base
```

**2. Intent-to-Tool Mapper yang Lebih Cerdas**

```python
# Sekarang: user harus secara eksplisit trigger tool
# Target: ADO proaktif suggest dan eksekusi tool yang relevan

INTENT_TO_TOOL = {
    "image_generate": "generate_image",
    "video_generate": "generate_video",
    "code_generate": "execute_code + write_file",
    "web_generate": "web_generator",
    "data_analyze": "data_analyzer",
    "report_generate": "report_generator",
    "music_generate": "generate_music",
    "search_info": "onamix_search + web_read",
    "domain_query": "knowledge_base_search",
}

async def process_with_intent(message: str, agent: Agent) -> Response:
    intent = classify_intent(message)
    tools_to_use = INTENT_TO_TOOL.get(intent, [])
    
    # Proaktif: jika intent = image_generate, langsung panggil tool
    # Bukan tunggu LLM memutuskan — classifier sudah tahu
    if tools_to_use:
        return await execute_with_tools(message, tools_to_use, agent)
    else:
        return await conversational_response(message, agent)
```

**3. Self-Correction Loop**

```python
# Sebelum kirim jawaban ke user, ADO cek dirinya sendiri

async def generate_with_self_check(message: str, first_response: str) -> str:
    check_prompt = f"""
Review jawaban ini untuk pertanyaan: "{message}"
Jawaban: "{first_response}"

Cek:
1. Apakah relevan dengan pertanyaan?
2. Apakah ada fakta yang salah atau perlu dikonfirmasi?
3. Apakah ada yang kurang dari yang diminta?

Jika OK, jawab: PASS
Jika ada masalah, perbaiki jawaban.
"""
    check_result = await local_brain.generate(check_prompt)
    
    if "PASS" in check_result:
        return first_response
    else:
        return check_result  # versi yang sudah diperbaiki
```

**4. GRPO Training — Reasoning via Teacher (200 pairs, offline)**

```
Proses: Teacher API (Claude/Gemini) generate pairs saat tidak ada user
Format GRPO:
- Math step-by-step: soal → langkah 1 → langkah 2 → jawaban
- Code debugging: error → analisa → fix → penjelasan
- Logic: pertanyaan → breakdown → kesimpulan
- Bisnis analisa: situasi → faktor → rekomendasi

ADO belajar POLA berpikir dari pairs ini
→ knowledge masuk ke bobot model ADO sendiri
→ bukan Claude yang jawab, tapi ADO yang sudah belajar cara berpikir Claude

Target: reasoning gate ≥ 0.80 di eval Cycle 8
```

**5. Nightly Teacher Curriculum (`scripts/nightly_teacher.py`)**

```python
# Jalan 23:00 UTC setiap malam, saat tidak ada user aktif
# Teacher (Gemini Flash, murah) generate 30-50 pairs per topik

CURRICULUM = [
    # Minggu 1: Coding & Engineering
    "python_async", "fastapi_patterns", "docker_compose", "sql_optimization",
    "react_hooks", "typescript_patterns", "debugging_methods",
    
    # Minggu 2: Math & Logic  
    "statistik_bisnis", "probabilitas", "logika_formal", "analisa_data",
    
    # Minggu 3: Creative & Writing
    "copywriting_indonesia", "storytelling_brand", "proposal_bisnis",
    
    # Minggu 4: Domain Indonesia
    "hukum_bisnis", "pajak_umkm", "regulasi_ojk", "standar_sni",
    
    # dst rotating...
]

async def run_nightly():
    topic = get_todays_topic(CURRICULUM)
    pairs = await teacher_api.generate_pairs(topic, count=40)
    await store_pairs(pairs)
    
    # Jika sudah > 100 pairs baru → trigger micro-training
    if await count_new_pairs() >= 100:
        await trigger_micro_training()
```

**Gate Sprint F5:**
- [ ] Intent classifier 95%+ accuracy (50 test messages)
- [ ] Self-correction via thinking mode: jawaban membaik untuk 3/5 test
- [ ] Context-aware system prompt: respons beda untuk coding vs creative
- [ ] Tool proaktif: "buat gambar logo" langsung trigger generate_image
- [ ] Nightly teacher script berjalan sekali tanpa error

---

## RINGKASAN SEMUA TOOL YANG ADA (POST FOUNDATION V2)

### Tools yang Sudah Ada (23 tools)
`onamix_get` `onamix_search` `onamix_scrape` `onamix_post` `onamix_crawl`
`onamix_history` `onamix_links` `onamix_config` `onamix_multi`
`web_read` `generate_image` `analyze_image` `write_file` `read_file`
`export_pdf` `export_slides` `tts` `stt` `generate_image` `knowledge_base_search`
`spawn_agent` `get_genealogy` `get_agent_info`

### Tools Baru (12 tools dari Foundation V2)
| Tool | Sprint | Input | Output |
|------|--------|-------|--------|
| `execute_code` | F2 | lang + code | stdout + files |
| `generate_web_app` | F2 | deskripsi | HTML/CSS/JS + URL |
| `generate_image_v2` | F3 | prompt + style | image URL |
| `generate_video` | F3 | prompt + duration | MP4 URL |
| `generate_music` | F3 | prompt + duration | audio URL |
| `generate_sound_fx` | F3 | description | audio URL |
| `tts_advanced` | F3 | text + voice_id | audio URL |
| `analyze_data` | F4 | file_path + question | chart + insight |
| `generate_report` | F4 | topic + data + template | PDF URL |
| `classify_intent` | F5 | message | intent string |
| `self_check_response` | F5 | message + response | improved response |
| `build_context_prompt` | F5 | agent + history + intent | system prompt |

**Total setelah Foundation V2: 35 tools**

---

## TRAINING CYCLES UNTUK FOUNDATION V2

Semua pairs di-generate oleh Teacher API (offline, saat tidak ada user aktif).
ADO belajar dari pairs tersebut — knowledge masuk ke bobot model ADO sendiri.

| Cycle | Base Model | Pairs | Focus | Gate Baru |
|-------|-----------|-------|-------|-----------|
| Cycle 7 | Qwen3-8B | 800 | Tool-use +200 (diverse scenarios), Coding +200 (Python/JS/SQL), Creative +100, Voice maintenance +100 | tool-use ≥ 0.88 |
| Cycle 8 | Qwen3-8B | 900 | GRPO reasoning +200 (thinking mode pairs), Data analysis +150, Report +100, Domain Indonesia +150 | reasoning ≥ 0.80 |
| Cycle 9 | Qwen3-8B | 700 | Specialization: hukum +150, keuangan +150, medis +100, engineering +150 | domain accuracy ≥ 0.90 |
| Cycle 10+ | Qwen3-14B? | 1000+ | Nightly curriculum (rotating topics, autonomous) | semua gates naik 0.02 |

**Nightly micro-training:** 50 pairs/hari × 7 hari = 350 pairs → micro cycle mingguan otomatis

---

## INFRASTRUKTUR YANG PERLU DIUPGRADE

| Item | Sekarang | Target | Kapan |
|------|----------|--------|-------|
| Base model | Qwen2.5-7B | Qwen3-8B | Sprint F1 |
| GPU untuk inference | CPU (3-8s) | Cloud routing < 2s | Sprint F1 (via hybrid) |
| GPU untuk training | Vast.ai on-demand | Sama, tapi lebih otomatis | Sprint F4 |
| Code sandbox | Tidak ada | Docker-in-Docker | Sprint F2 |
| File storage | VPS local | MinIO atau S3-compatible | Sprint F4 |
| Video/music storage | Tidak ada | CDN (Cloudflare R2, murah) | Sprint F3 |

---

## BUDGET ESTIMATE FOUNDATION V2

| Item | Estimasi |
|------|----------|
| Claude API (hybrid routing testing) | ~$10 |
| Kling AI video (testing 20 video) | ~$5 |
| ElevenLabs music/TTS testing | ~$5 |
| Cycle 7 training (Vast.ai) | ~$0.50 |
| Cycle 8 training (Vast.ai) | ~$0.75 |
| Cloudflare R2 storage (25GB) | ~$1.50 |
| **TOTAL 5 SPRINT** | **~$23** |

---

## DECISION YANG PERLU FAHMI JAWAB SEBELUM MULAI

**D1 — Base Model Upgrade Kapan?**
- Qwen3-8B: bisa langsung (5.2GB VRAM, masih muat di VPS) → reasoning naik signifikan
- Qwen3-14B: butuh ~10GB VRAM, mungkin butuh upgrade VPS RAM
- Qwen3-32B: butuh dedicated GPU server ($50-100/bulan)
*Rekomendasi: Qwen3-8B sekarang, evaluate setelah 2 cycle.*

**D2 — Video Generation Provider:**
- Kling AI ($0.14/video 5s) — terbaik sekarang, ada API
- Wan2.1 self-hosted — gratis tapi butuh GPU kuat
*Rekomendasi: Kling AI dulu, Wan2.1 setelah ada dedicated GPU.*

**D3 — Music Provider:**
- Suno API ($10/bulan unlimited) — paling mudah
- AudioCraft self-hosted — gratis tapi heavy
*Rekomendasi: Suno API.*

**D4 — File Storage:**
- Cloudflare R2 ($0.015/GB/bulan) — murah, global CDN
- VPS local — gratis tapi tidak scalable
*Rekomendasi: Cloudflare R2 dari awal.*

---

## KAPAN FOUNDATION V2 SELESAI?

```
Day 68-74:  Sprint F1 — Hybrid Brain ✓
Day 75-81:  Sprint F2 — Coding Suite ✓
Day 82-88:  Sprint F3 — Creation Suite ✓
Day 89-95:  Sprint F4 — Data & Report ✓
Day 96-103: Sprint F5 — Cognitive Engine ✓

Day 103: ADO Foundation V2 COMPLETE
         → 35 tools, hybrid brain, full creation suite
         → Stable, scalable, ready untuk klien serius
```

Setelah Day 103, setiap minggu adalah **iterasi kecil** — tambah domain, polish tool, onboard klien baru. Fondasi tidak perlu diubah lagi.
