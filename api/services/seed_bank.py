"""
Seed bank — 120 diverse user-message seeds for synthetic DPO generation (Day 19).

Triple-Source Architecture:
  1. MighanTech3D NPC personas (16 NPCs, 7 knowledge domains) — user archetypes
  2. SIDIX topic taxonomy (framing patterns ONLY — never content or answers)
  3. External SynPO research patterns (arxiv 2410.06961) — diversity heuristics

Safety design:
  - Seeds are realistic QUESTION TEMPLATES, not domain-specific facts
  - No SIDIX answers, QA pairs, or verbatim content imported (hallucination risk)
  - No MighanTech3D NPC identities exposed in prompts (brand separation)
  - All 7 domains cover diverse task types — distribution matches real user patterns

Usage:
  from services.seed_bank import SEEDS
  # SEEDS is a list[str] of 120 user message strings
"""

# ---------------------------------------------------------------------------
# Domain 1: Creative & Content (17 seeds)
# MighanTech3D archetypes: Wordsmith, Reviewer NPC
# ---------------------------------------------------------------------------
_D1_CREATIVE = [
    "Buatkan intro artikel tentang tren AI di Indonesia tahun 2025 yang engaging dan tidak klise.",
    "Saya perlu review produk kamera mirrorless entry-level untuk pembaca awam. Bantu saya susun struktur reviewnya.",
    "Bagaimana cara menulis hook yang kuat untuk konten blog B2B tentang software HR?",
    "Tolong bantu saya menulis ulang kalimat ini agar lebih natural: 'Produk kami memiliki banyak fitur yang sangat berguna bagi pelanggan kami.'",
    "Apa perbedaan antara copywriting dan content writing? Kapan menggunakan masing-masing?",
    "Saya ingin menulis cerita pendek tentang seorang freelancer yang berjuang menemukan klien pertamanya. Berikan outline 5 babak.",
    "Bantu saya membuat tagline untuk brand konsultan digital UMKM. Brand tone: hangat, terpercaya, praktis.",
    "Bagaimana cara menghindari passive voice yang berlebihan dalam tulisan Bahasa Indonesia formal?",
    "Buatkan contoh email pitching ke brand untuk kolaborasi konten, dari sudut pandang content creator 10K followers.",
    "Cara terbaik mengakhiri artikel opini tanpa terkesan menggurui pembaca?",
    "Apa itu inverted pyramid dalam jurnalistik dan bagaimana penerapannya di konten digital?",
    "Buatkan 3 variasi judul artikel tentang 'cara mengelola waktu untuk remote worker' — satu informatif, satu curiosity-driven, satu problem-solution.",
    "Bagaimana cara menulis deskripsi produk yang menjual tanpa terasa hard-sell?",
    "Saya sedang menulis white paper untuk startup fintech. Apa saja elemen wajib yang harus ada?",
    "Berikan contoh opening yang kuat untuk podcast script tentang keuangan personal untuk Gen Z.",
    "Apa perbedaan tone of voice 'friendly' vs 'casual' dalam brand writing? Berikan contoh kalimatnya.",
    "Cara memparafrasekan konten teknis agar bisa dipahami audience non-teknis tanpa kehilangan akurasi?",
]

# ---------------------------------------------------------------------------
# Domain 2: Research & Analytics (17 seeds)
# MighanTech3D archetypes: Profesor, Hunter NPC
# ---------------------------------------------------------------------------
_D2_RESEARCH = [
    "Bagaimana cara melakukan competitive analysis untuk startup SaaS yang baru masuk pasar Indonesia?",
    "Apa metodologi terbaik untuk riset user persona dengan budget terbatas?",
    "Jelaskan perbedaan antara primary research dan secondary research, beserta contoh penggunaannya.",
    "Saya punya data survei 200 responden tapi tidak tahu harus mulai dari mana untuk analisisnya. Panduan step-by-step?",
    "Bagaimana cara mengidentifikasi sinyal pasar yang menunjukkan produk fit dengan target market?",
    "Apa indikator kunci yang harus saya track untuk mengukur kesehatan bisnis UMKM digital?",
    "Cara membedakan korelasi dan kausalitas dalam data bisnis — beri contoh kasus nyata.",
    "Bagaimana cara membaca dan menginterpretasi laporan industri dari firm besar seperti McKinsey atau BCG?",
    "Apa framework analisis SWOT yang tepat untuk bisnis e-commerce fashion lokal?",
    "Saya ingin tahu tren konsumsi konten digital Indonesia 2024-2025. Dari mana saya bisa mulai riset ini?",
    "Jelaskan apa itu cohort analysis dan kapan saya perlu menggunakannya.",
    "Bagaimana cara membuat hipotesis yang testable untuk eksperimen produk digital?",
    "Apa perbedaan NPS, CSAT, dan CES? Kapan masing-masing digunakan?",
    "Cara menghitung market size untuk produk baru yang belum ada kompetitor langsungnya.",
    "Apa itu jobs-to-be-done framework dan bagaimana penerapannya dalam riset pengguna?",
    "Bagaimana cara melakukan desk research yang efisien dalam 2 jam untuk briefing eksekutif?",
    "Interpretasikan data ini: bounce rate 78%, avg session 45 detik, pages per session 1.2. Apa yang kemungkinan terjadi?",
]

