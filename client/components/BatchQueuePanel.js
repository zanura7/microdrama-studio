"use client";

import { useState, useEffect } from "react";
import {
  Moon,
  Play,
  Pause,
  RotateCcw,
  Trash2,
  CheckCircle2,
  Clock,
  Layers,
  Sparkles,
  ShieldCheck,
  Video,
  Download,
  Plus,
  FileText,
  AlertCircle,
  ExternalLink,
} from "lucide-react";

export default function BatchQueuePanel({ skills = [] }) {
  const [queueData, setQueueData] = useState({
    is_running: false,
    is_paused: false,
    stats: { total: 0, queued: 0, processing: 0, completed: 0, failed: 0 },
    items: [],
  });
  const [loading, setLoading] = useState(false);
  const [bulkText, setBulkText] = useState("");
  const [selectedSkill, setSelectedSkill] = useState("revenge_ceo");
  const [selectedStyle, setSelectedStyle] = useState("Cinematic");
  const [useStoryboardSheets, setUseStoryboardSheets] = useState(true);

  // Quick single add state
  const [singleTitle, setSingleTitle] = useState("");
  const [singleIdea, setSingleIdea] = useState("");
  const [inputMode, setInputMode] = useState("bulk"); // 'bulk' | 'single'

  const fetchQueue = async () => {
    try {
      const res = await fetch("/api/batch/status");
      if (res.ok) {
        const data = await res.json();
        setQueueData(data);
      }
    } catch (err) {
      console.error("Failed to fetch batch queue:", err);
    }
  };

  useEffect(() => {
    fetchQueue();
    const interval = setInterval(fetchQueue, 2500);
    return () => clearInterval(interval);
  }, []);

  const handleAddBulk = async (e) => {
    e.preventDefault();
    if (!bulkText.trim()) return;

    setLoading(true);
    // Parse episodes separated by '---' or double newline
    const rawEpisodes = bulkText
      .split(/\n\s*---\s*\n|\n{2,}/)
      .map((t) => t.trim())
      .filter((t) => t.length > 5);

    if (rawEpisodes.length === 0) {
      setLoading(false);
      return;
    }

    const items = rawEpisodes.map((epText, idx) => {
      const lines = epText.split("\n");
      let title = `Episode ${queueData.stats.total + idx + 1}`;
      let idea = epText;

      // If first line looks like a title (e.g., "Episode 1: ...")
      if (lines[0].toLowerCase().startsWith("ep") || lines[0].toLowerCase().startsWith("judul")) {
        title = lines[0].replace(/^(ep|judul)[\s\d:.-]*/i, "").trim() || lines[0];
        idea = lines.slice(1).join("\n").trim() || lines[0];
      }

      return {
        title,
        idea,
        style: selectedStyle,
        skill_id: selectedSkill,
        use_storyboard_sheets: useStoryboardSheets,
        mode: "idea2video",
      };
    });

    try {
      const res = await fetch("/api/batch/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items }),
      });
      if (res.ok) {
        setBulkText("");
        await fetchQueue();
      }
    } catch (err) {
      console.error("Failed to add bulk items:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddSingle = async (e) => {
    e.preventDefault();
    if (!singleIdea.trim()) return;

    setLoading(true);
    try {
      const res = await fetch("/api/batch/add-single", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: singleTitle.trim(),
          idea: singleIdea.trim(),
          style: selectedStyle,
          skill_id: selectedSkill,
          use_storyboard_sheets: useStoryboardSheets,
          mode: "idea2video",
        }),
      });
      if (res.ok) {
        setSingleTitle("");
        setSingleIdea("");
        await fetchQueue();
      }
    } catch (err) {
      console.error("Failed to add single item:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleStart = async () => {
    await fetch("/api/batch/start", { method: "POST" });
    fetchQueue();
  };

  const handlePause = async () => {
    await fetch("/api/batch/pause", { method: "POST" });
    fetchQueue();
  };

  const handleResume = async () => {
    await fetch("/api/batch/resume", { method: "POST" });
    fetchQueue();
  };

  const handleRetry = async (itemId) => {
    await fetch(`/api/batch/retry/${itemId}`, { method: "POST" });
    fetchQueue();
  };

  const handleDelete = async (itemId) => {
    await fetch(`/api/batch/${itemId}`, { method: "DELETE" });
    fetchQueue();
  };

  const handleClear = async () => {
    await fetch("/api/batch/clear", { method: "POST" });
    fetchQueue();
  };

  const { is_running, is_paused, stats, items } = queueData;

  return (
    <div className="space-y-6">
      {/* Top Banner: Overnight Engine Rules & Anti-Ban Info */}
      <div className="paper-card p-5 border-l-4 border-l-[#c25e40]">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Moon className="w-5 h-5 text-[#c25e40]" />
              <h2 className="text-base font-bold text-[#2d2621] dark:text-[#f2ece3]">
                Overnight Factory & Persistent Scene Queue
              </h2>
              <span className="paper-badge badge-terracotta">Flow Studio Engine</span>
            </div>
            <p className="text-xs text-[#7f7466] dark:text-[#a09587]">
              Sistem antrean episode massal mandiri. Ekspor 5–10 naskah sekaligus semalaman tanpa khawatir crash atau banned.
            </p>
          </div>

          {/* Engine Guards Badges */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="paper-badge badge-sage text-[11px] flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5" /> Concurrency = 1 (Serial)
            </span>
            <span className="paper-badge badge-sage text-[11px] flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" /> Jeda Natural 2–5s (Anti-Ban)
            </span>
            <span className="paper-badge badge-terracotta text-[11px] flex items-center gap-1">
              <Sparkles className="w-3.5 h-3.5" /> Auto-Fix Refusal Shield
            </span>
          </div>
        </div>

        {/* Live Counters */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mt-4 pt-4 border-t border-[#ede7dc] dark:border-[#38322b]">
          <div className="p-2.5 rounded-lg bg-[#fbf9f5] dark:bg-[#1a1714] border border-[#ede7dc] dark:border-[#332e27]">
            <p className="text-[10px] text-[#7f7466] uppercase font-semibold">Total Episode</p>
            <p className="text-lg font-bold text-[#2d2621] dark:text-[#f2ece3]">{stats.total}</p>
          </div>
          <div className="p-2.5 rounded-lg bg-[#fbf9f5] dark:bg-[#1a1714] border border-[#ede7dc] dark:border-[#332e27]">
            <p className="text-[10px] text-[#7f7466] uppercase font-semibold">Menunggu</p>
            <p className="text-lg font-bold text-[#c25e40]">{stats.queued}</p>
          </div>
          <div className="p-2.5 rounded-lg bg-[#fbf9f5] dark:bg-[#1a1714] border border-[#ede7dc] dark:border-[#332e27]">
            <p className="text-[10px] text-[#7f7466] uppercase font-semibold">Diproses</p>
            <p className="text-lg font-bold text-amber-600 animate-pulse">{stats.processing}</p>
          </div>
          <div className="p-2.5 rounded-lg bg-[#fbf9f5] dark:bg-[#1a1714] border border-[#ede7dc] dark:border-[#332e27]">
            <p className="text-[10px] text-[#7f7466] uppercase font-semibold">Selesai</p>
            <p className="text-lg font-bold text-[#587955]">{stats.completed}</p>
          </div>
          <div className="p-2.5 rounded-lg bg-[#fbf9f5] dark:bg-[#1a1714] border border-[#ede7dc] dark:border-[#332e27]">
            <p className="text-[10px] text-[#7f7466] uppercase font-semibold">Gagal/Retry</p>
            <p className="text-lg font-bold text-red-500">{stats.failed}</p>
          </div>
        </div>
      </div>

      {/* Input Section: Bulk Text or Quick Single */}
      <div className="paper-card p-6 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-[#ede7dc] dark:border-[#38322b]">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setInputMode("bulk")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                inputMode === "bulk"
                  ? "bg-[#c25e40] text-white shadow-sm"
                  : "bg-[#f2ece1] text-[#7f7466] dark:bg-[#2a2621] dark:text-[#dcd4c7]"
              }`}
            >
              📝 Masukkan Naskah Massal
            </button>
            <button
              type="button"
              onClick={() => setInputMode("single")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                inputMode === "single"
                  ? "bg-[#c25e40] text-white shadow-sm"
                  : "bg-[#f2ece1] text-[#7f7466] dark:bg-[#2a2621] dark:text-[#dcd4c7]"
              }`}
            >
              ➕ Tambah Satu Episode
            </button>
          </div>

          {/* Preset Formula & Style */}
          <div className="flex items-center gap-2">
            <select
              value={selectedSkill}
              onChange={(e) => setSelectedSkill(e.target.value)}
              className="text-xs p-1.5 rounded-md border border-[#ede7dc] dark:border-[#38322b] bg-[#fbf9f5] dark:bg-[#1a1714] text-[#2d2621] dark:text-[#f2ece3]"
            >
              <option value="revenge_ceo">👑 Balas Dendam CEO</option>
              <option value="ugc_affiliate">🛍️ UGC Affiliate Video</option>
              <option value="urban_horror">👻 Horor Urban Legend</option>
              <option value="office_romcom">☕ Komedi Romantis Kantor</option>
            </select>

            <select
              value={selectedStyle}
              onChange={(e) => setSelectedStyle(e.target.value)}
              className="text-xs p-1.5 rounded-md border border-[#ede7dc] dark:border-[#38322b] bg-[#fbf9f5] dark:bg-[#1a1714] text-[#2d2621] dark:text-[#f2ece3]"
            >
              <option value="Cinematic">Cinematic</option>
              <option value="Anime">Anime</option>
              <option value="Realistic">Realistic</option>
              <option value="Fantasy">Fantasy</option>
            </select>
          </div>
        </div>

        {inputMode === "bulk" ? (
          <form onSubmit={handleAddBulk} className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-[#7f7466] dark:text-[#a09587] mb-1">
                Ketik / Tempel Banyak Episode (Pisahkan tiap episode dengan baris baru ganda atau tanda &quot;---&quot;):
              </label>
              <textarea
                value={bulkText}
                onChange={(e) => setBulkText(e.target.value)}
                placeholder={`Episode 1: Menantu dibuang oleh keluarga konglomerat, ternyata dia pemegang saham terbesar.
---
Episode 2: Pertemuan para miliarder, sekretaris utama datang menjemput menantu di emperan toko.
---
Episode 3: Kebohongan keluarga mantan terbongkar di depan konferensi pers nasional.`}
                rows={6}
                className="w-full text-xs p-3 rounded-lg border border-[#ede7dc] dark:border-[#38322b] bg-[#fbf9f5] dark:bg-[#1a1714] text-[#2d2621] dark:text-[#f2ece3] focus:outline-none focus:border-[#c25e40] font-mono leading-relaxed"
              />
            </div>
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 cursor-pointer text-xs text-[#2d2621] dark:text-[#f2ece3]">
                <input
                  type="checkbox"
                  checked={useStoryboardSheets}
                  onChange={(e) => setUseStoryboardSheets(e.target.checked)}
                  className="rounded border-[#c25e40] text-[#c25e40]"
                />
                <span>Optimasi 4-in-1 Storyboard Sheets (Hemat ~70% kredit & anti-drift)</span>
              </label>
              <button
                type="submit"
                disabled={loading || !bulkText.trim()}
                className="btn-paper bg-[#c25e40] text-white text-xs px-4 py-2 hover:bg-[#a84d33] disabled:opacity-50 flex items-center gap-1.5"
              >
                <Plus className="w-4 h-4" /> Masukkan ke Antrean Overnight
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleAddSingle} className="space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-semibold text-[#7f7466] dark:text-[#a09587] mb-1">
                  Judul Episode (Opsional):
                </label>
                <input
                  type="text"
                  value={singleTitle}
                  onChange={(e) => setSingleTitle(e.target.value)}
                  placeholder="Episode 1: Penyamaran Berakhir"
                  className="w-full text-xs p-2.5 rounded-lg border border-[#ede7dc] dark:border-[#38322b] bg-[#fbf9f5] dark:bg-[#1a1714] text-[#2d2621] dark:text-[#f2ece3]"
                />
              </div>
              <div className="sm:col-span-2">
                <label className="block text-xs font-semibold text-[#7f7466] dark:text-[#a09587] mb-1">
                  Ide / Naskah Cerita Episode:
                </label>
                <input
                  type="text"
                  value={singleIdea}
                  onChange={(e) => setSingleIdea(e.target.value)}
                  placeholder="Seorang kurir dihina saat mengantar paket, lalu mobil iring-iringan Presiden Direktur berhenti..."
                  className="w-full text-xs p-2.5 rounded-lg border border-[#ede7dc] dark:border-[#38322b] bg-[#fbf9f5] dark:bg-[#1a1714] text-[#2d2621] dark:text-[#f2ece3]"
                />
              </div>
            </div>
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={loading || !singleIdea.trim()}
                className="btn-paper bg-[#c25e40] text-white text-xs px-4 py-2 hover:bg-[#a84d33] disabled:opacity-50 flex items-center gap-1.5"
              >
                <Plus className="w-4 h-4" /> Tambahkan Episode
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Queue Controller & Batch List */}
      <div className="paper-card p-6 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-[#ede7dc] dark:border-[#38322b]">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold text-[#2d2621] dark:text-[#f2ece3]">
              Daftar Antrean Produksi Massal
            </h3>
            {is_running && !is_paused && (
              <span className="paper-badge badge-sage text-[10px] animate-pulse">
                ● Worker Aktif Memproses
              </span>
            )}
            {is_paused && (
              <span className="paper-badge badge-terracotta text-[10px]">
                ⏸ Worker Dijeda
              </span>
            )}
            {!is_running && items.length > 0 && (
              <span className="paper-badge text-[10px] bg-[#f2ece1] dark:bg-[#2a2621]">
                Siap Dijalankan
              </span>
            )}
          </div>

          {/* Action Toolbar */}
          <div className="flex items-center gap-2">
            {(!is_running || is_paused) ? (
              <button
                type="button"
                onClick={handleStart}
                disabled={items.length === 0}
                className="btn-paper bg-[#587955] text-white text-xs px-3 py-1.5 hover:bg-[#486345] disabled:opacity-50 flex items-center gap-1.5 font-semibold"
              >
                <Play className="w-3.5 h-3.5" /> Mulai Antrean Semalaman
              </button>
            ) : (
              <button
                type="button"
                onClick={handlePause}
                className="btn-paper bg-amber-600 text-white text-xs px-3 py-1.5 hover:bg-amber-700 flex items-center gap-1.5 font-semibold"
              >
                <Pause className="w-3.5 h-3.5" /> Jeda Worker (Pause)
              </button>
            )}

            {stats.completed > 0 && (
              <button
                type="button"
                onClick={handleClear}
                className="btn-paper bg-[#f2ece1] dark:bg-[#2a2621] text-[#7f7466] dark:text-[#dcd4c7] text-xs px-3 py-1.5 hover:bg-[#ede7dc] flex items-center gap-1"
                title="Hapus episode yang sudah selesai"
              >
                <Trash2 className="w-3.5 h-3.5" /> Bersihkan Selesai
              </button>
            )}
          </div>
        </div>

        {/* Empty State */}
        {items.length === 0 ? (
          <div className="py-12 text-center space-y-2">
            <Moon className="w-10 h-10 text-[#dcd4c7] mx-auto stroke-1" />
            <p className="text-sm font-medium text-[#7f7466] dark:text-[#a09587]">
              Antrean Overnight masih kosong
            </p>
            <p className="text-xs text-[#a09587]">
              Masukkan naskah beberapa episode di atas, lalu klik Mulai Antrean Semalaman.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {items.map((item, index) => {
              const isProcessing = item.status === "processing";
              const isCompleted = item.status === "completed";
              const isFailed = item.status === "failed";
              const isQueued = item.status === "queued";

              return (
                <div
                  key={item.id}
                  className={`p-4 rounded-xl border transition-all ${
                    isProcessing
                      ? "border-[#c25e40] bg-[#fffcf9] dark:bg-[#241f1a] shadow-sm"
                      : isCompleted
                      ? "border-[#587955]/40 bg-[#fbfcfa] dark:bg-[#1a1f1a]"
                      : isFailed
                      ? "border-red-400/40 bg-red-50/20 dark:bg-red-950/20"
                      : "border-[#ede7dc] dark:border-[#38322b] bg-[#fbf9f5] dark:bg-[#1e1a17]"
                  }`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-[#7f7466]">
                        #{String(index + 1).padStart(2, "0")}
                      </span>
                      <h4 className="text-xs font-bold text-[#2d2621] dark:text-[#f2ece3]">
                        {item.title}
                      </h4>
                      {/* Skill badge */}
                      {item.skill_id && (
                        <span className="text-[10px] px-2 py-0.5 rounded bg-[#f2ece1] dark:bg-[#2e2924] text-[#7f7466] dark:text-[#c4baa9]">
                          {item.skill_id}
                        </span>
                      )}
                    </div>

                    {/* Status Badge */}
                    <div className="flex items-center gap-2">
                      {isProcessing && (
                        <span className="paper-badge badge-terracotta text-[10px] flex items-center gap-1 animate-pulse">
                          <Clock className="w-3 h-3 animate-spin" /> Sedang Diproduksi ({item.progress}%)
                        </span>
                      )}
                      {isCompleted && (
                        <span className="paper-badge badge-sage text-[10px] flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3 text-[#587955]" /> Selesai 100%
                        </span>
                      )}
                      {isQueued && (
                        <span className="paper-badge text-[10px] bg-[#f2ece1] dark:bg-[#2a2621] text-[#7f7466]">
                          Antrean
                        </span>
                      )}
                      {isFailed && (
                        <span className="paper-badge text-[10px] bg-red-100 text-red-700 dark:bg-red-950/50 dark:text-red-300">
                          Gagal
                        </span>
                      )}

                      {/* Item Actions */}
                      {isCompleted && item.video_url && (
                        <a
                          href={item.video_url}
                          target="_blank"
                          rel="noreferrer"
                          download
                          className="btn-paper bg-[#587955] text-white text-[11px] px-2.5 py-1 hover:bg-[#486345] flex items-center gap-1 font-semibold"
                        >
                          <Download className="w-3 h-3" /> Unduh MP4
                        </a>
                      )}
                      {isFailed && (
                        <button
                          type="button"
                          onClick={() => handleRetry(item.id)}
                          className="btn-paper bg-amber-600 text-white text-[11px] px-2.5 py-1 hover:bg-amber-700 flex items-center gap-1 font-semibold"
                        >
                          <RotateCcw className="w-3 h-3" /> Coba Ulang
                        </button>
                      )}
                      {!isProcessing && (
                        <button
                          type="button"
                          onClick={() => handleDelete(item.id)}
                          className="text-[#a09587] hover:text-red-500 p-1"
                          title="Hapus dari antrean"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Summary / Idea text */}
                  <p className="text-xs text-[#7f7466] dark:text-[#a09587] line-clamp-2 mb-2 font-mono">
                    {item.idea}
                  </p>

                  {/* Progress bar & message when active */}
                  {isProcessing && (
                    <div className="space-y-1.5 mt-2 pt-2 border-t border-[#ede7dc]/60 dark:border-[#38322b]/60">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="text-[#c25e40] font-medium">{item.message}</span>
                        <span className="font-mono font-bold text-[#2d2621] dark:text-[#f2ece3]">
                          {item.progress}%
                        </span>
                      </div>
                      <div className="w-full h-1.5 bg-[#f2ece1] dark:bg-[#332e27] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-[#c25e40] transition-all duration-300 rounded-full"
                          style={{ width: `${item.progress}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
