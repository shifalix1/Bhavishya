import { useState, useRef, useEffect, useCallback } from "react";
import { ImagePlus, X, ChevronRight, Globe } from "lucide-react";
import { api } from "../lib/api";
import styles from "./Aawaz.module.css";

/**
 * Strips all speak/SSML tags from a raw AI response string.
 * Handles normal tags, escaped variants, markdown bold/italic, and bullet points.
 */
function cleanText(raw) {
  return raw
    .replace(/\\?<\/?speak>/gi, "")
    .replace(/<[^>]+>/g, "")
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/\*(.*?)\*/g, "$1")
    .replace(/^[-*]\s/gm, "")
    .trim();
}

/**
 * Extracts the English TTS sentence from inside a speak tag block.
 * Falls back to the full cleaned text if no speak block is found.
 */
function extractSpeakText(raw) {
  const match = raw.match(/\\?<speak>([\s\S]*?)\\?<\/speak>/i);
  return match ? match[1].trim() : cleanText(raw);
}

/**
 * Returns the best available English voice from the browser's speech synthesis engine.
 * Prefers Google US English, then falls back by locale.
 */
function pickVoice() {
  const voices = window.speechSynthesis?.getVoices() || [];
  return (
    voices.find((v) => v.name === "Google US English") ||
    voices.find((v) => v.name.includes("Google") && v.lang === "en-US") ||
    voices.find((v) => v.lang === "en-US") ||
    voices.find((v) => v.lang === "en-GB") ||
    voices.find((v) => v.lang.startsWith("en-")) ||
    voices[0] ||
    null
  );
}

/**
 * Returns the first supported MIME type for MediaRecorder in the current browser.
 * Returns an empty string if none of the preferred types are supported.
 */
function getSupportedMime() {
  const types = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/mp4",
  ];
  for (const t of types) {
    try {
      if (MediaRecorder.isTypeSupported(t)) return t;
    } catch {
      // Browser does not support this type, continue checking.
    }
  }
  return "";
}

// Toast notification component

function Toast({ toasts, onDismiss }) {
  if (!toasts.length) return null;
  return (
    <div className={styles.toastStack}>
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`${styles.toast} ${styles[`toast_${t.type}`]}`}
        >
          <span>{t.message}</span>
          <button className={styles.toastClose} onClick={() => onDismiss(t.id)}>
            <X size={12} />
          </button>
        </div>
      ))}
    </div>
  );
}

// Main Aawaz component

