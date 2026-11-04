import { createSignal, onMount, For, Show } from "solid-js";

export default function App() {
  const [activeTab, setActiveTab] = createSignal("studio");
  const [authStatus, setAuthStatus] = createSignal({ is_authenticated: false, loading: true });
  const [skills, setSkills] = createSignal([]);
  const [selectedSkill, setSelectedSkill] = createSignal("vertical_microdrama");
  
  // Single episode form
  const [promptInput, setPromptInput] = createSignal("");
  const [characterName, setCharacterName] = createSignal("Maya");
  const [characterRole, setCharacterRole] = createSignal("Auditor handal yang memegang bukti rahasia");
  const [isGenerating, setIsGenerating] = createSignal(false);
  const [pipelineProgress, setPipelineProgress] = createSignal(null);

  // Batch overnight form
  const [batchScripts, setBatchScripts] = createSignal("");
  const [queueStatus, setQueueStatus] = createSignal({ items: [], is_running: false });

  // Check Google Flow session status
  const checkAuth = async () => {
    try {
      const res = await fetch("/api/auth/flow/status");
      const data = await res.json();
      setAuthStatus({ is_authenticated: data.is_authenticated, loading: false });
    } catch (e) {
      setAuthStatus({ is_authenticated: false, loading: false, error: e.message });
    }
  };

  // Launch Google Flow Chrome Login Window
  const handleConnectFlow = async () => {
    try {
      await fetch("/api/auth/flow/login", { method: "POST" });
      setTimeout(checkAuth, 3000);
    } catch (e) {
      alert("Gagal meluncurkan login window: " + e.message);
    }
  };

  // Fetch storytelling skills
  const fetchSkills = async () => {
    try {
      const res = await fetch("/api/skills");
      const data = await res.json();
      setSkills(data.skills || []);
    } catch (e) {
      console.error("Gagal load skills:", e);
    }
  };

  // Fetch overnight batch queue
  const fetchQueue = async () => {
    try {
      const res = await fetch("/api/batch/status");
      const data = await res.json();
      setQueueStatus(data);
    } catch (e) {}
  };

  onMount(() => {
    checkAuth();
    fetchSkills();
    fetchQueue();
    const interval = setInterval(fetchQueue, 3000);
    return () => clearInterval(interval);
  });

  const handleStartGeneration = async () => {
    if (!promptInput()) return;
    setIsGenerating(true);
    setPipelineProgress({ step: "start", message: "Menginisialisasi naskah 5-Stage...", percent: 10 });

    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          idea: promptInput(),
          skill_id: selectedSkill(),
          characters: [
            {
              name: characterName(),
              static_features: characterRole(),
              dynamic_features: "Setelan blazer hitam rapi, sedikit kusut di kerah",
              is_visible: true,
            }
          ]
        })
      });
      const data = await res.json();
      setPipelineProgress({ step: "queued", message: "Task terkirim. ID: " + data.task_id, percent: 100 });
    } catch (e) {
      alert("Error generate: " + e.message);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleAddBatch = async () => {
    if (!batchScripts()) return;
    try {
      await fetch("/api/batch/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scripts: batchScripts().split("\n---\n").map(s => s.trim()).filter(Boolean),
          skill_id: selectedSkill(),
        })
      });
      setBatchScripts("");
      fetchQueue();
    } catch (e) {
      alert("Error queue: " + e.message);
    }
  };

  return (
    <div class="min-h-screen bg-[#0b0e14] text-slate-200 flex flex-col font-sans">
      {/* Top Header */}
      <header class="h-14 border-b border-[#1e293b] bg-[#121824]/80 backdrop-blur px-6 flex items-center justify-between sticky top-0 z-50">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-lg bg-gradient-to-tr from-[#00f0ff] to-[#ff007f] flex items-center justify-center font-black text-black text-sm shadow-[0_0_15px_rgba(0,240,255,0.4)]">
            MD
          </div>
          <span class="font-bold tracking-wide text-white text-base">
            MICRODRAMA <span class="text-[#00f0ff]">STUDIO</span>
          </span>
          <span class="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-cyan-950/80 text-cyan-400 border border-cyan-800">
            Solid.js Desktop
          </span>
        </div>

        {/* Global Google Flow Session Status Card */}
        <div class="flex items-center gap-4">
          <div class="flex items-center gap-2 text-xs px-3 py-1.5 rounded-lg border border-[#1e293b] bg-[#0b0e14]">
            <span class="text-slate-400">Google Flow:</span>
            <Show when={!authStatus().loading} fallback={<span class="text-slate-500 animate-pulse">Checking...</span>}>
              <Show when={authStatus().is_authenticated} fallback={
                <button onClick={handleConnectFlow} class="text-[#ff007f] font-semibold hover:underline flex items-center gap-1">
                  <span class="w-2 h-2 rounded-full bg-[#ff007f] animate-ping"></span> Belum Login (Klik Hubungkan)
                </button>
              }>
                <span class="text-[#00ff66] font-semibold flex items-center gap-1.5">
                  <span class="w-2 h-2 rounded-full bg-[#00ff66]"></span> Terkoneksi ($0 API)
                </span>
              </Show>
            </Show>
          </div>

          {/* Navigation Tabs */}
          <nav class="flex gap-1 bg-[#0b0e14] p-1 rounded-lg border border-[#1e293b]">
            <button
              onClick={() => setActiveTab("studio")}
              class={`px-3 py-1 rounded text-xs font-medium transition ${activeTab() === 'studio' ? 'bg-[#00f0ff] text-black shadow' : 'text-slate-400 hover:text-white'}`}
            >
              🎬 Studio Sutradara
            </button>
            <button
              onClick={() => setActiveTab("overnight")}
              class={`px-3 py-1 rounded text-xs font-medium transition ${activeTab() === 'overnight' ? 'bg-[#ff007f] text-white shadow' : 'text-slate-400 hover:text-white'}`}
            >
              🌙 Pabrik Overnight ({queueStatus().items?.length || 0})
            </button>
          </nav>
        </div>
      </header>

      {/* Main Content Area */}
      <main class="flex-1 p-6 max-w-7xl w-full mx-auto grid grid-cols-1 md:grid-cols-12 gap-6">
        <Show when={activeTab() === "studio"}>
          {/* Left Column: Script & Formula Form */}
          <div class="md:col-span-7 flex flex-col gap-5">
            <div class="p-5 rounded-xl border border-[#1e293b] bg-[#121824]/60 backdrop-blur flex flex-col gap-4">
              <div class="flex items-center justify-between border-b border-[#1e293b] pb-3">
                <h2 class="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <span>⚡</span> Formula Drama & Formula Sutradara
                </h2>
                <span class="text-xs font-mono text-[#00f0ff]">Mx-Shell 5-Stage Mode</span>
              </div>

              {/* Skills Dropdown */}
              <div class="flex flex-col gap-1.5">
                <label class="text-xs font-semibold text-slate-300">Pilih Formula Cerita</label>
                <select
                  value={selectedSkill()}
                  onChange={(e) => setSelectedSkill(e.target.value)}
                  class="bg-[#0b0e14] border border-[#1e293b] text-slate-100 rounded-lg p-2.5 text-xs focus:outline-none focus:border-[#00f0ff]"
                >
                  <For each={skills()}>
                    {(s) => (
                      <option value={s.id}>
                        {s.icon} {s.name} ({s.category})
                      </option>
                    )}
                  </For>
                </select>
              </div>

              {/* Character Details */}
              <div class="grid grid-cols-2 gap-3">
                <div class="flex flex-col gap-1.5">
                  <label class="text-xs font-semibold text-slate-300">Nama Karakter Utama</label>
                  <input
                    type="text"
                    value={characterName()}
                    onInput={(e) => setCharacterName(e.target.value)}
                    class="bg-[#0b0e14] border border-[#1e293b] text-slate-100 rounded-lg p-2 text-xs focus:outline-none focus:border-[#00f0ff]"
                  />
                </div>
                <div class="flex flex-col gap-1.5">
                  <label class="text-xs font-semibold text-slate-300">Peran & Ciri Khas</label>
                  <input
                    type="text"
                    value={characterRole()}
                    onInput={(e) => setCharacterRole(e.target.value)}
                    class="bg-[#0b0e14] border border-[#1e293b] text-slate-100 rounded-lg p-2 text-xs focus:outline-none focus:border-[#00f0ff]"
                  />
                </div>
              </div>

              {/* Script / Premise Input */}
              <div class="flex flex-col gap-1.5">
                <label class="text-xs font-semibold text-slate-300">Ide Cerita / Premise Episode</label>
                <textarea
                  rows="4"
                  value={promptInput()}
                  onInput={(e) => setPromptInput(e.target.value)}
                  placeholder="Contoh: Maya secara mengejutkan membanting laporan audit korupsi di depan meja bosnya yang arogan..."
                  class="bg-[#0b0e14] border border-[#1e293b] text-slate-100 rounded-lg p-3 text-xs focus:outline-none focus:border-[#00f0ff] resize-none leading-relaxed"
                />
              </div>

              {/* Action Buttons */}
              <button
                disabled={isGenerating() || !promptInput()}
                onClick={handleStartGeneration}
                class="w-full py-3 rounded-lg font-bold text-xs uppercase tracking-wider bg-gradient-to-r from-[#00f0ff] to-[#00b4d8] text-black shadow-[0_0_20px_rgba(0,240,255,0.3)] hover:opacity-95 disabled:opacity-50 transition"
              >
                {isGenerating() ? "Sedang Memproduksi..." : "🚀 Produksi Episode Sinematik 9:16"}
              </button>
            </div>
          </div>

          {/* Right Column: Realtime Inspector & Preview */}
          <div class="md:col-span-5 flex flex-col gap-5">
            <div class="p-5 rounded-xl border border-[#1e293b] bg-[#121824]/60 backdrop-blur flex flex-col gap-4">
              <h3 class="text-xs font-bold text-white uppercase tracking-wider border-b border-[#1e293b] pb-2">
                Inspector Kualitas Sutradara
              </h3>
              
              <div class="space-y-3 text-xs">
                <div class="flex items-start gap-2.5 p-3 rounded-lg bg-[#0b0e14] border border-[#1e293b]">
                  <span class="text-[#00f0ff] font-bold">🔒</span>
                  <div>
                    <div class="font-semibold text-slate-200">Atmosphere Lock Aktif</div>
                    <div class="text-[11px] text-slate-400 mt-0.5">ARRI Alexa 35mm f/2.8 locked color grading di semua cuts.</div>
                  </div>
                </div>

                <div class="flex items-start gap-2.5 p-3 rounded-lg bg-[#0b0e14] border border-[#1e293b]">
                  <span class="text-[#00ff66] font-bold">⚡</span>
                  <div>
                    <div class="font-semibold text-slate-200">Action Budget Validator</div>
                    <div class="text-[11px] text-slate-400 mt-0.5">Maks 2 mikro-aksi per shot untuk mencegah wajah leleh/morphing.</div>
                  </div>
                </div>

                <div class="flex items-start gap-2.5 p-3 rounded-lg bg-[#0b0e14] border border-[#1e293b]">
                  <span class="text-[#ff007f] font-bold">🎯</span>
                  <div>
                    <div class="font-semibold text-slate-200">Breath-Like Float & Diegetic Sound</div>
                    <div class="text-[11px] text-slate-400 mt-0.5">Kamera handheld alami dan audio produksi tanpa musik sintesis palsu.</div>
                  </div>
                </div>
              </div>

              {/* Progress Display */}
              <Show when={pipelineProgress()}>
                <div class="mt-2 p-3 rounded-lg bg-cyan-950/40 border border-cyan-800 text-xs">
                  <div class="flex justify-between font-mono text-[11px] text-cyan-300 mb-1">
                    <span>{pipelineProgress().message}</span>
                    <span>{pipelineProgress().percent}%</span>
                  </div>
                  <div class="w-full bg-[#0b0e14] h-1.5 rounded-full overflow-hidden">
                    <div class="bg-[#00f0ff] h-full transition-all" style={{ width: `${pipelineProgress().percent}%` }}></div>
                  </div>
                </div>
              </Show>
            </div>
          </div>
        </Show>

        <Show when={activeTab() === "overnight"}>
          {/* Overnight Batch Factory */}
          <div class="md:col-span-12 flex flex-col gap-5">
            <div class="p-5 rounded-xl border border-[#1e293b] bg-[#121824]/60 backdrop-blur flex flex-col gap-4">
              <div class="flex items-center justify-between border-b border-[#1e293b] pb-3">
                <div>
                  <h2 class="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                    <span>🌙</span> Pabrik Overnight (Ekspor Massal 5-10 Episode)
                  </h2>
                  <p class="text-xs text-slate-400 mt-1">
                    Tempelkan naskah beberapa episode dipisahkan tanda <code class="text-[#ff007f] font-mono">---</code>. Biarkan PC memproduksi semalaman secara otomatis.
                  </p>
                </div>
                <div class="flex items-center gap-2">
                  <button onClick={handleAddBatch} class="px-4 py-2 rounded-lg bg-[#ff007f] text-white font-bold text-xs shadow hover:opacity-90">
                    + Masukkan Antrean
                  </button>
                </div>
              </div>

              <textarea
                rows="6"
                value={batchScripts()}
                onInput={(e) => setBatchScripts(e.target.value)}
                placeholder={"Episode 1: Pertemuan rahasia di basemen...\n---\nEpisode 2: Konfrontasi di ruang dewan direksi..."}
                class="bg-[#0b0e14] border border-[#1e293b] text-slate-100 rounded-lg p-3 text-xs font-mono focus:outline-none focus:border-[#ff007f] resize-none leading-relaxed"
              />

              {/* Queue List Table */}
              <div class="mt-4 border border-[#1e293b] rounded-lg overflow-hidden bg-[#0b0e14]">
                <table class="w-full text-left text-xs">
                  <thead class="bg-[#121824] text-slate-400 font-mono uppercase text-[10px] border-b border-[#1e293b]">
                    <tr>
                      <th class="p-3">ID / Naskah</th>
                      <th class="p-3">Formula</th>
                      <th class="p-3">Status</th>
                      <th class="p-3">Waktu Masuk</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-[#1e293b]">
                    <Show when={queueStatus().items?.length > 0} fallback={
                      <tr>
                        <td colspan="4" class="p-6 text-center text-slate-500 font-mono">
                          Antrean saat ini kosong. Masukkan naskah untuk memulai produksi semalaman.
                        </td>
                      </tr>
                    }>
                      <For each={queueStatus().items}>
                        {(item) => (
                          <tr class="hover:bg-[#121824]/40">
                            <td class="p-3 font-mono text-slate-300 max-w-xs truncate">{item.id} - {item.idea?.slice(0, 50)}...</td>
                            <td class="p-3 text-slate-400">{item.skill_id}</td>
                            <td class="p-3">
                              <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-950 text-amber-400 border border-amber-800">
                                {item.status}
                              </span>
                            </td>
                            <td class="p-3 text-slate-500 font-mono text-[11px]">{new Date(item.created_at * 1000).toLocaleTimeString()}</td>
                          </tr>
                        )}
                      </For>
                    </Show>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
        </Show>
      </main>
    </div>
  );
}
