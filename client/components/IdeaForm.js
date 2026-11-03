"use client";

import { useState, useEffect } from "react";
import { Sparkles, Loader2, Film, Clapperboard, Flame, Smartphone, Palette, Sliders } from "lucide-react";

const STYLES = [
  { value: "Cinematic", label: "Cinematic", desc: "Film Layar Lebar 4K" },
  { value: "Realistic", label: "Hyper-Real", desc: "Suasana Nyata Tajam" },
  { value: "Korean Drama", label: "K-Drama", desc: "Tone Romantis Emosional" },
  { value: "Dark Thriller", label: "Dark Thriller", desc: "Tegang, Shadow Kuat" },
  { value: "Cyberpunk", label: "Cyberpunk", desc: "Neon Glow & Masa Depan" },
];

const QUICK_IDEAS = [
  "Pewaris konglomerat menyamar jadi kurir ojol untuk membongkar korupsi dewan direksi.",
  "Seorang ilmuwan jenius menemukan rekaman CCTV masa depan yang memprediksi penculikan istrinya.",
  "Bos mafia yang pensiun kembali turun ke jalan demi melindungi anak panti asuhan tempat dia dibesarkan.",
];

const MODES = [
  {
    value: "idea2video",
    label: "Idea to Video (Otomatis)",
    desc: "AI merancang alur cerita, shot storyboard, aktor, dan render video",
  },
  {
    value: "script2video",
    label: "Script to Video (Manual)",
    desc: "Gunakan naskah adegan buatan sendiri",
  },
];