export default function Aawaz({ student, onReadyForDarpan }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [ready, setReady] = useState(false);
  const [combinedInput, setCombinedInput] = useState(null);
  const [darpanLoading, setDarpanLoading] = useState(false);
  const [understanding, setUnderstanding] = useState(0);
  const [toneSignals, setToneSignals] = useState([]);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [recState, setRecState] = useState("idle"); // "idle" | "recording" | "processing"
  const [recTime, setRecTime] = useState(0);
  const [imagePreview, setImagePreview] = useState(null);
  const [marksheet, setMarksheet] = useState(null);
  const [waveformBars, setWaveformBars] = useState(Array(14).fill(3));
  const [blobSeed, setBlobSeed] = useState(0);
  const [language, setLanguage] = useState("hinglish"); // "hinglish" | "english"
  const [toasts, setToasts] = useState([]);
  const [audioCtxReady, setAudioCtxReady] = useState(false);

  const mrRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);
  const audioCtxRef = useRef(null);
  const waveFrameRef = useRef(null);
  const blobFrameRef = useRef(null);
  const fileRef = useRef(null);
  const bottomRef = useRef(null);
  const initialized = useRef(false);
  const exchangeCount = useRef(0);
  const silenceStartRef = useRef(null);
  const mimeRef = useRef("");
  const toastIdRef = useRef(0);

  // Toast management. dismissToast is declared first so addToast can reference it.

  const dismissToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    (message, type = "error", duration = 4000) => {
      const id = ++toastIdRef.current;
      setToasts((prev) => [...prev, { id, message, type }]);
      if (duration > 0) {
        setTimeout(() => dismissToast(id), duration);
      }
      return id;
    },
    [dismissToast],
  );

  // Text-to-speech: speaks only the English portion inside the speak tag block.

  const speak = useCallback((rawText) => {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const text = extractSpeakText(rawText);
    if (!text) return;
    const utt = new SpeechSynthesisUtterance(text);
    const doSpeak = () => {
      const voice = pickVoice();
      if (voice) utt.voice = voice;
      utt.lang = "en-US";
      utt.rate = 0.93;
      utt.pitch = 1.0;
      utt.onstart = () => setIsSpeaking(true);
      utt.onend = () => setIsSpeaking(false);
      utt.onerror = () => setIsSpeaking(false);
      window.speechSynthesis.speak(utt);
    };
    if (window.speechSynthesis.getVoices().length > 0) {
      doSpeak();
    } else {
      window.speechSynthesis.addEventListener("voiceschanged", doSpeak, {
        once: true,
      });
    }
  }, []);

  const stopSpeaking = useCallback(() => {
    window.speechSynthesis?.cancel();
    setIsSpeaking(false);
  }, []);

  // Tone heuristic: derives signal labels from user message content.

  const detectTone = useCallback((text) => {
    const t = text.toLowerCase();
    const signals = [];
    if (/don'?t know|not sure|confused/.test(t)) signals.push("identity fog");
    if (/parents|family|dad|mom|papa|mummy/.test(t))
      signals.push("family pressure");
    if (text.length < 50 && !/!|\?/.test(text)) signals.push("guarded");
    if (text.length > 180) signals.push("engaged");
    if (/love|hate|amazing|boring|favourite|best|worst/.test(t))
      signals.push("emotional clarity");
    if (/average|okay|fine|normal/.test(t)) signals.push("self-doubt");
    if (/made|built|created|project|design/.test(t))
      signals.push("maker instinct");
    if (/scared|afraid|nervous|worried/.test(t)) signals.push("fear detected");
    if (/secretly|dream|wish|want to/.test(t)) signals.push("hidden ambition");
    return signals;
  }, []);

  const updateUnderstanding = useCallback((count, signals) => {
    setUnderstanding(
      Math.min(Math.min(count * 9, 65) + Math.min(signals.length * 4, 25), 93),
    );
  }, []);

  // Blob orb animation loop

  useEffect(() => {
    let frame;
    const tick = () => {
      setBlobSeed((s) => s + 1);
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    blobFrameRef.current = frame;
    return () => cancelAnimationFrame(frame);
  }, []);

  // Initialise component: set MIME type and display the opener message.

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    mimeRef.current = getSupportedMime();

    const opener = student.is_returning
      ? `<speak>${student.name}, you're back. What changed?</speak> ${student.name}, tu wapas aa gaya. School mein, ghar mein, ya andar - kya badla?`
      : `<speak>Hey ${student.name}. I'm Aawaz. I'm here to listen, not judge. When you have nothing to do and no one's watching - what do you naturally drift towards?</speak> Hey ${student.name}. Main Aawaz hoon - judge karne nahi aaya, sunne aaya hoon. Jab koi nahi dekh raha aur time free ho, toh tu naturally kya karne lagta hai?`;

    setMessages([{ role: "aawaz", content: cleanText(opener) }]);
    speak(opener);
  }, [speak, student]);

  // Auto-scroll to the latest message

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, aiLoading]);

  // Cleanup all active resources on unmount

  useEffect(
    () => () => {
      clearInterval(timerRef.current);
      cancelAnimationFrame(waveFrameRef.current);
      cancelAnimationFrame(blobFrameRef.current);
      audioCtxRef.current?.close();
      if (mrRef.current?.state !== "inactive") mrRef.current?.stop();
      window.speechSynthesis?.cancel();
    },
    [],
  );

  // stopRec is declared before startWaveform so the waveform loop can reference it.

  const stopRec = useCallback(() => {
    clearInterval(timerRef.current);
    cancelAnimationFrame(waveFrameRef.current);
    if (mrRef.current?.state !== "inactive") mrRef.current?.stop();
  }, []);

  /**
   * Drives waveform bar heights from analyser frequency data.
   * Handles silence detection: stops recording after SILENCE_DELAY ms of quiet.
   */
  const startWaveform = useCallback(
    (analyser) => {
      const data = new Uint8Array(analyser.frequencyBinCount);
      const BAR_COUNT = 14;
      const SILENCE_THRESH = 6;
      const SILENCE_DELAY = 1800;
      const frame = () => {
        analyser.getByteTimeDomainData(data);
        const step = Math.floor(data.length / BAR_COUNT);
        setWaveformBars(
          Array.from({ length: BAR_COUNT }, (_, i) => {
            let sum = 0;
            for (let j = 0; j < step; j++) {
              const v = (data[i * step + j] - 128) / 128;
              sum += v * v;
            }
            return Math.max(2, Math.min(30, Math.sqrt(sum / step) * 220));
          }),
        );
        let total = 0;
        for (let i = 0; i < data.length; i++) {
          const v = (data[i] - 128) / 128;
          total += v * v;
        }
        const rms = Math.sqrt(total / data.length) * 100;
        if (rms < SILENCE_THRESH) {
          if (!silenceStartRef.current) silenceStartRef.current = Date.now();
          else if (Date.now() - silenceStartRef.current > SILENCE_DELAY) {
            stopRec();
            return;
          }
        } else {
          silenceStartRef.current = null;
        }
        waveFrameRef.current = requestAnimationFrame(frame);
      };
      waveFrameRef.current = requestAnimationFrame(frame);
    },
    [stopRec],
  );

  // Sends a message to the Aawaz chat API and handles the response.

  const send = useCallback(
    async (textOverride) => {
      const text = (textOverride !== undefined ? textOverride : input).trim();
      if (!text || aiLoading || darpanLoading) return;
      setInput("");
      stopSpeaking();

      // Compute merged signals synchronously to avoid stale closure issues.
      const newSignals = detectTone(text);
      const mergedSignals = [...new Set([...toneSignals, ...newSignals])].slice(
        -7,
      );
      setToneSignals(mergedSignals);

      exchangeCount.current += 1;
      setMessages((m) => [...m, { role: "user", content: text }]);
      setAiLoading(true);

      const payload = marksheet
        ? `${text}\n\n[Marksheet:\n${marksheet}]`
        : text;

      try {
        const res = await api.aawazChat(
          student.name,
          student.grade,
          student.uid,
          payload,
          language,
        );
        const clean = cleanText(res.response);
        setMessages((m) => [...m, { role: "aawaz", content: clean }]);
        speak(res.response);
        updateUnderstanding(exchangeCount.current, mergedSignals);

        if (res.ready_for_darpan && !ready) {
          setReady(true);
          setCombinedInput(res.combined_input);
          setUnderstanding(95);
        }
      } catch (err) {
        console.error("[AAWAZ/SEND]", err);
        const isOffline = !navigator.onLine;
        const toastMsg = isOffline
          ? "You appear to be offline. Trying local model..."
          : "Something went wrong reaching the server. Try again.";
        setMessages((m) => [
          ...m,
          {
            role: "aawaz",
            content: "Something went wrong. Try again in a moment.",
          },
        ]);
        addToast(toastMsg, "error");
      } finally {
        setAiLoading(false);
      }
    },
    [
      input,
      aiLoading,
      darpanLoading,
      toneSignals,
      marksheet,
      language,
      ready,
      student,
      speak,
      stopSpeaking,
      detectTone,
      updateUnderstanding,
      addToast,
    ],
  );

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  // Starts microphone recording and initialises AudioContext for waveform visualisation.

  const startRec = useCallback(async () => {
    chunksRef.current = [];
    silenceStartRef.current = null;
    stopSpeaking();
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mime = mimeRef.current;
      const mr = mime
        ? new MediaRecorder(stream, { mimeType: mime })
        : new MediaRecorder(stream);
      mrRef.current = mr;
      mr.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      mr.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        cancelAnimationFrame(waveFrameRef.current);
        audioCtxRef.current?.close();
        setAudioCtxReady(false);
        setWaveformBars(Array(14).fill(3));
        setRecState("processing");
        const actualMime = mr.mimeType || mime || "audio/webm";
        const blob = new Blob(chunksRef.current, { type: actualMime });
        const reader = new FileReader();
        reader.onloadend = async () => {
          const b64 = reader.result.split(",")[1];
          try {
            const res = await api.aawazTranscribe(
              student.name,
              student.grade,
              student.uid,
              {
                audio_b64: b64,
                audio_mime: actualMime,
              },
            );
            if (res.transcript?.trim()) {
              setRecState("idle");
              setRecTime(0);
              send(res.transcript.trim());
              return;
            }
          } catch (err) {
            console.error("[AAWAZ/TRANSCRIBE]", err);
            addToast(
              "Voice transcription failed. Please type your message instead.",
              "warning",
            );
          }
          setRecState("idle");
          setRecTime(0);
        };
        reader.readAsDataURL(blob);
      };
      mr.start(200);
      setRecState("recording");
      setRecTime(0);
      timerRef.current = setInterval(() => setRecTime((t) => t + 1), 1000);

      // AudioContext is wrapped in try/catch because Safari and iOS often block it
      // until a direct user gesture. The CSS fallback animation activates instead.
      try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        const ctx = new AudioCtx();
        const analyser = ctx.createAnalyser();
        analyser.fftSize = 512;
        ctx.createMediaStreamSource(stream).connect(analyser);
        audioCtxRef.current = ctx;
        setAudioCtxReady(true);
        startWaveform(analyser);
      } catch {
        setAudioCtxReady(false);
        console.warn("[AAWAZ] AudioContext unavailable, using CSS fallback.");
      }
    } catch {
      addToast(
        "Microphone access denied. Please allow mic permissions and try again.",
        "warning",
      );
    }
  }, [stopSpeaking, send, addToast, startWaveform, student]);

  /**
   * Handles image uploads. Detects marksheets and routes the description to the
   * chat payload for any other image type.
   */
  const handleImage = useCallback(
    async (e) => {
      const file = e.target.files?.[0];
      if (!file || !file.type.startsWith("image/")) return;

      const previewReader = new FileReader();
      previewReader.onload = (ev) => setImagePreview(ev.target.result);
      previewReader.readAsDataURL(file);

      const b64Reader = new FileReader();
      b64Reader.onloadend = async () => {
        const b64 = b64Reader.result.split(",")[1];
        let res;
        try {
          res = await api.aawazTranscribe(
            student.name,
            student.grade,
            student.uid,
            {
              image_b64: b64,
              image_mime: file.type,
            },
          );
        } catch (err) {
          console.error("[AAWAZ/IMAGE]", err);
          addToast(
            "Could not analyse the image. You can still describe it in text.",
            "warning",
          );
          return;
        }

        if (res.marksheet_data) {
          setMarksheet(res.marksheet_data);
          const ackMsg = {
            role: "aawaz",
            content:
              "Got your marksheet. Interesting patterns here. Let us talk a bit more first.",
          };
          setMessages((m) => [...m, ackMsg]);
          speak(ackMsg.content);
          const newSignals = [
            ...new Set([...toneSignals, "evidence uploaded"]),
          ].slice(-7);
          setToneSignals(newSignals);
          updateUnderstanding(exchangeCount.current + 2, newSignals);
        } else if (res.image_description) {
          setMarksheet(null);
          send(`[Image uploaded: ${res.image_description}]`);
        } else {
          addToast(
            "Image uploaded but could not be analysed. Try typing about it instead.",
            "info",
          );
        }
      };
      b64Reader.readAsDataURL(file);
    },
    [student, toneSignals, speak, send, addToast, updateUnderstanding],
  );

  const removeImage = () => {
    setImagePreview(null);
    setMarksheet(null);
    if (fileRef.current) fileRef.current.value = "";
  };

  const handleRunDarpan = async () => {
    if (!combinedInput) return;
    stopSpeaking();
    setDarpanLoading(true);
    await onReadyForDarpan(combinedInput);
    setDarpanLoading(false);
  };

  const toggleLanguage = () => {
    setLanguage((l) => (l === "hinglish" ? "english" : "hinglish"));
  };

  const fmt = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

  const orbState = isSpeaking
    ? "speaking"
    : recState === "recording"
      ? "listening"
      : recState === "processing"
        ? "processing"
        : aiLoading
          ? "thinking"
          : "idle";

  return (
    <div className={styles.root}>
      <Toast toasts={toasts} onDismiss={dismissToast} />

      <div className={styles.messagesArea}>
        <div className={styles.messages}>
          {messages.map((m, i) => (
            <Bubble
              key={`${m.role}-${i}`}
              msg={m}
              isLast={i === messages.length - 1 && m.role === "aawaz"}
            />
          ))}
          {aiLoading && <TypingBubble />}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Stage area with orb and understanding arc */}
      <div className={styles.stage}>
        <AmoebaOrb state={orbState} seed={blobSeed} bars={waveformBars} />
        <div className={styles.stageRight}>
          <div className={styles.stageInfo}>
            <div className={styles.stageNameRow}>
              <span className={styles.stageName}>Aawaz</span>
              <button
                className={`${styles.langToggle} ${language === "english" ? styles.langEn : styles.langHi}`}
                onClick={toggleLanguage}
                title={`Switch to ${language === "hinglish" ? "English" : "Hinglish"}`}
              >
                <Globe size={10} />
                {language === "hinglish" ? "HI/EN" : "EN"}
              </button>
            </div>
            <span className={styles.stageStatus}>
              {orbState === "speaking" && "Speaking..."}
              {orbState === "listening" && `Listening  ${fmt(recTime)}`}
              {orbState === "processing" && "Transcribing..."}
              {orbState === "thinking" && "Thinking..."}
              {orbState === "idle" && "Here"}
            </span>
          </div>
          <div className={styles.understandingWrap}>
            <UnderstandingArc value={understanding} />
            <span className={styles.understandingPct}>{understanding}%</span>
            <span className={styles.understandingLabel}>understood</span>
          </div>
        </div>
      </div>

      {toneSignals.length > 0 && (
        <div className={styles.toneBar}>
          {toneSignals.map((s, i) => (
            <span key={`tone-${i}`} className={styles.toneChip}>
              {s}
            </span>
          ))}
        </div>
      )}

      {ready && (
        <div className={styles.readyBanner}>
          <div className={styles.readyText}>
            <span className={styles.readyBadge}>Enough to proceed</span>
            <p>
              I have heard enough. Darpan will now show your real fingerprint.
            </p>
          </div>
          <button
            className={styles.darpanBtn}
            onClick={handleRunDarpan}
            disabled={darpanLoading}
          >
            {darpanLoading ? (
              "Revealing..."
            ) : (
              <>
                <ChevronRight size={14} /> Reveal Darpan
              </>
            )}
          </button>
        </div>
      )}

      <div className={styles.inputBar}>
        <div className={styles.uploadSlot}>
          {!imagePreview ? (
            <label
              className={styles.uploadBtn}
              title="Upload image or marksheet"
            >
              <ImagePlus size={15} />
              <input
                ref={fileRef}
                type="file"
                accept="image/*"
                onChange={handleImage}
                style={{ display: "none" }}
              />
            </label>
          ) : (
            <div className={styles.thumbWrap}>
              <img src={imagePreview} alt="Uploaded" className={styles.thumb} />
              <button className={styles.removeThumb} onClick={removeImage}>
                <X size={9} />
              </button>
            </div>
          )}
        </div>

        <div className={styles.textWrap}>
          <textarea
            className={styles.textInput}
            placeholder={
              recState === "recording"
                ? `${fmt(recTime)}  Listening...`
                : recState === "processing"
                  ? "Transcribing..."
                  : language === "hinglish"
                    ? "Hinglish ya English mein type kar..."
                    : "Type anything, or tap the mic..."
            }
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            rows={1}
            disabled={darpanLoading || recState !== "idle"}
          />
        </div>

        <button
          className={`${styles.micBtn} ${recState === "recording" ? styles.micActive : ""}`}
          onClick={recState === "recording" ? stopRec : startRec}
          disabled={darpanLoading || aiLoading || recState === "processing"}
          title={recState === "recording" ? "Stop" : "Speak"}
        >
          {recState === "recording" ? (
            <span
              className={`${styles.waveform} ${!audioCtxReady ? styles.waveformFallback : ""}`}
              aria-hidden="true"
            >
              {waveformBars.map((h, i) => (
                <span
                  key={`bar-${i}`}
                  className={styles.waveBar}
                  style={{ height: `${h}px` }}
                />
              ))}
            </span>
          ) : recState === "processing" ? (
            <span className={styles.typingDots}>
              <span />
              <span />
              <span />
            </span>
          ) : (
            <MicIcon />
          )}
          {recState === "recording" && <span className={styles.micRing} />}
        </button>

        {input.trim() && (
          <button
            className={styles.sendBtn}
            onClick={() => send()}
            disabled={aiLoading || darpanLoading}
          >
            <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
              <path d="M14 2L2 7l5 1.5L8.5 14 14 2z" fill="currentColor" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}

// Sub-components

function AmoebaOrb({ state, seed, bars }) {
  const t = seed * 0.016;
  const activity =
    state === "speaking"
      ? 1.0
      : state === "listening"
        ? 0.85
        : state === "thinking"
          ? 0.5
          : 0.2;
  const points = 12;

  const coords = Array.from({ length: points }, (_, i) => {
    const angle = (i / points) * Math.PI * 2;
    const noise =
      Math.sin(angle * 2 + t * 1.1) * 7 * activity +
      Math.sin(angle * 3 - t * 0.7) * 4 * activity +
      Math.sin(angle * 5 + t * 1.5) * 2.5 * activity +
      Math.cos(angle * 2 + t * 0.9) * 3 * activity;
    const barIdx = Math.floor((i / points) * bars.length);
    const barAmp = state === "listening" ? (bars[barIdx] / 30) * 7 : 0;
    const r = 32 + noise + barAmp;
    return [50 + r * Math.cos(angle), 50 + r * Math.sin(angle)];
  });

  const d =
    coords
      .map((p, i) => {
        const prev = coords[(i - 1 + points) % points];
        const next = coords[(i + 1) % points];
        const cpx = p[0] + (next[0] - prev[0]) * 0.18;
        const cpy = p[1] + (next[1] - prev[1]) * 0.18;
        return i === 0 ? `M${p[0]},${p[1]}` : `Q${cpx},${cpy},${p[0]},${p[1]}`;
      })
      .join(" ") + "Z";

  const g1 =
    state === "listening"
      ? "#ffb347"
      : state === "speaking"
        ? "#ff6b35"
        : state === "thinking"
          ? "#ffcc44"
          : "#ff8c42";
  const g2 =
    state === "listening"
      ? "#ff6b35"
      : state === "speaking"
        ? "#ff3d00"
        : state === "thinking"
          ? "#f7a825"
          : "#f54e00";
  const glow =
    state === "speaking"
      ? "rgba(255,61,0,0.4)"
      : state === "listening"
        ? "rgba(255,107,53,0.32)"
        : "rgba(245,78,0,0.22)";

  return (
    <svg
      viewBox="0 0 100 100"
      width="84"
      height="84"
      style={{
        filter: `drop-shadow(0 0 14px ${glow})`,
        overflow: "visible",
        flexShrink: 0,
      }}
    >
      <defs>
        <radialGradient id="aawaz_bg1" cx="40%" cy="36%" r="65%">
          <stop offset="0%" stopColor={g1} />
          <stop offset="100%" stopColor={g2} />
        </radialGradient>
        <radialGradient id="aawaz_bg2" cx="34%" cy="30%" r="42%">
          <stop offset="0%" stopColor="rgba(255,255,255,0.3)" />
          <stop offset="100%" stopColor="rgba(255,255,255,0)" />
        </radialGradient>
      </defs>
      <path d={d} fill="url(#aawaz_bg1)" />
      <path d={d} fill="url(#aawaz_bg2)" />
    </svg>
  );
}

function UnderstandingArc({ value }) {
  const circ = Math.PI * 28;
  const offset = circ - (value / 100) * circ;
  const color =
    value >= 80
      ? "var(--success)"
      : value >= 45
        ? "var(--accent)"
        : "var(--gold)";
  return (
    <svg width="62" height="34" viewBox="0 0 68 38">
      <path
        d="M4 36 A30 30 0 0 1 64 36"
        fill="none"
        stroke="var(--border)"
        strokeWidth="3"
        strokeLinecap="round"
      />
      <path
        d="M4 36 A30 30 0 0 1 64 36"
        fill="none"
        stroke={color}
        strokeWidth="3"
        strokeLinecap="round"
        strokeDasharray={circ}
        strokeDashoffset={offset}
        style={{ transition: "stroke-dashoffset 0.8s ease, stroke 0.4s" }}
      />
    </svg>
  );
}

function Bubble({ msg, isLast }) {
  const isUser = msg.role === "user";
  return (
    <div
      className={`${styles.bubbleRow} ${isUser ? styles.userRow : styles.aawazRow}`}
    >
      {!isUser && <div className={styles.aawazDot} />}
      <div
        className={`${styles.bubble} ${isUser ? styles.userBubble : styles.aawazBubble} ${
          isLast ? styles.lastBubble : ""
        }`}
      >
        {msg.content}
      </div>
    </div>
  );
}

function TypingBubble() {
  return (
    <div className={`${styles.bubbleRow} ${styles.aawazRow}`}>
      <div className={styles.aawazDot} />
      <div className={`${styles.bubble} ${styles.aawazBubble}`}>
        <span className={styles.typingDots}>
          <span />
          <span />
          <span />
        </span>
      </div>
    </div>
  );
}

function MicIcon() {
  return (
    <svg
      width="17"
      height="17"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="9" y="2" width="6" height="12" rx="3" />
      <path d="M5 10a7 7 0 0 0 14 0" />
      <line x1="12" y1="19" x2="12" y2="22" />
      <line x1="8" y1="22" x2="16" y2="22" />
    </svg>
  );
}
