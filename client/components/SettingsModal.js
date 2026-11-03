"use client";

import { useState, useEffect } from "react";

const PRESET_MODELS = [
  { value: "gh/gpt-4o", label: "gh/gpt-4o (9Router - Recommended)" },
  { value: "gh/gpt-4o-mini", label: "gh/gpt-4o-mini (Fast & Light)" },
  { value: "gemini", label: "gemini (Google DeepMind)" },
  { value: "cc/claude-sonnet-5", label: "cc/claude-sonnet-5 (Claude via 9Router)" },
];

export default function SettingsModal({ isOpen, onClose, onSettingsUpdated }) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [openingFlow, setOpeningFlow] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [flowMessage, setFlowMessage] = useState(null);

  const [settings, setSettings] = useState({
    llm_base_url: "http://localhost:20128/v1",
    llm_model: "gh/gpt-4o",
    api_key: "",
    video_engine: "google_omni_flash",
    snapgen_api_key: "",
    has_snapgen_key: false,
    zernio_api_key: "",
    has_zernio_key: false,
    flow_profile: "",
    flow_profile_exists: true,
  });

  useEffect(() => {
    if (!isOpen) return;
    setLoading(true);
    fetch("/api/settings")
      .then((res) => res.json())
      .then((data) => {
        setSettings((prev) => ({
          ...prev,
          llm_base_url: data.llm_base_url || "http://localhost:20128/v1",
          llm_model: data.llm_model || "gh/gpt-4o",
          video_engine: data.video_engine || "google_omni_flash",
          has_snapgen_key: data.has_snapgen_key || false,
          has_zernio_key: data.has_zernio_key || false,
          flow_profile: data.flow_profile || "",
          flow_profile_exists: data.flow_profile_exists ?? true,
        }));
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load settings:", err);
        setLoading(false);
      });
  }, [isOpen]);

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setSaveSuccess(false);
    try {
      const res = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          llm_base_url: settings.llm_base_url,
          llm_model: settings.llm_model,
          api_key: settings.api_key,
          video_engine: settings.video_engine,
          snapgen_api_key: settings.snapgen_api_key,
          zernio_api_key: settings.zernio_api_key,
        }),
      });
      if (res.ok) {
        setSaveSuccess(true);
        if (onSettingsUpdated) onSettingsUpdated();
        setTimeout(() => setSaveSuccess(false), 3000);
      }
    } catch (err) {
      console.error("Save error:", err);
    } finally {
      setSaving(false);
    }
  };

  const handleOpenFlowBrowser = async () => {
    setOpeningFlow(true);
    setFlowMessage(null);
    try {
      const res = await fetch("/api/flow/open-browser", { method: "POST" });
      const data = await res.json();
      setFlowMessage(data.message || "Browser Google Flow telah dibuka di PC!");
    } catch (err) {
      setFlowMessage("Gagal membuka browser Chrome.");
    } finally {
      setOpeningFlow(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#2d2621]/40 backdrop-blur-xs">
      <div className="w-full max-w-xl paper-sheet p-6 sm:p-8 flex flex-col max-h-[92vh] overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-[#e6dfd1]">
          <div>
            <h3 className="text-base font-bold text-[#2d2621]">Pengaturan Engine &amp; Akun AI</h3>
            <p className="text-xs text-[#7f7466]">Konfigurasi 9Router naskah, SnapGen, dan profil Google Flow</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center text-[#7f7466] hover:bg-[#f4efe6] transition-colors cursor-pointer text-sm"
          >
            ✕
          </button>
        </div>

        {/* Dialog Body */}
        <div className="py-4 overflow-y-auto space-y-5 text-xs text-[#473f37]">
          {/* Section 1: Google Flow Account */}
          <div className="paper-card p-4 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-sm text-[#2d2621]">Google Flow Profile (Omni Flash 1.1)</span>
              <span className="paper-badge badge-sage">Profil Tersedia</span>
            </div>
            <p className="text-xs text-[#7f7466]">
              Engine Playwright menggunakan direktori profil browser PC di:
            </p>
            <div className="p-2.5 bg-[#ffffff] border border-[#e6dfd1] rounded-lg font-mono text-[11px] text-[#473f37] break-all select-all">
              {settings.flow_profile || "C:\\Users\\HP\\.google-flow-creator\\browser-profile"}
            </div>
            <div className="pt-1 flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={handleOpenFlowBrowser}
                disabled={openingFlow}
                className="btn-paper py-2 px-3.5 text-xs font-semibold text-[#c25e40] flex items-center gap-1.5 cursor-pointer"
              >
                {openingFlow ? "Membuka Chrome..." : "🌐 Buka Browser Google Flow"}
              </button>
              <span className="text-[11px] text-[#aba092] italic">
                (Login Google satu kali jika sesi kedaluwarsa)
              </span>
            </div>
            {flowMessage && (
              <div className="p-2 rounded-lg bg-[#ebf3ea] border border-[#d2e4d0] text-[#3b5f38] text-[11px]">
                {flowMessage}
              </div>
            )}
          </div>

          {/* Section 2: SnapGen.ai Provider */}
          <div className="paper-card p-4 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-sm text-[#2d2621]">SnapGen.ai Provider (AdFlx Standard)</span>
              <span className="paper-badge badge-honey">
                {settings.has_snapgen_key || settings.snapgen_api_key ? "Key Tersedia" : "Belum Terisi"}
              </span>
            </div>
            <p className="text-xs text-[#7f7466]">
              Dipakai untuk konsistensi potret karakter, scene frame, dan video cloud Veo 3.1:
            </p>
            <div>
              <input
                type="password"
                value={settings.snapgen_api_key}
                onChange={(e) => setSettings({ ...settings, snapgen_api_key: e.target.value })}
                placeholder={settings.has_snapgen_key ? "•••••••••••• (Tersimpan di .env)" : "Masukkan SnapGen API Key (x-api-key)"}
                className="paper-input w-full p-2.5 text-xs font-mono"
              />
            </div>
          </div>

          {/* Section 3: Zernio Multi-Platform Publisher */}
          <div className="paper-card p-4 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-sm text-[#2d2621]">Zernio Social Publisher (Multi-Platform)</span>
              <span className={`paper-badge ${settings.has_zernio_key || settings.zernio_api_key ? "badge-sage" : "badge-honey"}`}>
                {settings.has_zernio_key || settings.zernio_api_key ? "API Key Aktif" : "Belum Terisi"}
              </span>
            </div>
            <p className="text-xs text-[#7f7466]">
              Hubungkan akun TikTok, Instagram Reels, YouTube Shorts, dan Facebook di dashboard Zernio. Cukup masukkan API Key Zernio di bawah untuk auto-publish:
            </p>
            <div>
              <input
                type="password"
                value={settings.zernio_api_key}
                onChange={(e) => setSettings({ ...settings, zernio_api_key: e.target.value })}
                placeholder={settings.has_zernio_key ? "•••••••••••• (Tersimpan di .env)" : "Masukkan Zernio API Key (sk_...)"}
                className="paper-input w-full p-2.5 text-xs font-mono"
              />
            </div>
          </div>

          {/* Section 4: 9Router Local Scriptwriter */}
          <form onSubmit={handleSave} className="space-y-4">
            <div className="paper-card p-4 space-y-3">
              <span className="font-semibold text-sm text-[#2d2621] block">9Router Scriptwriter (Zero Cost LLM)</span>

              <div className="space-y-1">
                <label className="block text-xs font-medium text-[#7f7466]">9Router Base URL / Endpoint:</label>
                <input
                  type="text"
                  value={settings.llm_base_url}
                  onChange={(e) => setSettings({ ...settings, llm_base_url: e.target.value })}
                  className="paper-input w-full p-2 text-xs font-mono"
                  required
                />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-medium text-[#7f7466]">Model Naskah Drama:</label>
                <select
                  value={settings.llm_model}
                  onChange={(e) => setSettings({ ...settings, llm_model: e.target.value })}
                  className="paper-input w-full p-2 text-xs cursor-pointer"
                >
                  {PRESET_MODELS.map((m) => (
                    <option key={m.value} value={m.value}>
                      {m.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1.5 pt-1">
                <label className="block text-xs font-medium text-[#7f7466]">Pilihan Mesin Video:</label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  <label
                    className={`p-3 rounded-xl border flex items-center gap-2 cursor-pointer transition-all ${
                      settings.video_engine === "google_omni_flash"
                        ? "bg-[#fffdf9] border-[#c25e40] ring-1 ring-[#c25e40]/20"
                        : "bg-[#ffffff] border-[#e6dfd1]"
                    }`}
                  >
                    <input
                      type="radio"
                      name="video_engine"
                      checked={settings.video_engine === "google_omni_flash"}
                      onChange={() => setSettings({ ...settings, video_engine: "google_omni_flash" })}
                      className="accent-[#c25e40] cursor-pointer"
                    />
                    <div>
                      <div className="text-xs font-bold text-[#2d2621]">Google Omni Flash 1.1</div>
                      <div className="text-[10px] text-[#7f7466]">Lokal Playwright &bull; 9:16 &bull; $0 Cost</div>
                    </div>
                  </label>

                  <label
                    className={`p-3 rounded-xl border flex items-center gap-2 cursor-pointer transition-all ${
                      settings.video_engine === "snapgen"
                        ? "bg-[#fffdf9] border-[#c25e40] ring-1 ring-[#c25e40]/20"
                        : "bg-[#ffffff] border-[#e6dfd1]"
                    }`}
                  >
                    <input
                      type="radio"
                      name="video_engine"
                      checked={settings.video_engine === "snapgen"}
                      onChange={() => setSettings({ ...settings, video_engine: "snapgen" })}
                      className="accent-[#c25e40] cursor-pointer"
                    />
                    <div>
                      <div className="text-xs font-bold text-[#2d2621]">SnapGen.ai (AdFlx)</div>
                      <div className="text-[10px] text-[#7f7466]">Veo 3.1 Fast / Cloud I2V &bull; 9:16</div>
                    </div>
                  </label>
                </div>
              </div>
            </div>

            {/* Modal Actions */}
            <div className="pt-3 border-t border-[#e6dfd1] flex items-center justify-between">
              {saveSuccess ? (
                <span className="text-xs font-semibold text-[#3b5f38]">✔ Pengaturan berhasil disimpan!</span>
              ) : (
                <span className="text-[11px] text-[#aba092]">D:\microdrama-app\server\.env</span>
              )}

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="btn-paper py-2 px-4 text-xs font-medium cursor-pointer"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="btn-terracotta py-2 px-5 text-xs font-semibold cursor-pointer"
                >
                  {saving ? "Menyimpan..." : "Simpan Pengaturan"}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
