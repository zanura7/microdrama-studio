"use client";

import { useRef, useEffect } from "react";
import {
  FileText,
  Users,
  Layout,
  Image,
  Film,
  Video,
  Scissors,
  CheckCircle,
  Circle,
  Loader2,
} from "lucide-react";

const STAGES = [
  { id: "screenwriter", label: "Story", icon: FileText, progress_range: [5, 25] },
  { id: "characters", label: "Characters", icon: Users, progress_range: [20, 35] },
  { id: "storyboard", label: "Storyboard", icon: Layout, progress_range: [30, 45] },
  { id: "portraits", label: "Portraits", icon: Image, progress_range: [40, 55] },
  { id: "frames", label: "Frames", icon: Film, progress_range: [50, 75] },
  { id: "video", label: "Video", icon: Video, progress_range: [65, 88] },
  { id: "concat", label: "Done", icon: Scissors, progress_range: [88, 100] },
];

function getStageState(stage, progress) {
  const [start, end] = stage.progress_range;
  if (progress >= end) return "done";
  if (progress >= start) return "active";
  return "pending";
}

export default function PipelineProgress({
  progress,
  currentMessage,
  status,
  logs,
}) {
  const logsEndRef = useRef(null);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  return (
    <div className="space-y-6">
      {/* Stage timeline checklist */}
      <div className="paper-card p-5 space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-[#e6dfd1]">
          <span className="font-bold text-sm text-[#2d2621]">Tahapan Produksi Naskah &amp; Render</span>
          <span className="text-xs font-mono font-semibold text-[#c25e40]">{progress}% Selesai</span>
        </div>

        {/* Stage nodes pills */}
        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2">
          {STAGES.map((stage) => {
            const state =
              status === "completed"
                ? "done"
                : status === "failed"
                ? getStageState(stage, progress) === "active"
                  ? "failed"
                  : getStageState(stage, progress)
                : getStageState(stage, progress);

            const Icon = stage.icon;

            return (
              <div
                key={stage.id}
                className={`p-2.5 rounded-xl border text-center transition-all flex flex-col items-center gap-1 ${
                  state === "done"
                    ? "bg-[#ebf3ea] border-[#d2e4d0] text-[#3b5f38]"
                    : state === "active"
                    ? "bg-[#fffdf9] border-[#c25e40] text-[#c25e40] shadow-xs ring-1 ring-[#c25e40]/20"
                    : state === "failed"
                    ? "bg-[#fcf0ec] border-[#f5d7ce] text-[#9e4328]"
                    : "bg-[#ffffff] border-[#e6dfd1] text-[#aba092]"
                }`}
              >
                <div className="flex items-center gap-1 text-[11px] font-semibold">
                  {state === "done" && <CheckCircle size={12} className="text-[#3b5f38]" />}
                  {state === "active" && <Loader2 size={12} className="animate-spin text-[#c25e40]" />}
                  {state === "failed" && <span>✖</span>}
                  {state === "pending" && <Circle size={10} />}
                  <span>{stage.label}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Modern Smooth Progress Bar */}
        <div className="space-y-2 pt-2">
          <div className="flex justify-between items-center text-xs">
            <span className="font-medium text-[#473f37]">{currentMessage}</span>
            <span className="font-mono font-bold text-[#c25e40]">{progress}%</span>
          </div>

          <div className="w-full bg-[#e6dfd1]/60 h-2.5 rounded-full overflow-hidden">
            <div
              className="h-full bg-[#c25e40] rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>

      {/* Flow Studio Style Scene Queue Tracker */}
      <div className="paper-card p-4 space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-[#e6dfd1] dark:border-[#38322b]">
          <div className="flex items-center gap-2">
            <span className="font-bold text-xs text-[#2d2621] dark:text-[#f2ece3]">
              ✦ Antrean Produksi Adegan (Scene Queue)
            </span>
            <span className="paper-badge badge-terracotta text-[10px]">Storyboard Sheet 4-in-1</span>
          </div>
          <span className="text-[11px] font-mono text-[#7f7466] dark:text-[#a89e90]">
            Concurrent: 1 &bull; Auto-Fix: Ready
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
          {[1, 2, 3, 4].map((sceneNum) => {
            const isCompleted = progress >= 88 || status === "completed";
            const isRunning = !isCompleted && progress >= 30 && progress < 88;
            return (
              <div
                key={sceneNum}
                className={`p-2.5 rounded-lg border transition-all flex items-center justify-between ${
                  isCompleted
                    ? "bg-[#f5faf4] dark:bg-[#1a2419] border-[#cbe3c8] dark:border-[#2d402b]"
                    : isRunning
                    ? "bg-[#fffdf9] dark:bg-[#27231e] border-[#c25e40] shadow-xs ring-1 ring-[#c25e40]/20"
                    : "bg-[#fbf7f0] dark:bg-[#1c1916] border-[#e6dfd1] dark:border-[#38322b] opacity-80"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-[#2d2621] dark:text-[#f2ece3]">
                    00{sceneNum}
                  </span>
                  <div className="flex flex-col">
                    <span className="font-medium text-[#473f37] dark:text-[#dcd4c7]">
                      Scene Adegan #{sceneNum}
                    </span>
                    <span className="text-[10px] text-[#7f7466] dark:text-[#998f82]">
                      Grid 2x2 Master Sheet &bull; 9:16 HD
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#f2ece1] dark:bg-[#332c25] text-[#7f7466] dark:text-[#dcd4c7] font-mono">
                    combined
                  </span>
                  {isCompleted ? (
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-[#ebf3ea] text-[#3b5f38] flex items-center gap-1">
                      <CheckCircle size={10} /> done
                    </span>
                  ) : isRunning ? (
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-[#fdf0ec] text-[#c25e40] flex items-center gap-1 animate-pulse">
                      <Loader2 size={10} className="animate-spin" /> running
                    </span>
                  ) : (
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-[#f2ece1] dark:bg-[#332c25] text-[#7f7466] dark:text-[#a89e90]">
                      queued
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Live execution logs note */}
      {logs.length > 0 && (
        <div className="paper-card p-4 space-y-2">
          <div className="flex items-center justify-between pb-2 border-b border-[#e6dfd1]">
            <span className="font-semibold text-xs text-[#2d2621]">Catatan Aktivitas Sistem (Live Logs)</span>
            <span className="text-[11px] text-[#7f7466]">{logs.length} catatan</span>
          </div>
          <div className="p-3 bg-[#ffffff] border border-[#e6dfd1] rounded-xl font-mono text-[11px] max-h-48 overflow-y-auto space-y-1.5 text-[#473f37] select-text">
            {logs.map((log, i) => (
              <div key={i} className="flex gap-2 leading-relaxed">
                <span className="text-[#aba092] select-none">[{log.time}]</span>
                <span
                  className={
                    log.type === "complete"
                      ? "text-[#3b5f38] font-semibold"
                      : log.type === "error"
                      ? "text-[#c25e40] font-semibold"
                      : log.stage === "autofix"
                      ? "text-[#d68d30] font-semibold"
                      : log.stage === "storyboard_sheet"
                      ? "text-[#c25e40] font-semibold"
                      : "text-[#473f37]"
                  }
                >
                  {log.message}
                </span>
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        </div>
      )}
    </div>
  );
}