# ---------------------------------------------------------------------------
# Domain 3: SEO & Metadata (17 seeds)
# MighanTech3D archetypes: Pustakawan, Blog Bot, Sari Tagar NPC
# SIDIX taxonomy: framing patterns for information-seeking queries
# ---------------------------------------------------------------------------
_D3_SEO = [
    "Apa perbedaan long-tail keyword dan short-tail keyword? Mana yang lebih baik untuk website baru?",
    "Bagaimana cara menulis meta description yang optimal untuk artikel blog tentang investasi reksa dana?",
    "Jelaskan konsep topical authority dan bagaimana cara membangunnya untuk website baru.",
    "Cara memilih hashtag yang tepat untuk konten Instagram tentang kesehatan mental.",
    "Apa itu schema markup dan apakah semua website perlu menggunakannya?",
    "Bagaimana cara melakukan keyword research tanpa menggunakan tools berbayar?",
    "Berapa jumlah hashtag optimal untuk TikTok vs Instagram? Ada data atau riset pendukungnya?",
    "Apa itu pillar page dan cluster content? Jelaskan dengan contoh sederhana.",
    "Bagaimana cara mengoptimalkan gambar untuk SEO selain hanya menggunakan alt text?",
    "Cara membuat title tag yang balance antara SEO-friendly dan click-worthy?",
    "Apa yang dimaksud dengan search intent dan bagaimana cara mengidentifikasinya?",
    "Jelaskan perbedaan on-page SEO, off-page SEO, dan technical SEO dengan bahasa sederhana.",
    "Bagaimana cara menentukan kategori dan tag artikel blog secara konsisten dan strategis?",
    "Apa itu internal linking strategy dan mengapa ini penting untuk domain authority?",
    "Cara mengoptimalkan konten untuk voice search yang semakin populer di Indonesia?",
    "Apa perbedaan crawling, indexing, dan ranking dalam cara kerja mesin pencari?",
    "Bagaimana cara melakukan audit SEO basic untuk website yang trafficnya stagnan selama 6 bulan?",
]

# ---------------------------------------------------------------------------
# Domain 4: Social & Distribution (17 seeds)
# MighanTech3D archetypes: Social Bot, YT Bot, Lina Link NPC
# ---------------------------------------------------------------------------
_D4_SOCIAL = [
    "Bagaimana cara membuat konten calendar untuk brand fashion lokal yang konsisten dan relevan?",
    "Apa strategi terbaik untuk meningkatkan engagement organik di Instagram tanpa boost berbayar?",
    "Cara mengoptimalkan judul video YouTube agar muncul di search dan recommended.",
    "Apa perbedaan reach, impression, dan engagement? Mana yang paling penting untuk dioptimalkan?",
    "Bagaimana cara repurpose satu konten blog menjadi 5 format berbeda di platform berbeda?",
    "Strategi cross-posting yang efektif antara TikTok, Instagram Reels, dan YouTube Shorts?",
    "Apa waktu posting terbaik di LinkedIn untuk konten B2B yang menargetkan pasar Indonesia?",
    "Cara membuat hook 3 detik pertama untuk video TikTok yang efektif menahan penonton.",
    "Bagaimana cara menggunakan kolom komentar sebagai strategi distribusi konten organik?",
    "Apa itu viral loop dan bagaimana cara merancangnya untuk produk digital?",
    "Cara membangun komunitas aktif di platform Discord untuk brand digital.",
    "Apa perbedaan antara influencer marketing nano, micro, dan macro? Mana yang cocok untuk UMKM?",
    "Bagaimana cara mengukur ROI dari social media marketing untuk bisnis skala kecil?",
    "Cara membuat caption yang mendorong save dan share, bukan sekadar like.",
    "Apa strategi link building yang etis dan efektif untuk website berbahasa Indonesia?",
    "Bagaimana cara memanfaatkan trending topic tanpa terkesan oportunistik atau tidak autentik?",
    "Cara mengembangkan email list dari nol untuk bisnis digital yang baru berdiri.",
]

