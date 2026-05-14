# Sprint 2 Code Lab Design — Pyodide Sandbox + Rasa Sakit/Senang

**Date:** 2026-05-14 (Day 73)
**Sprint:** 2 (Day 74-80)
**Principle Tag:** Akal (Prefrontal Cortex sim-before-act) + Nafs (Self-awareness scoring)
**Facility Area:** B. TANGAN (Creative & Code Lab) + E. PERTUMBUHAN (Self-Improvement)

---

## 1. PROBLEM STATEMENT

Migan saat ini bisa **generate kode** lewat tool `run_python` (subprocess isolation), tapi BELUM:
- Eksekusi → observe → critique → iterate (autonomous learning loop)
- Score signal per execution (rasa sakit/senang)
- Write lessons ke `nafs`/`hikmah` bucket
- Pattern accumulation across executions

**Visi:** Migan harus "merasa" kode efisien vs boros, "sakit" saat error, "senang" saat success. Bukan blanket — adaptive per context.

---

## 2. ARCHITECTURE OVERVIEW

```
User: "Tulis fungsi sort yang efficient"
   ↓
Brain: write code attempt #1
   ↓
[Code Lab Service]
   ↓ submit to sandbox
   ├─ Pyodide (browser) — for safe, fast, no Docker overhead
   └─ Docker exec (fallback for non-Python)
   ↓
Capture: stdout, stderr, exit_code, elapsed_ms, memory_used
   ↓
[Scoring Layer] — adaptive based on task type
   ├─ success+fast → score +0.8 (rasa senang)
   ├─ success+slow → score +0.3 (mixed)
   ├─ error syntax → score -0.5 (mild rasa sakit)
   ├─ error runtime → score -0.8 (rasa sakit)
   └─ timeout → score -0.9 (heavy rasa sakit)
   ↓
[Decision: Iterate or Save?]
   ├─ score < 0 AND has retry budget → critique + iterate
   ├─ score > 0.7 → save pattern ke `hikmah` bucket
   ├─ multiple attempts → save lesson ke `nafs` bucket
   └─ casual code → no save (adaptive — bukan blanket)
   ↓
Return final result + (optional) citation chip
```

---

## 3. SCOPING — Adaptive, NOT Blanket

Per Adaptive Design Doctrine, Code Lab tidak selalu invoked:

| Context | Code Lab? | Why |
|---------|-----------|-----|
| User: "buat fungsi sort" | ✅ YES (write+execute+verify) | Concrete code task |
| User: "jelasin algoritma sorting" | ❌ NO (just explain) | Educational, no exec needed |
| User: "kira-kira efisien gak ya?" | ❌ NO (opinion) | Discussion mode |
| User: "test kode ini: ..." | ✅ YES (paste + exec) | Explicit eval request |
| User: "improve kode kemarin" | ✅ YES (load + iterate) | Memory + exec |
| User: "best practice Python?" | ❌ NO (KB recall + cite) | Knowledge lookup |
| Brain self-decides important | ✅ MAYBE (simulate before commit) | Akal/Prefrontal active |

**Decision rule:**
- Has executable code intent → activate Code Lab
- Theoretical/opinion → skip Code Lab, use KB
- Brain detect uncertainty in own code → optional simulate

---

## 4. PYODIDE vs DOCKER — Decision

**Pyodide (browser/sandbox-js):**
- ✅ Fast startup (<1s)
- ✅ Truly sandboxed (no host escape)
- ✅ No Docker overhead per execution
- ✅ Python 3.11 + numpy/pandas/matplotlib subset
- ❌ Limited to Python stdlib + pure-Python libs (no C-ext easily)
- ❌ No network access (good for safety)
- ❌ Subset of standard packages

**Docker exec (container per task):**
- ✅ Full Linux + any language
- ✅ Real network (if permitted)
- ✅ Native C extensions work
- ❌ Slow startup (3-10s)
- ❌ Resource heavy
- ❌ Security careful (container escape risks)

**Decision:**
- **Primary: Pyodide** for 95% Python tasks (math, string, basic ML, algorithms)
- **Fallback: Docker** for tasks needing C-ext or non-Python
- **Brain decides** via tool routing: if user query mentions "numpy/pandas/torch" → may need Docker; else Pyodide

