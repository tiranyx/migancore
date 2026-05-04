/* Migancore — Section components */

const NavBar = () => (
  <nav className="nav">
    <div className="brand">
      <span className="brand-mark">
        <svg viewBox="0 0 32 32" width="26" height="26">
          <defs>
            <linearGradient id="bg-grad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stopColor="#ffb060"/>
              <stop offset="1" stopColor="#d95e0e"/>
            </linearGradient>
          </defs>
          <rect x="2" y="2" width="28" height="28" rx="4" fill="none" stroke="url(#bg-grad)" strokeWidth="1.5"/>
          <path d="M9 22 L9 10 L16 18 L23 10 L23 22" fill="none" stroke="url(#bg-grad)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <circle cx="16" cy="16" r="2" fill="#2fe39a"/>
        </svg>
      </span>
      <span>MIGANCORE</span>
    </div>
    <div className="nav-links">
      <a href="#produk">Produk</a>
      <a href="#arsitektur">Arsitektur</a>
      <a href="#evolusi">Evolusi</a>
      <a href="https://api.migancore.com/docs">API</a>
      <a href="https://app.migancore.com/admin/">Dashboard</a>
    </div>
    <div className="nav-right">
      <span className="nav-status">v0.5.0 <b>LIVE</b><span className="dot-pulse"/></span>
      <a href="https://app.migancore.com" className="btn btn-primary">CHAT <IconArrowRight size={14}/></a>
    </div>
  </nav>
);