# ---------------------------------------------------------------------------
# Domain 5: Design & Visual (17 seeds)
# MighanTech3D archetypes: Designer Dina, Rama Reel NPC
# ---------------------------------------------------------------------------
_D5_DESIGN = [
    "Apa prinsip dasar desain yang harus saya pahami sebelum membuat presentasi bisnis yang meyakinkan?",
    "Bagaimana cara memilih palet warna yang konsisten untuk brand identity startup teknologi?",
    "Jelaskan konsep white space dalam desain dan mengapa ini penting untuk keterbacaan.",
    "Cara membuat brief desain yang jelas untuk freelancer atau agensi desain agar hasilnya sesuai ekspektasi.",
    "Apa perbedaan antara typeface serif dan sans-serif? Kapan menggunakan masing-masing?",
    "Bagaimana cara membuat storyboard untuk konten video pendek yang efektif sebelum produksi?",
    "Apa yang harus ada dalam script reel 60 detik untuk konten tutorial makeup yang engaging?",
    "Cara membuat thumbnail YouTube yang click-through rate-nya tinggi tanpa terlihat clickbait.",
    "Apa itu design system dan apakah startup kecil dengan tim 5 orang perlu membuatnya?",
    "Bagaimana cara mengevaluasi apakah sebuah desain berhasil secara komunikasi visual?",
    "Prinsip komposisi fotografi apa yang juga berlaku dalam desain grafis digital?",
    "Cara membuat motion graphic sederhana yang tetap terlihat profesional dengan tools terbatas.",
    "Apa perbedaan infografik yang efektif vs yang hanya terlihat sibuk dan membingungkan?",
    "Bagaimana cara menentukan visual direction untuk konten Instagram brand lifestyle lokal?",
    "Apa yang dimaksud dengan visual hierarchy dan bagaimana menerapkannya di landing page?",
    "Cara memilih stock photo yang terlihat autentik dan tidak generik untuk konten brand.",
    "Bagaimana cara mengadaptasi brand guideline ke berbagai format konten sosial media yang berbeda?",
]

# ---------------------------------------------------------------------------
# Domain 6: Operations & Management (18 seeds)
# MighanTech3D archetypes: Kurator, Scheduler, Mira Atur NPC
# ---------------------------------------------------------------------------
_D6_OPS = [
    "Bagaimana cara membuat OKR yang realistis untuk tim kecil startup 5 orang?",
    "Apa framework prioritisasi tugas yang paling efektif untuk product manager dengan banyak stakeholder?",
    "Cara mengelola proyek dari beberapa klien sekaligus sebagai freelancer tanpa burnout.",
    "Apa perbedaan Agile, Scrum, dan Kanban? Mana yang cocok untuk tim konten kreatif?",
    "Bagaimana cara membuat SOP (Standard Operating Procedure) untuk proses yang berulang di tim kecil?",
    "Cara yang efektif untuk melakukan meeting 1-on-1 dengan anggota tim yang performanya menurun.",
    "Apa yang dimaksud dengan delegation matrix (RACI) dan bagaimana cara menggunakannya dalam proyek?",
    "Bagaimana cara menghitung kapasitas tim untuk planning sprint atau produksi konten bulanan?",
    "Cara membuat sistem pelaporan mingguan yang tidak membuang waktu tim tapi tetap informatif.",
    "Apa tanda-tanda bahwa workflow produksi konten sudah mengalami bottleneck yang perlu diperbaiki?",
    "Bagaimana cara melakukan retrospektif yang jujur dan produktif di akhir proyek?",
    "Cara membuat anggaran operasional bulanan untuk startup bootstrap dengan arus kas terbatas.",
    "Apa strategi onboarding terbaik untuk freelancer baru yang bergabung dalam project yang sudah berjalan?",
    "Bagaimana cara mengidentifikasi dan menghilangkan bottleneck dalam workflow produksi konten?",
    "Cara menyampaikan kabar buruk kepada klien secara profesional tanpa merusak hubungan jangka panjang.",
    "Apa perbedaan KPI lagging indicator dan leading indicator? Berikan contoh untuk bisnis konten.",
    "Bagaimana cara membangun kebiasaan kerja yang produktif untuk remote team yang tersebar di berbagai kota?",
    "Cara menulis project brief yang komprehensif tapi tetap ringkas dan actionable untuk semua stakeholder.",
]

