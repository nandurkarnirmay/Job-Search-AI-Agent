"use client";
import { useEffect, useRef, useState } from "react";

/* Browser speech-to-text (Web Speech API: Chrome, Edge, Safari). Our server never receives audio: only the transcript
   and timing (speaking time, pauses > 2 s). The browser vendor may process the audio (Chrome uses Google's servers). */
type Recognition = {
  lang: string; continuous: boolean; interimResults: boolean; start(): void; stop(): void;
  onresult: ((e: { resultIndex: number; results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }> }) => void) | null;
  onend: (() => void) | null; onerror: ((e: { error: string }) => void) | null;
};
type Ctor = new () => Recognition;

export function speechSupported(): boolean {
  if (typeof window === "undefined") return false;
  const w = window as unknown as { SpeechRecognition?: Ctor; webkitSpeechRecognition?: Ctor };
  return Boolean(w.SpeechRecognition || w.webkitSpeechRecognition);
}

export interface VoiceResult { transcript: string; durationSeconds: number; longPauses: number }

export default function VoiceInput({ onDone }: { onDone: (r: VoiceResult) => void }) {
  const [recording, setRecording] = useState(false);
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const rec = useRef<Recognition | null>(null);
  const finalText = useRef("");
  const started = useRef(0);
  const lastHeard = useRef(0);
  const pauses = useRef(0);

  useEffect(() => () => rec.current?.stop(), []);

  function start() {
    const w = window as unknown as { SpeechRecognition?: Ctor; webkitSpeechRecognition?: Ctor };
    const C = w.SpeechRecognition || w.webkitSpeechRecognition;
    if (!C) return setError("Voice answers need Chrome, Edge or Safari. You can type instead.");
    const r = new C();
    r.lang = "en-IN";
    r.continuous = true;
    r.interimResults = true;
    finalText.current = "";
    pauses.current = 0;
    started.current = lastHeard.current = Date.now();
    r.onresult = (e) => {
      const now = Date.now();
      if (now - lastHeard.current > 2000) pauses.current += 1;
      lastHeard.current = now;
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const res = e.results[i];
        if (res.isFinal) finalText.current += res[0].transcript + " ";
        else interim += res[0].transcript;
      }
      setText(finalText.current + interim);
    };
    r.onerror = (e) => setError(e.error === "not-allowed" ? "Microphone permission was denied." : `Voice error: ${e.error}`);
    r.onend = () => setRecording(false);
    rec.current = r;
    setError(null);
    setText("");
    r.start();
    setRecording(true);
  }

  function stop() {
    rec.current?.stop();
    setRecording(false);
    const transcript = (finalText.current || text).trim();
    const seconds = Math.max((lastHeard.current - started.current) / 1000, 1);
    if (transcript) onDone({ transcript, durationSeconds: seconds, longPauses: Math.max(pauses.current - 1, 0) });
  }

  return (
    <div className="space-y-2">
      <button type="button" onClick={recording ? stop : start}
        className={`rounded px-3 py-1 text-sm text-white ${recording ? "bg-red-600 hover:bg-red-700" : "bg-slate-800 hover:bg-slate-900"}`}>
        {recording ? "■ Stop & get feedback" : "🎤 Answer by voice"}
      </button>
      {recording && <p className="text-xs text-slate-500">Listening… speak as you would in the interview.</p>}
      {!recording && !text && <p className="text-xs text-slate-500">We never receive audio, only the text. Your browser&apos;s
        speech service (Google for Chrome, Apple for Safari) transcribes it.</p>}
      {text && <p className="rounded bg-slate-50 p-2 text-sm text-slate-700">{text}</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}