**Adoption count:** 1 (Pyodide WASM binary, no framework deps)

---

## 5. API DESIGN

### New service: `api/services/code_lab.py` (~250 LOC)

```python
class CodeLabResult:
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    elapsed_ms: int
    memory_kb: int
    sandbox: str  # 'pyodide' | 'docker'
    score: float  # -1.0 to +1.0 (rasa sakit/senang)
    feeling: str  # 'senang' | 'biasa' | 'sakit' | 'sangat_sakit'

async def execute_code(
    code: str,
    language: str = 'python',
    timeout_s: int = 30,
    sandbox: str = 'auto',  # auto-pick pyodide/docker
) -> CodeLabResult:
    ...
```

### Scoring algorithm (adaptive):

```python
def compute_score(result: CodeLabResult) -> float:
    if not result.success:
        if result.exit_code == -1:  # timeout
            return -0.9
        if 'SyntaxError' in result.stderr:
            return -0.5
        return -0.7
    # success
    base_score = 0.5
    if result.elapsed_ms < 100:
        base_score += 0.3  # fast bonus
    elif result.elapsed_ms > 5000:
        base_score -= 0.2  # slow penalty
    return min(base_score, 1.0)
```

### Lesson capture (adaptive):

```python
async def maybe_save_lesson(
    code: str, result: CodeLabResult, context: dict
) -> bool:
    """Save lesson ONLY when adds value."""
    # Don't save if: casual exploration, trivial code, single attempt success
    if context.get('intent') == 'casual':
        return False
    if len(code) < 50 and result.success:
        return False  # too trivial

    # Save if: pattern emerges, failure with fix, milestone success
    if result.feeling == 'senang' and context.get('complexity') == 'high':
        # Save to `hikmah` (wisdom) bucket
        await memory_write(bucket='hikmah', content=f"Pattern berhasil: {summarize(code)}", score=result.score)
        return True
    if result.feeling.startswith('sakit') and context.get('retry_count', 0) > 0:
        # Save to `nafs` (self-awareness) bucket
        await memory_write(bucket='nafs', content=f"Belajar dari gagal: {result.stderr[:200]}", score=result.score)
        return True
    return False
```

---

## 6. PYODIDE INTEGRATION

### Approach: server-side Pyodide via Node.js

Pyodide runs natively in browser, but for backend code execution, options:
1. **pyodide-node** (npm package) — Pyodide loaded in Node.js subprocess
2. **WebWorker pool** in browser (kalau brain delegates to frontend)
3. **Browser bookmark approach** — sandbox via headless Chrome

**Decision:** option 1 (pyodide-node). Reasons:
- Pure Node.js, simple Docker
- No headless browser overhead
- Can pool processes for concurrency
- Existing hyperx-browser pattern di /opt/sidix/tools/ shows we can integrate Node services

### Subprocess pattern:

```python
# api/services/code_lab.py
import subprocess
import asyncio
import json

async def run_pyodide(code: str, timeout_s: int = 30) -> dict:
    """Spawn pyodide-node subprocess for safe Python exec."""
    proc = await asyncio.create_subprocess_exec(
        'node', '/opt/migancore/codelab/pyodide_runner.js',
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=code.encode()),
            timeout=timeout_s,
        )
        result = json.loads(stdout)
        return result
    except asyncio.TimeoutError:
        proc.kill()
        return {'success': False, 'exit_code': -1, 'stderr': 'TIMEOUT'}
```

### Node.js runner (`pyodide_runner.js`):

```javascript
const { loadPyodide } = require("pyodide");

(async () => {
    const pyodide = await loadPyodide();
    const code = require('fs').readFileSync(0, 'utf-8');
    const t0 = Date.now();
    try {
        const result = await pyodide.runPythonAsync(code);
        console.log(JSON.stringify({
            success: true,
            stdout: String(result || ''),
            stderr: '',
            elapsed_ms: Date.now() - t0,
        }));
    } catch (err) {
        console.log(JSON.stringify({
            success: false,
            stdout: '',
            stderr: err.message,
            elapsed_ms: Date.now() - t0,
        }));
    }
})();
```

