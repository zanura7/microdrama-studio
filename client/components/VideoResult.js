"use client";

import { useState, useEffect } from "react";
import { Download, ExternalLink, Send, Sparkles, Loader2, CheckCircle2, AlertCircle } from "lucide-react";

export default function VideoResult({ videoUrl, jobId }) {
  const [isPlaying, setIsPlaying] = useState(false);

  // Zernio State
  const [zernioLoading, setZernioLoading] = useState(true);
  const [zernioConfigured, setZernioConfigured] = useState(false);
  const [accounts, setAccounts] = useState([]);
  const [selectedAccountIds, setSelectedAccountIds] = useState([]);
  const [caption, setCaption] = useState("");
  const [generatingCaption, setGeneratingCaption] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [publishStatus, setPublishStatus] = useState(null);

  useEffect(() => {
    fetch("/api/zernio/accounts")
      .then((res) => res.json())
      .then((data) => {
        setZernioConfigured(data.configured || false);
        const accs = data.accounts || [];
        setAccounts(accs);
        const activeIds = accs.filter((a) => a.is_active).map((a) => a.id);
        setSelectedAccountIds(activeIds);
        setZernioLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load Zernio accounts:", err);
        setZernioLoading(false);
      });
  }, []);

  const handleDownload = () => {
    const a = document.createElement("a");
    a.href = videoUrl;
    a.download = `microdrama-${jobId}.mp4`;
    a.click();
  };

  const handleGenerateCaption = async () => {
    setGeneratingCaption(true);
    setPublishStatus(null);
    try {
      const res = await fetch(`/api/caption/${jobId}`, { method: "POST" });
      const data = await res.json();
      if (data.caption) {
        setCaption(data.caption);
      }
    } catch (err) {
      console.error("Caption generation error:", err);
    } finally {
      setGeneratingCaption(false);
    }
  };

  const toggleAccount = (accId) => {
    setSelectedAccountIds((prev) =>
      prev.includes(accId) ? prev.filter((id) => id !== accId) : [...prev, accId]
    );
  };

  const handlePublish = async () => {
    if (selectedAccountIds.length === 0) {
      setPublishStatus({ type: "error", message: "Pilih minimal satu akun media sosial tujuan." });
      return;
    }
    setPublishing(true);
    setPublishStatus(null);

    const platformTargets = accounts
      .filter((a) => selectedAccountIds.includes(a.id))
      .map((a) => ({ platform: a.platform, accountId: a.id }));

    try {
      const res = await fetch("/api/publish", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_id: jobId,
          caption: caption.trim() || "Klip MicroDrama Terbaru 🔥 #microdrama #viral",
          platforms: platformTargets,
          publish_now: true,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Gagal mempublikasikan video.");
      }

      setPublishStatus({
        type: "success",
        message: data.message || "Video berhasil dipublikasikan ke media sosial via Zernio!",
      });
    } catch (err) {
      setPublishStatus({ type: "error", message: err.message });
    } finally {
      setPublishing(false);
    }
  };

  const getPlatformIcon = (platform) => {
    switch (platform) {
      case "tiktok":
        return "🎵";
      case "instagram":
        return "📸";
      case "youtube":
        return "▶️";
      case "facebook":
        return "👥";
      default:
        return "🌐";
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-[#e6dfd1] dark:border-[#38322b]">
        <div className="flex items-center gap-2">
          <span className="w-7 h-7 rounded-lg bg-[#ebf3ea] dark:bg-[#1f2b1d] text-[#3b5f38] dark:text-[#7bb375] flex items-center justify-center font-bold text-xs">
            ✔
          </span>
          <div>
            <h4 className="text-sm font-bold text-[#2d2621] dark:text-[#f2ece3]">Klip Microdrama Selesai Diproduksi</h4>
            <p className="text-[11px] text-[#7f7466] dark:text-[#aba092]">microdrama-{jobId}.mp4 &bull; Format 9:16 Sinematik</p>
          </div>
        </div>
        <span className="paper-badge badge-sage">Siap Tayang / Download</span>
      </div>

      {/* Video display */}
      <div className="flex flex-col items-center justify-center py-2">
        <div className="bg-[#1f1b18] rounded-2xl p-2 max-w-[320px] w-full shadow-lg border border-[#e6dfd1] dark:border-[#38322b] aspect-[9/16] overflow-hidden flex items-center justify-center">
          <video
            src={videoUrl}
            controls
            autoPlay
            loop
            className="w-full h-full object-contain rounded-xl"
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
          />
        </div>

        {/* Action Buttons */}
        <div className="w-full max-w-[320px] mt-4 flex items-center gap-2.5">
          <button
            onClick={handleDownload}
            className="btn-terracotta py-2.5 px-4 text-xs font-semibold flex-1 flex items-center justify-center gap-1.5 cursor-pointer"
          >
            <Download size={14} />
            <span>Unduh MP4</span>
          </button>
          <a
            href={videoUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-paper py-2.5 px-3.5 text-xs font-semibold text-[#2d2621] dark:text-[#f2ece3] flex items-center justify-center gap-1.5 cursor-pointer no-underline"
          >
            <ExternalLink size={14} />
            <span>Buka Tab</span>
          </a>
        </div>
      </div>

      {/* Zernio Multi-Platform Auto-Publisher Panel */}
      <div className="paper-card p-4 sm:p-5 space-y-4 border border-[#e6dfd1] dark:border-[#38322b] rounded-2xl">
        <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-[#e6dfd1] dark:border-[#38322b]">
          <div className="flex items-center gap-2">
            <span className="text-base">🚀</span>
            <div>
              <h5 className="text-xs font-bold text-[#2d2621] dark:text-[#f2ece3] uppercase tracking-wider">
                Auto-Publish Multi-Platform (Zernio API)
              </h5>
              <p className="text-[11px] text-[#7f7466] dark:text-[#aba092]">
                Publikasikan klip 9:16 serentak ke TikTok, Instagram Reels, dan YouTube Shorts
              </p>
            </div>
          </div>
          <span className={`paper-badge ${zernioConfigured ? "badge-sage" : "badge-honey"}`}>
            {zernioConfigured ? "Zernio Terhubung" : "API Key Belum Disetel"}
          </span>
        </div>

        {!zernioConfigured ? (
          <div className="p-3 bg-[#fbf7f0] dark:bg-[#1a1714] border border-[#e6dfd1] dark:border-[#38322b] rounded-xl text-xs text-[#7f7466] dark:text-[#aba092]">
            <p className="mb-1 font-semibold text-[#2d2621] dark:text-[#f2ece3]">
              💡 Sambungkan Zernio API Key untuk Auto-Publish:
            </p>
            <p>
              Hubungkan akun sosial media Anda langsung di dashboard Zernio. Setelah itu masukkan <strong>Zernio API Key</strong> di menu Pengaturan (pojok kanan atas).
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Account selector pills */}
            <div className="space-y-1.5">
              <label className="block text-[11px] font-semibold text-[#7f7466] dark:text-[#aba092] uppercase">
                1. Pilih Akun Media Sosial Tujuan:
              </label>
              {accounts.length === 0 ? (
                <p className="text-xs text-[#aba092] italic">
                  Belum ada akun media sosial yang terhubung di Zernio. Hubungkan akun di dashboard Zernio Anda.
                </p>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {accounts.map((acc) => {
                    const isSelected = selectedAccountIds.includes(acc.id);
                    return (
                      <div
                        key={acc.id}
                        onClick={() => toggleAccount(acc.id)}
                        className={`p-2.5 rounded-xl border flex items-center justify-between cursor-pointer transition-all ${
                          isSelected
                            ? "bg-[#fffdf9] dark:bg-[#27231e] border-[#c25e40] ring-1 ring-[#c25e40]/20"
                            : "bg-[#ffffff] dark:bg-[#1a1714] border-[#e6dfd1] dark:border-[#38322b] opacity-60 hover:opacity-100"
                        }`}
                      >
                        <div className="flex items-center gap-2 overflow-hidden">
                          <span className="text-base">{getPlatformIcon(acc.platform)}</span>
                          <div className="truncate">
                            <div className="text-xs font-semibold text-[#2d2621] dark:text-[#f2ece3] truncate">
                              {acc.display_name || acc.username}
                            </div>
                            <div className="text-[10px] text-[#7f7466] dark:text-[#aba092] capitalize">
                              {acc.platform}
                            </div>
                          </div>
                        </div>
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => {}}
                          className="accent-[#c25e40] cursor-pointer ml-2"
                        />
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Caption & Hashtag generator */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-[11px] font-semibold text-[#7f7466] dark:text-[#aba092] uppercase">
                  2. Caption &amp; Tagar Viral:
                </label>
                <button
                  type="button"
                  onClick={handleGenerateCaption}
                  disabled={generatingCaption}
                  className="btn-paper py-1 px-2.5 text-[11px] font-medium text-[#c25e40] flex items-center gap-1 cursor-pointer"
                >
                  {generatingCaption ? (
                    <>
                      <Loader2 size={12} className="animate-spin" />
                      <span>Menyusun Caption AI...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles size={12} />
                      <span>Buat Caption Viral Otomatis</span>
                    </>
                  )}
                </button>
              </div>

              <textarea
                value={caption}
                onChange={(e) => setCaption(e.target.value)}
                placeholder="Tulis caption atau klik 'Buat Caption Viral Otomatis'..."
                rows={3}
                className="paper-input w-full p-2.5 text-xs font-sans dark:bg-[#181614] dark:text-[#f2ece3]"
              />
            </div>

            {/* Publish action button & feedback */}
            <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-3">
              <div className="text-[11px] text-[#7f7466] dark:text-[#aba092]">
                Target: <strong>{selectedAccountIds.length} platform terpilih</strong>
              </div>

              <button
                type="button"
                onClick={handlePublish}
                disabled={publishing || selectedAccountIds.length === 0}
                className="btn-terracotta py-2.5 px-6 text-xs font-semibold flex items-center justify-center gap-2 cursor-pointer w-full sm:w-auto"
              >
                {publishing ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    <span>Mengunggah &amp; Mempublikasikan...</span>
                  </>
                ) : (
                  <>
                    <Send size={14} />
                    <span>Publikasikan Sekarang</span>
                  </>
                )}
              </button>
            </div>

            {publishStatus && (
              <div
                className={`p-3 rounded-xl flex items-center gap-2 text-xs ${
                  publishStatus.type === "success"
                    ? "bg-[#ebf3ea] dark:bg-[#1f2b1d] border border-[#d2e4d0] text-[#3b5f38] dark:text-[#7bb375]"
                    : "bg-[#fdf0ed] dark:bg-[#2b1814] border border-[#f5c7bc] text-[#c25e40]"
                }`}
              >
                {publishStatus.type === "success" ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
                <span>{publishStatus.message}</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Metadata note */}
      <div className="p-3 bg-[#ffffff] dark:bg-[#1a1714] border border-[#e6dfd1] dark:border-[#38322b] rounded-xl text-[11px] flex flex-wrap items-center justify-between gap-2 text-[#7f7466] dark:text-[#aba092]">
        <span>Rasio Aspek: <strong>9:16 Vertikal (Shorts / TikTok / Reels)</strong></span>
        <span>Engine: <strong>Omni Flash 1.1 + SnapGen + Zernio</strong></span>
      </div>
    </div>
  );
}
