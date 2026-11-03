"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import IdeaForm from "../components/IdeaForm";
import SettingsModal from "../components/SettingsModal";
import { Film, Zap, GitBranch, Layers, Settings, ExternalLink, ShieldCheck, CheckCircle2, Sun, Moon } from "lucide-react";

export default function HomePage() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [isDark, setIsDark] = useState(false);
  const [statusInfo, setStatusInfo] = useState({
    llm_model: "gh/gpt-4o",
    video_engine: "Google Omni Flash 1.1",
    flow_profile_exists: true,
  });

  const loadSettings = () => {
    fetch("/api/settings")
      .then((res) => res.json())
      .then((data) => {
        setStatusInfo({
          llm_model: data.llm_model || "gh/gpt-4o",
          video_engine: data.video_engine === "google_omni_flash" ? "Google Omni Flash 1.1" : data.video_engine,
          flow_profile_exists: data.flow_profile_exists ?? true,
        });
      })
      .catch(() => {});
  };

  useEffect(() => {
    loadSettings();
    const savedTheme = localStorage.getItem("microdrama_theme");
    if (savedTheme === "dark") {
      document.documentElement.classList.add("dark");
      setIsDark(true);
    } else {
      document.documentElement.classList.remove("dark");
      setIsDark(false);
    }
  }, []);

  const toggleTheme = () => {
    if (isDark) {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("microdrama_theme", "light");
      setIsDark(false);
    } else {
      document.documentElement.classList.add("dark");
      localStorage.setItem("microdrama_theme", "dark");
      setIsDark(true);
    }
  };

  const handleSubmit = async (formData) => {
    setIsSubmitting(true);
    setError(null);
    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to start generation");
      }
      const data = await res.json();
      router.push(`/generate/${data.job_id}`);
    } catch (err) {
      setError(err.message);
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen py-8 px-4 sm:px-6 flex flex-col justify-between">
      {/* Top Navigation Bar / Stationery Desk Header */}
      <header className="max-w-4xl mx-auto w-full mb-8 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#c25e40] text-white flex items-center justify-center font-bold text-lg shadow-sm">
            MD
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-[#2d2621]">MicroDrama Studio</h1>
              <span className="paper-badge badge-terracotta">Notebook Edition</span>
            </div>
            <p className="text-xs text-[#7f7466]">Zero Cost AI Micro-Drama Orchestrator</p>
          </div>
        </div>

        {/* Action Buttons & Engine Badges */}
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="hidden sm:flex items-center gap-2">
            <span className="paper-badge badge-sage">
              ● LLM: {statusInfo.llm_model}
            </span>
            <span className="paper-badge badge-honey">
              Omni Flash 1.1 (9:16)
            </span>
          </div>

          <button
            type="button"
            onClick={() => setSettingsOpen(true)}
            className="btn-paper py-2 px-3.5 text-xs flex items-center gap-1.5 cursor-pointer"
          >
            <ExternalLink size={14} className="text-[#c25e40]" />
            <span>Login Google Flow</span>
          </button>

          <button
            type="button"
            onClick={() => setSettingsOpen(true)}
            className="btn-paper p-2 text-xs flex items-center justify-center cursor-pointer"
            title="Pengaturan"
          >
            <Settings size={16} className="text-[#7f7466]" />
          </button>

          {/* Theme Toggle Button (Light Paper / Dark Journal) */}
          <button
            type="button"
            onClick={toggleTheme}
            className="btn-paper py-1.5 px-3 text-xs flex items-center gap-1.5 cursor-pointer"
            title={isDark ? "Ganti ke Tema Kertas Terang" : "Ganti ke Tema Gelap (Jurnal Malam)"}
          >
            {isDark ? (
              <>
                <Sun size={15} className="text-[#e8a548]" />
                <span className="font-medium text-xs">Terang</span>
              </>
            ) : (
              <>
                <Moon size={15} className="text-[#486683]" />
                <span className="font-medium text-xs">Gelap</span>
              </>
            )}
          </button>
        </div>
      </header>

      {/* Main Notebook Sheet */}
      <main className="max-w-4xl mx-auto w-full paper-sheet p-6 sm:p-10 mb-10">
        {/* Notebook Title Area */}
        <div className="mb-8 pb-6 border-b border-[#e6dfd1]">
          <div className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#c25e40] mb-2 uppercase tracking-wider">
            <span>📓</span>
            <span>Buku Catatan Produksi Serial</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-[#2d2621] tracking-tight mb-2">
            Generator Serial Microdrama AI
          </h2>
          <p className="text-sm text-[#7f7466] leading-relaxed max-w-2xl">
            Tulis ide cerita atau naskah Anda. Sistem otomatis merancang skenario adegan, storyboard shot, konsistensi aktor, dan me-render klip video vertikal sinematik (9:16) siap posting.
          </p>

          {/* Workflow Steps Indicator */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mt-6">
            {[
              { icon: <Film size={14} />, label: "1. Screenwriter", desc: "Naskah AI" },
              { icon: <GitBranch size={14} />, label: "2. Storyboard", desc: "Shot & Framing" },
              { icon: <Layers size={14} />, label: "3. Karakter", desc: "Konsistensi Aktor" },
              { icon: <Zap size={14} />, label: "4. Omni Flash", desc: "Render 9:16" },
            ].map((step) => (
              <div key={step.label} className="paper-card p-3">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-[#2d2621] mb-0.5">
                  <span className="text-[#c25e40]">{step.icon}</span>
                  <span>{step.label}</span>
                </div>
                <div className="text-[11px] text-[#7f7466]">{step.desc}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Error notification if any */}
        {error && (
          <div className="mb-6 p-4 rounded-xl text-xs font-medium bg-[#fcf0ec] border border-[#f5d7ce] text-[#9e4328] flex items-center gap-2">
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {/* The Clean Form */}
        <IdeaForm onSubmit={handleSubmit} isSubmitting={isSubmitting} />
      </main>

      {/* Clean Desk Footer */}
      <footer className="max-w-4xl mx-auto w-full text-center py-6 text-xs text-[#aba092] border-t border-[#e6dfd1]/60">
        MicroDrama Studio &bull; Local Native Engine &bull; Zero Cost 9Router &amp; Google Omni Flash 1.1
      </footer>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onSettingsUpdated={loadSettings}
      />
    </div>
  );
}