export default function IdeaForm({ onSubmit, isSubmitting }) {
  const [idea, setIdea] = useState("");
  const [userRequirement, setUserRequirement] = useState("");
  const [style, setStyle] = useState("Cinematic");
  const [mode, setMode] = useState("idea2video");
  const [script, setScript] = useState("");
  const [skills, setSkills] = useState([]);
  const [selectedSkill, setSelectedSkill] = useState("revenge_ceo");
  const [useStoryboardSheets, setUseStoryboardSheets] = useState(true);

  useEffect(() => {
    fetch("/api/skills")
      .then((res) => res.json())
      .then((data) => {
        if (data.skills && data.skills.length > 0) {
          setSkills(data.skills);
        }
      })
      .catch((err) => console.error("Failed to load skills:", err));
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!idea.trim() && (mode !== "script2video" || !script.trim())) return;
    onSubmit({
      idea: idea.trim(),
      user_requirement: userRequirement.trim(),
      style,
      mode,
      script: script.trim(),
      skill_id: selectedSkill,
      use_storyboard_sheets: useStoryboardSheets,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Soft Sticky Note Header */}
      <div className="sticky-note p-3.5 flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#587955]" />
          <span className="font-semibold text-[#66501c]">Engine Aktif:</span>
          <span className="font-medium text-[#2d2621]">Google Omni Flash 1.1 (Vertikal 9:16 &bull; 10s) + SnapGen.ai</span>
        </div>
        <div className="paper-badge badge-sage">
          Zero API Cost
        </div>
      </div>

      {/* Section 1: Mode Pipeline */}
      <div className="space-y-2">
        <label className="block text-xs font-semibold text-[#7f7466] uppercase tracking-wider">
          1. Metode Pembuatan
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {MODES.map((m) => (
            <div
              key={m.value}
              onClick={() => setMode(m.value)}
              className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                mode === m.value
                  ? "bg-[#fffdf9] dark:bg-[#27231e] border-[#c25e40] shadow-sm ring-1 ring-[#c25e40]/30"
                  : "bg-[#fbf7f0] dark:bg-[#1a1714] border-[#e6dfd1] dark:border-[#38322b] hover:bg-[#f6f0e4] dark:hover:bg-[#221e1a]"
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <input
                  type="radio"
                  name="pipeline_mode"
                  value={m.value}
                  checked={mode === m.value}
                  onChange={() => setMode(m.value)}
                  className="accent-[#c25e40] cursor-pointer"
                />
                <span className="text-sm font-semibold text-[#2d2621]">{m.label}</span>
              </div>
              <p className="text-xs text-[#7f7466] pl-5">{m.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Section 2: Skill & Formula Cerita */}
      {skills.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-[#7f7466] uppercase tracking-wider">
              2. Skill / Formula Cerita Microdrama
            </label>
            <span className="paper-badge badge-sage text-[10px]">9Router Screenplay Skill</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {skills.map((sk) => (
              <div
                key={sk.id}
                onClick={() => setSelectedSkill(selectedSkill === sk.id ? "" : sk.id)}
                className={`p-3 rounded-xl border cursor-pointer transition-all ${
                  selectedSkill === sk.id
                    ? "bg-[#fffdf9] dark:bg-[#27231e] border-[#c25e40] shadow-sm ring-1 ring-[#c25e40]/30"
                    : "bg-[#fbf7f0] dark:bg-[#1a1714] border-[#e6dfd1] dark:border-[#38322b] hover:bg-[#f6f0e4] dark:hover:bg-[#221e1a]"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-bold text-[#2d2621] dark:text-[#f2ece3] flex items-center gap-1.5">
                    <span>{sk.icon}</span> {sk.name}
                  </span>
                  <span className="text-[10px] text-[#aba092]">{sk.category}</span>
                </div>
                <p className="text-[11px] text-[#7f7466] dark:text-[#aba092] line-clamp-2">{sk.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Section 3: Story Idea on Lined Paper */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-xs font-semibold text-[#7f7466] uppercase tracking-wider">
            3. Ide Cerita / Premis Drama
          </label>
          <span className="text-xs text-[#aba092] italic">Halaman Naskah</span>
        </div>

        <div className="paper-card p-1">
          <textarea
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            placeholder={
              mode === "idea2video"
                ? "Tulis ide cerita Anda di sini...\n(Contoh: Seorang kurir sederhana tanpa sengaja menyelamatkan putri konglomerat yang diculik...)"
                : "Tulis judul dan ringkasan episode..."
            }
            rows={5}
            required={mode === "idea2video"}
            className="w-full p-4 paper-ruled rounded-lg text-sm text-[#2d2621] placeholder-[#aba092] border-0 focus:ring-0 outline-none resize-y"
          />
        </div>

        {/* Quick Inspiration Chips */}
        {mode === "idea2video" && (
          <div className="pt-1 flex flex-wrap items-center gap-2 text-xs">
            <span className="text-[#7f7466] font-medium">Inspirasi:</span>
            {QUICK_IDEAS.map((qi, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => setIdea(qi)}
                className="btn-paper py-1 px-3 text-xs text-[#473f37] hover:text-[#c25e40]"
              >
                &ldquo;{qi.slice(0, 38)}...&rdquo;
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Script to Video Field */}
      {mode === "script2video" && (
        <div className="space-y-2">
          <label className="block text-xs font-semibold text-[#7f7466] uppercase tracking-wider">
            Naskah Adegan Lengkap (Scene Script)
          </label>
          <div className="paper-card p-1">
            <textarea
              value={script}
              onChange={(e) => setScript(e.target.value)}
              placeholder="Tulis naskah dialog dan aksi per adegan di sini..."
              rows={6}
              required
              className="w-full p-4 paper-ruled rounded-lg text-sm text-[#2d2621] border-0 focus:ring-0 outline-none resize-y"
            />
          </div>
        </div>
      )}

      {/* Section 3: Visual Style & Director Notes */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <label className="block text-xs font-semibold text-[#7f7466] uppercase tracking-wider">
            3. Gaya Sinematik
          </label>
          <select
            value={style}
            onChange={(e) => setStyle(e.target.value)}
            className="paper-input w-full p-2.5 text-sm cursor-pointer dark:bg-[#181614] dark:text-[#f2ece3]"
          >
            {STYLES.map((s) => (
              <option key={s.value} value={s.value} className="dark:bg-[#181614] dark:text-[#f2ece3]">
                {s.label} — {s.desc}
              </option>
            ))}
          </select>
          <p className="text-[11px] text-[#aba092]">Menyesuaikan grading warna & pencahayaan</p>
        </div>

        <div className="space-y-1.5">
          <label className="block text-xs font-semibold text-[#7f7466] uppercase tracking-wider">
            4. Catatan Sutradara (Opsional)
          </label>
          <input
            type="text"
            value={userRequirement}
            onChange={(e) => setUserRequirement(e.target.value)}
            placeholder="Pencahayaan dramatis, tempo cepat, dsb."
            className="paper-input w-full p-2.5 text-sm dark:bg-[#181614] dark:text-[#f2ece3]"
          />
          <p className="text-[11px] text-[#aba092]">Instruksi pacing atau angle kamera khusus</p>
        </div>
      </div>

      {/* Section 5: Engine Optimasi (Flow Studio Paradigm: Storyboard Sheets & Auto-Fix) */}
      <div className="p-4 rounded-xl border border-[#e6dfd1] dark:border-[#38322b] bg-[#fffdfa] dark:bg-[#201d19] space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-[#2d2621] dark:text-[#f2ece3]">
              ✦ Engine Optimasi: Storyboard Sheets &amp; Auto-Fix
            </span>
            <span className="paper-badge badge-terracotta text-[10px]">Flow Studio Engine</span>
          </div>
          <span className="text-[11px] font-medium text-[#587955] dark:text-[#88b085]">
            ~70% Hemat Kredit &amp; Waktu
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          {/* Storyboard Sheets Toggle */}
          <label
            onClick={() => setUseStoryboardSheets(!useStoryboardSheets)}
            className={`flex items-start gap-2.5 p-3 rounded-lg border cursor-pointer transition-all select-none ${
              useStoryboardSheets
                ? "bg-[#fbf7f0] dark:bg-[#27231e] border-[#c25e40]"
                : "bg-white dark:bg-[#1a1714] border-[#e6dfd1] dark:border-[#38322b] opacity-70"
            }`}
          >
            <input
              type="checkbox"
              checked={useStoryboardSheets}
              onChange={() => {}}
              className="mt-0.5 rounded text-[#c25e40] focus:ring-[#c25e40]"
            />
            <div>
              <div className="font-semibold text-[#2d2621] dark:text-[#f2ece3] mb-0.5">
                Storyboard Sheets (4 Scenes, 1 Image)
              </div>
              <p className="text-[11px] text-[#7f7466] dark:text-[#a89e90]">
                AI membuat 1 gambar grid 2x2 lalu di-slice otomatis menjadi 4 adegan berurutan. Karakter, wajah, dan kostum 100% konsisten tanpa drift.
              </p>
            </div>
          </label>

          {/* Auto-Fix Censorship & Safety Shield */}
          <div className="flex items-start gap-2.5 p-3 rounded-lg border border-[#e6dfd1] dark:border-[#38322b] bg-white dark:bg-[#1a1714]">
            <div className="w-2.5 h-2.5 rounded-full bg-[#587955] mt-1 shrink-0" />
            <div>
              <div className="font-semibold text-[#2d2621] dark:text-[#f2ece3] mb-0.5 flex items-center gap-1.5">
                Auto-Fix Censorship Shield
                <span className="paper-badge badge-sage text-[9px] py-0 px-1">Aktif</span>
              </div>
              <p className="text-[11px] text-[#7f7466] dark:text-[#a89e90]">
                Jika adegan naskah terhalang sensor AI, 9Router LLM otomatis mereparasi prompt menjadi aman secara semantik tanpa menghentikan pipeline.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Action Footer */}
      <div className="pt-4 border-t border-[#e6dfd1] flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="text-xs text-[#7f7466]">
          Format output: <span className="font-semibold text-[#2d2621]">Vertikal 9:16 (Siap TikTok / Shorts / Reels)</span>
        </div>

        <button
          type="submit"
          disabled={isSubmitting || (!idea.trim() && (mode !== "script2video" || !script.trim()))}
          className="btn-terracotta py-3 px-8 text-sm flex items-center justify-center gap-2 cursor-pointer w-full sm:w-auto"
        >
          {isSubmitting ? (
            <>
              <Loader2 size={16} className="animate-spin" />
              <span>Menyusun &amp; Merender Video...</span>
            </>
          ) : (
            <>
              <Sparkles size={16} />
              <span>Mulai Rancang &amp; Render Video</span>
            </>
          )}
        </button>
      </div>
    </form>
  );
}
