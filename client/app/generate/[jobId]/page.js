"use client";

import { useParams } from "next/navigation";
import { useEffect, useState, useRef } from "react";
import PipelineProgress from "../../../components/PipelineProgress";
import VideoResult from "../../../components/VideoResult";
import { ArrowLeft, Sun, Moon } from "lucide-react";
import Link from "next/link";

export default function GeneratePage() {
  const { jobId } = useParams();
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState("running"); // running | completed | failed
  const [videoUrl, setVideoUrl] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const [progress, setProgress] = useState(0);
  const [currentMessage, setCurrentMessage] = useState("Starting pipeline...");
  const [logs, setLogs] = useState([]);
  const [isDark, setIsDark] = useState(false);
  const esRef = useRef(null);

  useEffect(() => {
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

  useEffect(() => {
    if (!jobId) return;

    const es = new EventSource(`/api/status/${jobId}`);
    esRef.current = es;

    es.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data);
        setEvents((prev) => [...prev, event]);
        setLogs((prev) => [
          ...prev,
          {
            time: new Date().toLocaleTimeString(),
            message: event.message || event.stage || "",
            type: event.type,
          },
        ]);

        if (event.type === "progress") {
          setProgress(event.progress || 0);
          setCurrentMessage(event.message || "");
        } else if (event.type === "complete") {
          setProgress(100);
          setStatus("completed");
          setVideoUrl(event.video_url);
          setCurrentMessage("Video generation complete!");
          es.close();
        } else if (event.type === "error") {
          setStatus("failed");
          setErrorMsg(event.message || "Generation failed");
          setCurrentMessage("Generation failed");
          es.close();
        }
      } catch (err) {
        console.error("Failed to parse SSE event:", err);
      }
    };

    es.onerror = () => {
      // If SSE drops after completion it's fine; otherwise check job result
      if (status !== "completed") {
        fetch(`/api/result/${jobId}`)
          .then((r) => r.json())
          .then((data) => {
            if (data.status === "completed") {
              setStatus("completed");
              setVideoUrl(data.video_url);
              setProgress(100);
            } else if (data.status === "failed") {
              setStatus("failed");
              setErrorMsg(data.error || "Unknown error");
            }
          })
          .catch(() => {});
      }
      es.close();
    };

    return () => {
      es.close();
    };
  }, [jobId]);

  return (
    <div className="min-h-screen py-8 px-4 sm:px-6 flex flex-col justify-between">
      {/* Top Navigation */}
      <header className="max-w-4xl mx-auto w-full mb-6 flex flex-wrap items-center justify-between gap-4">
        <Link
          href="/"
          className="btn-paper py-2 px-3.5 text-xs font-semibold text-[#2d2621] flex items-center gap-2 cursor-pointer no-underline"
        >
          <ArrowLeft size={14} className="text-[#c25e40]" />
          <span>Kembali ke Studio</span>
        </Link>

        <div className="flex items-center gap-2">
          {status === "running" && (
            <span className="paper-badge badge-honey animate-pulse">
              ● Sedang Merender ({progress}%)
            </span>
          )}
          {status === "completed" && (
            <span className="paper-badge badge-sage">
              ✔ Produksi Selesai (100%)
            </span>
          )}
          {status === "failed" && (
            <span className="paper-badge badge-terracotta">
              ✖ Render Terhenti
            </span>
          )}

          {/* Theme Toggle Button */}
          <button
            type="button"
            onClick={toggleTheme}
            className="btn-paper py-1.5 px-3 text-xs flex items-center gap-1.5 cursor-pointer ml-1"
            title={isDark ? "Ganti ke Tema Terang" : "Ganti ke Tema Gelap"}
          >
            {isDark ? (
              <>
                <Sun size={14} className="text-[#e8a548]" />
                <span className="font-medium text-xs">Terang</span>
              </>
            ) : (
              <>
                <Moon size={14} className="text-[#486683]" />
                <span className="font-medium text-xs">Gelap</span>
              </>
            )}
          </button>
        </div>
      </header>

      {/* Main Notebook Container */}
      <main className="max-w-4xl mx-auto w-full paper-sheet p-6 sm:p-10 mb-8 space-y-6">
        {/* Page Header */}
        <div className="pb-6 border-b border-[#e6dfd1] flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#c25e40] mb-1 uppercase tracking-wider">
              <span>🎬</span>
              <span>Lembar Produksi &amp; Pemantauan Job</span>
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-[#2d2621]">
              Status Eksekusi Serial AI
            </h2>
          </div>
          <div className="text-right">
            <span className="text-[11px] text-[#7f7466] block">ID Naskah / Job:</span>
            <code className="text-xs font-mono font-semibold text-[#2d2621] bg-[#f4efe6] px-2 py-1 rounded-md border border-[#e6dfd1]">
              {jobId}
            </code>
          </div>
        </div>

        {/* Video Result Card (When Completed) */}
        {status === "completed" && videoUrl && (
          <div className="paper-card p-6 border-[#587955]/30">
            <VideoResult videoUrl={videoUrl} jobId={jobId} />
          </div>
        )}

        {/* Error Notification */}
        {status === "failed" && errorMsg && (
          <div className="p-4 rounded-xl bg-[#fcf0ec] border border-[#f5d7ce] text-[#9e4328] space-y-1">
            <div className="font-bold text-xs flex items-center gap-1.5">
              <span>⚠️</span>
              <span>Kompilasi Video Mengalami Kendala</span>
            </div>
            <p className="text-xs font-mono">{errorMsg}</p>
          </div>
        )}

        {/* Pipeline Progress */}
        <PipelineProgress
          progress={progress}
          currentMessage={currentMessage}
          status={status}
          logs={logs}
        />
      </main>

      {/* Clean Footer */}
      <footer className="max-w-4xl mx-auto w-full text-center py-4 text-xs text-[#aba092] border-t border-[#e6dfd1]/60">
        MicroDrama Studio &bull; Local Native Pipeline &bull; ID: {jobId}
      </footer>
    </div>
  );
}