---

## 7. INTEGRATION dengan EXISTING TOOL run_python

Sekarang ada `run_python` di tool_executor.py (subprocess isolation). Code Lab BUKAN replace, tapi extend:

```python
# Existing: tool_executor._python_repl
# New: services.code_lab.execute_code

# Behavior:
# - User explicit "jalankan kode X" → tool run_python (manual)
# - Brain autonomous decide to verify → services.code_lab (auto)
# - Code Lab wraps run_python + adds scoring + lesson capture
```

Tool router stays: explicit run_python via tool. Code Lab via brain's internal decision (Akal layer).

---

## 8. UI SURFACE (frontend impact)

### Chat UI extensions:

Saat Code Lab activated (adaptive):
- Inline code block dengan **run indicator** (▶ running)
- Output preview (success → green, error → orange)
- Score chip ONLY if user explicitly explore or if multiple iterations
- Hide chip otherwise (per adaptive doctrine)

```html
<div class="code-result success">
  <pre>def sort_fast(arr): ...</pre>
  <div class="meta">✓ 47ms · pyodide</div>  <!-- minimal, no over-cite -->
</div>
```

### Backlog SSOT — Code Lab logs:

New tab? NO — extend existing.
- Lessons ke `hikmah` bucket → already surface di SSOT Lessons tab
- Self-awareness ke `nafs` bucket → new bucket in memory_search

---

## 9. ROLLOUT PLAN (Sprint 2 — Day 74-80)

| Day | Deliverable |
|-----|-------------|
| Day 74 | code_lab.py service skeleton + Pyodide-node subprocess wiring |
| Day 75 | Scoring layer (rasa sakit/senang) + adaptive activation rules |
| Day 76 | Lesson capture (hikmah/nafs buckets) |
| Day 77 | Integration test: brain submits code → executes → saves lesson |
| Day 78 | UI surface (minimal, adaptive citation) |
| Day 79 | QA + adversarial tests (sandbox escape attempts) |
| Day 80 | Production deploy + observability + Sprint 2 closing log |

---

## 10. RISKS & MITIGATIONS

| Risk | Mitigation |
|------|-----------|
| Pyodide WASM heavy startup | Pool 2-3 warm subprocess workers |
| Code injection via prompt | Pyodide naturally isolated, no host access |
| Infinite loops | Hard timeout 30s, kill process |
| Memory exhaustion | Pyodide has 512MB limit by default |
| Brain over-uses Code Lab | Adaptive activation rule, not blanket |
| Score signal too noisy | Smooth via moving average, save lessons only sustained patterns |

---

## 11. METRICS TO TRACK

- **Code Lab activations/day** — should grow as Migan learns
- **Success rate** (success/total executions) — quality signal
- **Avg score** (rasa sakit/senang aggregate) — overall feeling
- **Lessons saved to hikmah** — wisdom accumulation
- **Lessons saved to nafs** — self-awareness growth
- **Iteration cycles per task** — efficiency improvement over time

---

## 12. VISION ALIGNMENT CHECK

- ✅ Akal (Prefrontal Cortex): simulate before commit pattern
- ✅ Nafs (self-awareness): scoring loop, lesson capture
- ✅ Biomimetic growth: rasa sakit/senang feedback (Fahmi's vision)
- ✅ Sandbox principle: safe environment for experimentation
- ✅ Pencernaan: lessons → hikmah bucket → retrieval next time
- ✅ Adaptive design: NOT every code → execute (only when justified)
- ✅ Tabayyun consult: brain can request judge teacher critique
- ✅ Saksi: audit log every execution preserved (UI hidden, backend logged)

---

## 13. WHY THIS SPRINT FIRST

Code Lab adalah **foundational** untuk:
- Sprint 3: Tool Autonomy MVP (brain propose new tools = needs simulate before commit)
- Sprint 5: User reaction probes (brain self-improve from feedback = needs scoring layer)
- Sprint 7: Coding katas (practice arena = needs Code Lab)
- Sprint 9: Video/3D modeling (advanced sandboxed exec)

Tanpa Code Lab, semua sprint downstream blocked.