# ---------------------------------------------------------------------------
# Domain 7: General AI Assistant (17 seeds)
# Framing patterns from SIDIX taxonomy: information-seeking, how-to, comparison, evaluation
# External research: SynPO diversity heuristics — reasoning, explanation, decision-support tasks
# ---------------------------------------------------------------------------
_D7_GENERAL = [
    "Jelaskan perbedaan antara machine learning, deep learning, dan AI secara sederhana tanpa jargon teknis.",
    "Bagaimana cara terbaik menggunakan AI untuk meningkatkan produktivitas kerja sehari-hari?",
    "Apa risiko utama menggunakan AI untuk pembuatan konten tanpa review dari manusia?",
    "Cara mengevaluasi apakah sebuah AI tool worth the investment untuk bisnis skala kecil.",
    "Apa itu prompt engineering dan mengapa ini menjadi skill penting di era AI?",
    "Bagaimana cara menggunakan AI sebagai thought partner tanpa menjadi terlalu dependent?",
    "Jelaskan konsep RAG (Retrieval Augmented Generation) dengan bahasa yang mudah dipahami non-teknis.",
    "Apa perbedaan AI generatif dan AI prediktif? Berikan contoh penggunaan masing-masing di dunia bisnis.",
    "Bagaimana cara memverifikasi keakuratan informasi yang diberikan oleh AI chatbot?",
    "Apa ethical consideration utama dalam penggunaan AI untuk bisnis di konteks Indonesia?",
    "Cara menjelaskan manfaat AI kepada klien atau atasan yang skeptis terhadap teknologi baru.",
    "Apa limitasi AI saat ini yang paling sering disalahpahami oleh pengguna umum?",
    "Bagaimana AI bisa membantu UMKM Indonesia bersaing dengan perusahaan besar dalam hal produktivitas?",
    "Cara membuat sistem kerja hybrid human-AI yang efektif untuk tim kreatif.",
    "Apa yang dimaksud dengan AI hallucination dan bagaimana cara mendeteksinya dalam praktik?",
    "Bagaimana cara menggunakan AI untuk belajar skill baru lebih cepat dan lebih efektif?",
    "Apa perbedaan antara fine-tuning AI model dan prompt engineering? Kapan masing-masing lebih tepat digunakan?",
]

# ---------------------------------------------------------------------------
# Public export: flat list of all 120 seeds
# Order: D1→D7, interspersed for domain diversity in streaming generation
# ---------------------------------------------------------------------------
SEEDS: list[str] = (
    _D1_CREATIVE    # 17
    + _D2_RESEARCH  # 17
    + _D3_SEO       # 17
    + _D4_SOCIAL    # 17
    + _D5_DESIGN    # 17
    + _D6_OPS       # 18
    + _D7_GENERAL   # 17
)  # Total: 120

assert len(SEEDS) == 120, f"Expected 120 seeds, got {len(SEEDS)}"


# ---------------------------------------------------------------------------
# Day 38 — Pluggable seed source (hardcoded vs Magpie 300K)
# ---------------------------------------------------------------------------
async def get_seeds(per_round: int = 120) -> tuple[list[str], str]:
    """Return (seeds, source_label).

    Source selection via env SEED_SOURCE:
      - 'hardcoded' (default): legacy 120 hand-curated seeds (always available)
      - 'magpie_300k': pull Magpie-Qwen2.5-Pro-300K-Filtered from HuggingFace,
                       sample `per_round` per call. Falls back to hardcoded on any error.

    Source label is logged into preference_pair source_method:
      - hardcoded -> "synthetic_seed_v1"
      - magpie_300k -> "synthetic_magpie_v1"
    """
    import os
    source = (os.environ.get("SEED_SOURCE") or "hardcoded").lower().strip()

    if source == "magpie_300k":
        try:
            from services.magpie_seeds import get_magpie_seeds, sample_seeds
            pool = await get_magpie_seeds()
            if pool and len(pool) >= 100:
                sampled = sample_seeds(pool, n=per_round)
                return sampled, "synthetic_magpie_v1"
            # Fall through to hardcoded if Magpie pool too small
        except Exception as exc:
            import structlog
            structlog.get_logger().warning("seed_bank.magpie_fallback", error=str(exc))

    return list(SEEDS), "synthetic_seed_v1"