const Hero = () => {
  const [stats, setStats] = React.useState({ total_pairs: 277, by_source_method: { synthetic_seed_v1: 262, cai_pipeline: 15 } });
  React.useEffect(() => {
    const load = async () => {
      try {
        const r = await fetch('https://api.migancore.com/v1/public/stats');
        if (r.ok) setStats(await r.json());
      } catch {}
    };
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, []);
  const pairs = useCounter(stats.total_pairs || 277, 1800);
  const tokens = useCounter(14, 1800);
  const sources = Object.keys(stats.by_source_method || {}).length;
  const ready = Math.min(100, Math.round((stats.total_pairs || 0) / 1500 * 100));
  return (
  <section className="hero">
    <div className="panel panel-corners hot hero-card reveal">
      <div className="hero-meta">
        <span className="panel-label">◆ MISSION CONTROL</span>
        <span className="live-feed"><span className="dot-pulse"/> LIVE FEED</span>
      </div>
      <h1 className="hero-title">AI yang <span className="accent">Belajar</span><br/>Setiap <span className="accent">Minggu</span></h1>
      <p className="hero-sub">Migancore adalah Autonomous Digital Organism — Core Brain dengan SOUL.md identity, memori 3-tier, melahirkan agen anak, dan memperbaiki diri lewat training cycle. Open core, MCP-native, built in Indonesia.</p>
      <div className="hero-actions">
        <a className="btn btn-primary" href="https://app.migancore.com">COBA CHAT SEKARANG <IconArrowRight size={14}/></a>
        <a className="btn btn-ghost" href="#arsitektur">LIHAT ARSITEKTUR</a>
      </div>
      <div className="stat-row">
        <div className="stat"><div className="label">DPO PAIRS COLLECTED</div><div className="val">{Math.round(pairs)}</div></div>
        <div className="stat"><div className="label">TOKEN/DETIK (QWEN-7B)</div><div className="val">{Math.round(tokens)}</div></div>
      </div>
    </div>

    <div className="orb-wrap">
      <Orb/>
      <div className="orb-overlay"/>
      <div className="scan-line"/>
      <div style={{position:'absolute', top: 18, left: 18, fontFamily:'var(--mono)', fontSize: 10, color:'var(--text-mute)', letterSpacing:'0.2em'}}>
        MIGHAN-CORE // <span style={{color:'var(--green)'}}>SOUL.md ACTIVE</span>
      </div>
      <div style={{position:'absolute', top: 18, right: 18, fontFamily:'var(--mono)', fontSize: 10, color:'var(--text-mute)', letterSpacing:'0.2em'}}>
        v0.5.0
      </div>
    </div>

    <div style={{display:'flex', flexDirection:'column', gap: 18}} className="reveal">
      <div className="panel panel-corners-g diag-card">
        <h4>TRAINING READINESS <IconRocket size={14}/></h4>
        <div className="readiness-num">{ready}<small>%</small></div>
        <div className="readiness-bar"/>
        <div style={{fontFamily:'var(--mono)', fontSize: 10, color:'var(--text-mute)', marginTop: 6, letterSpacing:'0.1em'}}>
          {stats.total_pairs || 277} / 1500 pairs · target Cycle 1
        </div>
      </div>
      <div className="panel panel-corners-g diag-card">
        <h4>STACK STATUS <IconShield size={14}/></h4>
        <div className="diag-grid">
          <div className="diag-cell"><div className="l">POSTGRES</div><div className="v" style={{color:'var(--green)'}}>OK</div></div>
          <div className="diag-cell"><div className="l">QDRANT</div><div className="v" style={{color:'var(--green)'}}>OK</div></div>
          <div className="diag-cell"><div className="l">OLLAMA</div><div className="v" style={{color:'var(--green)'}}>OK</div></div>
          <div className="diag-cell"><div className="l">MCP</div><div className="v" style={{color:'var(--green)'}}>LIVE</div></div>
        </div>
      </div>
      <div className="panel panel-corners-g diag-card">
        <h4>DATA STREAM <span style={{color:'var(--orange)'}}>● REAL-TIME</span></h4>
        <div className="sparkline"><Sparkline color="#2fe39a"/></div>
      </div>
    </div>
  </section>
  );
};

const ProsesHex = ({ active }) => (
  <svg viewBox="0 0 100 110">
    <defs>
      <linearGradient id={`hg-${active ? 'a' : 'b'}`} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor={active ? '#ffb060' : 'rgba(47, 227, 154, 0.5)'}/>
        <stop offset="1" stopColor={active ? 'rgba(255, 138, 36, 0.1)' : 'rgba(47, 227, 154, 0.05)'}/>
      </linearGradient>
    </defs>
    <polygon points="50,4 92,28 92,80 50,104 8,80 8,28"
      fill={active ? 'rgba(255, 138, 36, 0.06)' : 'rgba(47, 227, 154, 0.04)'}
      stroke={active ? '#ff8a24' : 'rgba(47, 227, 154, 0.5)'}
      strokeWidth="1.4"
      className="hex-stroke"/>
    <polygon points="50,12 84,32 84,76 50,96 16,76 16,32"
      fill="none"
      stroke={active ? 'rgba(255, 138, 36, 0.4)' : 'rgba(47, 227, 154, 0.2)'}
      strokeWidth="0.8"
      strokeDasharray="2 3"/>
  </svg>
);

const Proses = () => {
  const steps = [
    { num: 'L1', name: 'The Seed', desc: 'VPS + Ollama + FastAPI + Postgres. First token, single agent loop, 3 tools.', icon: <IconStar size={36}/> },
    { num: 'L2', name: 'The Director', desc: 'LangGraph orchestrator + Letta memory + Qdrant + tool registry. Multi-tenant RLS.', icon: <IconAtom size={36}/> },
    { num: 'L3', name: 'The Factory', desc: '3 mode templates: customer_success, research_companion, code_pair. Specialist on demand.', icon: <IconCube size={36}/> },
    { num: 'L4', name: 'The Innovator', desc: 'CAI critique + synthetic + 4-teacher distillation. Weekly SimPO training.', icon: <IconHeart size={36}/>, active: true },
    { num: 'L5', name: 'The Breeder', desc: 'Spawn UI + genealogy tree D3.js. Setiap child inherits SOUL, gains specialization.', icon: <IconRocket size={36}/> },
  ];
  return (
    <section className="panel panel-corners section reveal">
      <div className="section-head">
        <div className="section-title">5 LEVEL EVOLUSI</div>
        <div style={{fontFamily:'var(--mono)', fontSize: 11, color:'var(--text-mute)', letterSpacing:'0.18em'}}>
          DARI SEED KE BREEDER
        </div>
      </div>
      <div className="proses">
        {steps.map((s, i) => (
          <div key={i} className={`proses-step ${s.active ? 'active' : ''}`}>
            <div className={`hex ${s.active ? 'active' : ''}`}>
              <ProsesHex active={s.active}/>
              <div className="hex-icon">{s.icon}</div>
            </div>
            <div className="proses-num">{s.num}</div>
            <div className="proses-name">{s.name}</div>
            <div className="proses-desc">{s.desc}</div>
          </div>
        ))}
      </div>
      <div className="progress-block">
        <div className="pl">PROGRES SPRINT — WEEK 4 COMPLETE</div>
        <div className="progress-bar"><div className="progress-fill" style={{width:'85%'}}/></div>
        <div className="progress-meta">
          <span>Day 35 · L1-L5 ✅ · MCP Server ✅ · Distillation Pipeline ✅ · Cycle 1 Training READY</span>
          <b>85%</b>
        </div>
      </div>
    </section>
  );
};

const Produk = () => {
  const items = [
    { name: 'MIGANCORE CORE', desc: 'Core Brain Engine: Qwen2.5-7B + LangGraph director + SOUL.md. Identitas persisten yang survive lintas model version.' },
    { name: 'MIGANCORE MEMORY', desc: 'Stack memori 3 tier: Redis K-V (instan), Qdrant semantic (jangka panjang), Letta working memory (konteks aktif).' },
    { name: 'MIGANCORE SPAWN', desc: 'Platform genealogi agen: kloning dengan persona turunan, silsilah tercatat di D3.js force-directed graph live di /admin/.' },
    { name: 'MIGANCORE MCP', desc: 'Streamable HTTP MCP server: 8 tools + 4 resources. Plug ke Claude Desktop, Cursor, Continue.dev. No vendor lock-in.' },
  ];
  return (
    <section id="produk" className="panel panel-corners section reveal">
      <div className="section-head">
        <div className="section-title">PRODUK UTAMA</div>
        <div style={{fontFamily:'var(--mono)', fontSize: 11, color:'var(--text-mute)', letterSpacing:'0.18em'}}>
          4 MODUL · 1 EKOSISTEM
        </div>
      </div>
      <div className="produk-grid">
        {items.map((p, i) => (
          <div key={i} className="produk-card reveal" onMouseMove={(e) => {
            const r = e.currentTarget.getBoundingClientRect();
            e.currentTarget.style.setProperty('--mx', ((e.clientX - r.left) / r.width * 100) + '%');
            e.currentTarget.style.setProperty('--my', ((e.clientY - r.top) / r.height * 100) + '%');
            const rx = ((e.clientY - r.top) / r.height - 0.5) * -6;
            const ry = ((e.clientX - r.left) / r.width - 0.5) * 6;
            e.currentTarget.style.transform = `perspective(800px) rotateX(${rx}deg) rotateY(${ry}deg) translateY(-3px)`;
          }} onMouseLeave={(e) => { e.currentTarget.style.transform = ''; }}>
            <div className="glow"/>
            <div className="produk-thumb"><ProductThumb variant={i}/></div>
            <h3 className="produk-name">{p.name}</h3>
            <p className="produk-desc">{p.desc}</p>
          </div>
        ))}
      </div>
    </section>
  );
};

const Arsitektur = () => {
  const left = [
    { n: 'SOUL.md IDENTITY', d: 'Persona permanen: nilai, suara, fingerprint test 0.85 cosine sim' },
    { n: 'CHAT MULTI-TURN', d: 'SSE streaming + history dari Postgres + heartbeat 15s' },
    { n: 'MEMORY INJECT', d: 'Redis K-V summary + Qdrant episodic retrieval → system prompt' },
    { n: 'TOOL REGISTRY', d: '8 tools: web_search, fal.ai gen, file R/W, memory, TTS' },
  ];
  const right = [
    { n: 'MCP SERVER', d: 'Streamable HTTP + JWT auth + 4 resources at /mcp/' },
    { n: 'AGENT SPAWN UI', d: 'Spawn modal + 3 mode templates + genealogy D3 tree' },
    { n: 'DISTILLATION PIPELINE', d: '4 teachers: Anthropic, Kimi K2.6, OpenAI, Gemini' },
    { n: 'TRAINING READY', d: 'SimPO + identity eval gate + GGUF hot-swap' },
  ];
  return (
    <section id="arsitektur" className="panel panel-corners section reveal">
      <div className="section-head">
        <div className="section-title">ARSITEKTUR SISTEM</div>
        <div style={{fontFamily:'var(--mono)', fontSize: 11, color:'var(--text-mute)', letterSpacing:'0.18em'}}>
          MODULAR · SCALABLE · RESILIENT
        </div>
      </div>
      <div className="arch-wrap">
        <div className="arch-side">
          <div>
            <p className="arch-intro">Arsitektur modular yang dirancang untuk skala kosmik, stabilitas tinggi, dan evolusi tanpa batas.</p>
            <a href="#arch-detail" className="btn btn-ghost arch-cta">LIHAT ARSITEKTUR <IconArrowRight size={14}/></a>
          </div>
          <div className="arch-nodes">
            {left.map(n => (
              <div key={n.n} className="arch-node">
                <span className="ndot"/>{n.n}
                <span className="tip">{n.d}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="arch-center">
          <div className="core-label">▣ MIGHAN-CORE v0.5.0</div>
          <ArchCore/>
          <div className="arch-bottom">
            <span className="arch-pill"><IconCircuit size={12}/> REDIS K-V</span>
            <span className="arch-pill"><IconNetwork size={12}/> QDRANT VECTOR</span>
            <span className="arch-pill"><IconBrain size={12}/> QWEN2.5-7B</span>
          </div>
        </div>
        <div className="arch-side">
          <div className="arch-nodes">
            {right.map(n => (
              <div key={n.n} className="arch-node">
                <span className="ndot"/>{n.n}
                <span className="tip">{n.d}</span>
              </div>
            ))}
          </div>
          <div style={{textAlign:'right', fontFamily:'var(--mono)', fontSize: 11, color:'var(--text-mute)', letterSpacing:'0.18em'}}>
            <div>INFERENCE · 14 tok/s</div>
            <div style={{color:'var(--green)'}}>● SSE STREAMING</div>
          </div>
        </div>
      </div>
    </section>
  );
};

const Evolusi = () => {
  const items = [
    { num: '01', name: 'OBSERVASI', desc: 'Setiap percakapan direkam. Feedback implisit (retry, panjang sesi) dikumpulkan otomatis. Episodic memory di Qdrant.', icon: <IconTelescope size={32}/> },
    { num: '02', name: 'FILTRASI', desc: 'CAI critique self-judge + tool-error filter. Margin filter score ≥2.0 masuk dataset training.', icon: <IconBrain size={32}/> },
    { num: '03', name: 'DISTILLATION', desc: '4 teacher LLMs (Anthropic, Kimi K2.6, GPT-4o, Gemini) generate chosen pairs. Independent judge.', icon: <IconBlocks size={32}/> },
    { num: '04', name: 'PELATIHAN', desc: 'SimPO + QLoRA + Unsloth di RunPod RTX 4090 (~$5.50/cycle). Identity eval gate ≥0.85 cosine sim.', icon: <IconExpand size={32}/> },
    { num: '05', name: 'EVOLUSI', desc: 'GGUF Q4_K_M hot-swap ke Ollama. A/B 24h. Promote v+1 atau rollback. Silsilah tercatat selamanya.', icon: <IconInfinity size={32}/> },
  ];
  return (
    <section id="evolusi" className="panel panel-corners section reveal">
      <div className="section-head">
        <div className="section-title">SIKLUS EVOLUSI</div>
        <div style={{fontFamily:'var(--mono)', fontSize: 11, color:'var(--text-mute)', letterSpacing:'0.18em'}}>
          ∞ FEEDBACK LOOP
        </div>
      </div>
      <div className="siklus">
        {items.map((s, i) => (
          <div key={i} className="siklus-card">
            <div className="siklus-icon">{s.icon}</div>
            <div className="siklus-num">{s.num}</div>
            <div className="siklus-name">{s.name}</div>
            <div className="siklus-desc">{s.desc}</div>
          </div>
        ))}
      </div>
      <div className="siklus-foot">— UMPAN BALIK BERKELANJUTAN —</div>
    </section>
  );
};

const DesignSystem = () => (
  <section id="ds" className="panel panel-corners section">
    <div className="section-head">
      <div className="section-title">DESIGN SYSTEM</div>
      <div style={{fontFamily:'var(--mono)', fontSize: 11, color:'var(--text-mute)', letterSpacing:'0.18em'}}>
        TOKENS · COMPONENTS · MOTION
      </div>
    </div>
    <div className="ds-grid">
      <div className="ds-card">
        <div className="ds-label">WARNA</div>
        <div className="swatch-row">
          <div className="swatch o"/>
          <div className="swatch g"/>
          <div className="swatch k"/>
          <div className="swatch w"/>
        </div>
      </div>
      <div className="ds-card">
        <div className="ds-label">TIPOGRAFI</div>
        <div className="type-display">Orbitron</div>
        <div className="type-sub">Inter / JetBrains Mono</div>
      </div>
      <div className="ds-card">
        <div className="ds-label">IKONOGRAFI</div>
        <div className="icon-grid">
          <IconStar/><IconAtom/><IconCube/><IconHeart/>
          <IconRocket/><IconCircuit/><IconNetwork/><IconInfinity/>
        </div>
      </div>
      <div className="ds-card">
        <div className="ds-label">KOMPONEN</div>
        <div className="cmp-grid">
          <div className="cmp-bar b1"/>
          <div className="cmp-bar b2"/>
          <div className="cmp-bar b3"/>
          <div className="cmp-bar b4"/>
        </div>
      </div>
      <div className="ds-card">
        <div className="ds-label">EFEK VISUAL</div>
        <div className="fx-canvas"/>
      </div>
    </div>
  </section>
);

const Launch = () => (
  <section id="konsole" className="launch reveal">
    <div className="launch-bg"/>
    <div className="launch-fire"/>
    <div className="planet"/>
    <div className="rocket"/>
    <div className="launch-content">
      <div className="launch-pre">v0.5.0 LIVE · WEEK 4 COMPLETE</div>
      <h2 className="launch-title">COBA SEKARANG</h2>
      <div className="launch-sub">AI YANG BENAR-BENAR HIDUP</div>
      <p className="launch-body">Bersama MIGANCORE, ngobrol dengan agent yang ingat semua, melahirkan child agent baru, dan memperbaiki diri setiap minggu. Open core, MCP-native, built in Indonesia.</p>
      <div className="launch-actions">
        <a className="btn btn-primary" href="https://app.migancore.com">CHAT SEKARANG <IconArrowRight size={14}/></a>
        <a className="btn btn-ghost" href="https://app.migancore.com/admin/">DASHBOARD <IconArrowRight size={14}/></a>
      </div>
      <div className="launch-foot">— THE SEED IS PATIENT. THE BREEDER IS HERE. —</div>
    </div>
  </section>
);

const Footer = () => (
  <footer className="foot">
    <div className="brand" style={{opacity:0.9}}>
      <span className="brand-mark">
        <svg viewBox="0 0 32 32" width="22" height="22">
          <rect x="2" y="2" width="28" height="28" rx="4" fill="none" stroke="#ff8a24" strokeWidth="1.5"/>
          <path d="M9 22 L9 10 L16 18 L23 10 L23 22" fill="none" stroke="#ff8a24" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <circle cx="16" cy="16" r="2" fill="#2fe39a"/>
        </svg>
      </span>
      <span style={{fontSize: 12}}>MIGANCORE</span>
      <span style={{fontFamily:'var(--mono)', fontSize: 11, color:'var(--text-mute)', marginLeft: 14}}>© 2026 TIRANYX · MIGANCORE · APACHE 2.0 (BULAN 3+)</span>
    </div>
    <div className="foot-links">
      <a href="https://app.migancore.com">Chat</a>
      <a href="https://app.migancore.com/admin/">Dashboard</a>
      <a href="https://api.migancore.com/docs">API</a>
      <a href="https://api.migancore.com/mcp/">MCP</a>
      <a href="https://api.migancore.com/health">Status</a>
    </div>
    <div className="foot-social">
      <a href="https://github.com/tiranyx/migancore" aria-label="GitHub (Bulan 3+)">GitHub</a>
    </div>
  </footer>
);

Object.assign(window, { NavBar, Hero, Proses, Produk, Arsitektur, Evolusi, DesignSystem, Launch, Footer });
