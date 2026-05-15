import { useState, useRef, useEffect, useCallback } from "react";
import { ImagePlus, X, ChevronRight, Globe } from "lucide-react";
import { api } from "../lib/api";
import styles from "./Aawaz.module.css";

function cleanText(raw) {
  return raw
    .replace(/\\?<\/?speak>/gi, "")
    .replace(/<[^>]+>/g, "")
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/\*(.*?)\*/g, "$1")
    .replace(/^[-*]\s/gm, "")
    .trim();
}

function extractSpeakText(raw) {
  const match = raw.match(/\\?<speak>([\s\S]*?)\\?<\/speak>/i);
  return match ? match[1].trim() : cleanText(raw);
}

function pickVoice() {
  const voices = window.speechSynthesis?.getVoices() || [];
  const enVoices = voices.filter(
    (v) => v.lang.startsWith("en") && v.lang !== "en-IN",
  );
  return (
    enVoices.find((v) => v.name === "Google US English") ||
    enVoices.find((v) => v.name.includes("Samantha")) ||
    enVoices.find((v) => v.name.includes("Alex")) ||
    enVoices.find((v) => v.name.includes("Daniel")) ||
    enVoices.find((v) => v.lang === "en-US" && v.localService) ||
    enVoices.find((v) => v.lang === "en-GB" && v.localService) ||
    enVoices.find((v) => v.lang === "en-US") ||
    enVoices.find((v) => v.lang === "en-GB") ||
    enVoices[0] ||
    null
  );
}

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

// Fire media prompt after this many user exchanges
const MEDIA_PROMPT_EXCHANGE = 1;
const SILENCE_THRESHOLD_MS = 2500;

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
  const [recState, setRecState] = useState("idle");
  const [recTime, setRecTime] = useState(0);
  const [imagePreview, setImagePreview] = useState(null);
  const [marksheet, setMarksheet] = useState(null);
  const [waveformBars, setWaveformBars] = useState(Array(22).fill(3));
  const [language, setLanguage] = useState("english");
  const [toasts, setToasts] = useState([]);
  const [audioCtxReady, setAudioCtxReady] = useState(false);
  const [showMediaPrompt, setShowMediaPrompt] = useState(false);
  const [mediaPromptDismissed, setMediaPromptDismissed] = useState(false);
  const [interimText, setInterimText] = useState("");

  const recRef = useRef(null);
  const streamRef = useRef(null);
  const timerRef = useRef(null);
  const audioCtxRef = useRef(null);
  const waveFrameRef = useRef(null);
  const idleFrameRef = useRef(null);
  const fileRef = useRef(null);
  const fileRef2 = useRef(null);
  const bottomRef = useRef(null);
  const initialized = useRef(false);
  const exchangeCount = useRef(0);
  const toastIdRef = useRef(0);
  const idleSeedRef = useRef(0);
  const silenceTimerRef = useRef(null);
  const lastInterimRef = useRef("");
  const finalTranscriptRef = useRef("");

  const dismissToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    (message, type = "error", duration = 4000) => {
      const id = ++toastIdRef.current;
      setToasts((prev) => [...prev, { id, message, type }]);
      if (duration > 0) setTimeout(() => dismissToast(id), duration);
      return id;
    },
    [dismissToast],
  );

  // Idle breathing animation
  useEffect(() => {
    const BAR_COUNT = 22;
    const tick = () => {
      idleSeedRef.current += 1;
      const t = idleSeedRef.current * 0.035;
      setWaveformBars((prev) => {
        if (audioCtxReady) return prev;
        return Array.from({ length: BAR_COUNT }, (_, i) => {
          const phase = (i / BAR_COUNT) * Math.PI * 2;
          return 3 + Math.abs(Math.sin(t + phase) * 6);
        });
      });
      idleFrameRef.current = requestAnimationFrame(tick);
    };
    idleFrameRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(idleFrameRef.current);
  }, [audioCtxReady]);

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
      utt.rate = 0.92;
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

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    const opener = student.is_returning
      ? `${student.name}, you're back. What changed since we last spoke?`
      : `Hey ${student.name}. I'm Aawaz. I'm here to listen, not judge. When you have nothing to do and no one's watching, what do you naturally drift towards?`;
    setMessages([{ role: "aawaz", content: opener }]);
    speak(opener);
  }, [speak, student]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, aiLoading]);

  useEffect(
    () => () => {
      clearInterval(timerRef.current);
      clearTimeout(silenceTimerRef.current);
      cancelAnimationFrame(waveFrameRef.current);
      cancelAnimationFrame(idleFrameRef.current);
      audioCtxRef.current?.close();
      recRef.current?.abort?.();
      streamRef.current?.getTracks().forEach((t) => t.stop());
      window.speechSynthesis?.cancel();
    },
    [],
  );

  const startWaveform = useCallback((analyser) => {
    const data = new Uint8Array(analyser.frequencyBinCount);
    const BAR_COUNT = 22;
    const frame = () => {
      analyser.getByteFrequencyData(data);
      const step = Math.floor(data.length / BAR_COUNT);
      setWaveformBars(
        Array.from({ length: BAR_COUNT }, (_, i) => {
          let sum = 0;
          for (let j = 0; j < step; j++) sum += data[i * step + j];
          return Math.max(3, Math.min(44, (sum / step / 255) * 44));
        }),
      );
      waveFrameRef.current = requestAnimationFrame(frame);
    };
    waveFrameRef.current = requestAnimationFrame(frame);
  }, []);

  const send = useCallback(
    async (textOverride) => {
      const text = (textOverride !== undefined ? textOverride : input).trim();
      if (!text || aiLoading || darpanLoading) return;
      setInput("");
      setInterimText("");
      stopSpeaking();
      const newSignals = detectTone(text);
      const mergedSignals = [...new Set([...toneSignals, ...newSignals])].slice(
        -7,
      );
      setToneSignals(mergedSignals);
      exchangeCount.current += 1;
      setMessages((m) => [...m, { role: "user", content: text }]);
      setAiLoading(true);

      // Show media prompt after first user exchange if not uploaded/dismissed
      if (
        exchangeCount.current === MEDIA_PROMPT_EXCHANGE &&
        !imagePreview &&
        !marksheet &&
        !mediaPromptDismissed
      ) {
        setShowMediaPrompt(true);
      }

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
          setShowMediaPrompt(false);
        }
      } catch (err) {
        console.error("[AAWAZ/SEND]", err);
        setMessages((m) => [
          ...m,
          {
            role: "aawaz",
            content: "Something went wrong. Try again in a moment.",
          },
        ]);
        addToast("Could not reach the server. Check your connection.", "error");
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
      imagePreview,
      mediaPromptDismissed,
    ],
  );

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const stopRec = useCallback(() => {
    clearInterval(timerRef.current);
    clearTimeout(silenceTimerRef.current);
    cancelAnimationFrame(waveFrameRef.current);
    if (recRef.current) {
      try {
        recRef.current.stop();
      } catch {
        /* ignore */
      }
    }
    audioCtxRef.current?.close().catch(() => {});
    streamRef.current?.getTracks().forEach((t) => t.stop());
    setAudioCtxReady(false);
    setRecState("idle");
    setRecTime(0);
    setInterimText("");
  }, []);

  const startRec = useCallback(async () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      addToast(
        "Voice input not supported in this browser. Type instead.",
        "warning",
      );
      return;
    }
    stopSpeaking();
    finalTranscriptRef.current = "";
    lastInterimRef.current = "";

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      const ctx = new AudioCtx();
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 1024;
      ctx.createMediaStreamSource(stream).connect(analyser);
      audioCtxRef.current = ctx;
      setAudioCtxReady(true);
      startWaveform(analyser);
    } catch {
      // no waveform, still continue
    }

    const rec = new SR();
    recRef.current = rec;
    rec.lang = language === "hinglish" ? "hi-IN" : "en-US";
    rec.continuous = true;
    rec.interimResults = true;

    setRecState("recording");
    setRecTime(0);
    timerRef.current = setInterval(() => setRecTime((t) => t + 1), 1000);

    const scheduleAutoStop = () => {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = setTimeout(() => {
        const text = finalTranscriptRef.current.trim();
        if (text) {
          stopRec();
          setInput("");
          send(text);
        } else {
          stopRec();
        }
      }, SILENCE_THRESHOLD_MS);
    };

    rec.onresult = (e) => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) {
          finalTranscriptRef.current += e.results[i][0].transcript + " ";
        } else {
          interim += e.results[i][0].transcript;
        }
      }
      const combined = finalTranscriptRef.current + interim;
      setInput(combined);
      setInterimText(interim);
      lastInterimRef.current = interim;
      scheduleAutoStop();
    };

    rec.onend = () => {
      const text = finalTranscriptRef.current.trim();
      clearInterval(timerRef.current);
      clearTimeout(silenceTimerRef.current);
      cancelAnimationFrame(waveFrameRef.current);
      audioCtxRef.current?.close().catch(() => {});
      streamRef.current?.getTracks().forEach((t) => t.stop());
      setAudioCtxReady(false);
      setRecState("idle");
      setRecTime(0);
      setInterimText("");
      if (text) {
        setInput("");
        send(text);
      }
    };

    rec.onerror = (e) => {
      if (e.error !== "no-speech" && e.error !== "aborted") {
        addToast("Could not hear you clearly. Please type.", "warning");
      }
    };

    try {
      rec.start();
      scheduleAutoStop();
    } catch {
      addToast("Could not start voice input. Please type.", "warning");
      setRecState("idle");
    }
  }, [stopSpeaking, send, stopRec, addToast, startWaveform, language]);

  const handleImage = useCallback(
    async (e) => {
      const file = e.target.files?.[0];
      if (!file || !file.type.startsWith("image/")) return;
      e.target.value = "";
      setShowMediaPrompt(false);
      setMediaPromptDismissed(true);

      const previewReader = new FileReader();
      previewReader.onload = (ev) => setImagePreview(ev.target.result);
      previewReader.readAsDataURL(file);

      setMessages((m) => [
        ...m,
        { role: "aawaz", content: "Let me take a look at that..." },
      ]);

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
            "Could not analyse the image. Describe it in text instead.",
            "warning",
          );
          setMessages((m) => m.slice(0, -1));
          return;
        }

        setMessages((m) => m.slice(0, -1));

        if (res.marksheet_data) {
          setMarksheet(res.marksheet_data);
          const ackMsg = {
            role: "aawaz",
            content:
              "Got your marksheet. There are some interesting patterns here. Tell me one thing -- which subject surprised you most, in either direction?",
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
          const ackMsg = {
            role: "aawaz",
            content: `I can see: ${res.image_description}. What does this mean to you?`,
          };
          setMessages((m) => [...m, ackMsg]);
          speak(ackMsg.content);
          const newSignals = [
            ...new Set([...toneSignals, "visual shared"]),
          ].slice(-7);
          setToneSignals(newSignals);
          updateUnderstanding(exchangeCount.current + 1, newSignals);
        } else {
          addToast(
            "Image uploaded but could not be analysed. Try typing about it.",
            "info",
          );
        }
      };
      b64Reader.readAsDataURL(file);
    },
    [student, toneSignals, speak, addToast, updateUnderstanding],
  );

  const removeImage = () => {
    setImagePreview(null);
    setMarksheet(null);
    if (fileRef.current) fileRef.current.value = "";
    if (fileRef2.current) fileRef2.current.value = "";
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

  const waveState = isSpeaking
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
          {recState === "recording" && interimText && (
            <div className={`${styles.bubbleRow} ${styles.userRow}`}>
              <div
                className={`${styles.bubble} ${styles.userBubble}`}
                style={{ opacity: 0.5, fontStyle: "italic" }}
              >
                {interimText}
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Stage bar */}
      <div className={styles.stage}>
        <div className={styles.stageLeft}>
          <WaveVisualizer bars={waveformBars} state={waveState} />
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
              {waveState === "speaking" && "Speaking..."}
              {waveState === "listening" && (
                <span className={styles.listeningRow}>
                  <span className={styles.listeningDot} />
                  Listening {fmt(recTime)} -- keep talking
                </span>
              )}
              {waveState === "processing" && "Processing..."}
              {waveState === "thinking" && "Thinking..."}
              {waveState === "idle" && "Here"}
            </span>
          </div>
        </div>
        <div className={styles.stageRight}>
          <div className={styles.understandingWrap}>
            <UnderstandingArc value={understanding} />
            <span className={styles.understandingPct}>{understanding}%</span>
            <span className={styles.understandingLabel}>UNDERSTOOD</span>
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

      {/* Multimedia prompt -- fires after first user exchange */}
      {showMediaPrompt && !ready && (
        <div className={styles.mediaBanner}>
          <p className={styles.mediaBannerText}>
            <strong>Show me something real.</strong> A marksheet, a project
            photo, or a sketch. Aawaz reads images and it changes everything.
          </p>
          <label className={styles.mediaBannerUpload}>
            <ImagePlus size={13} />
            Upload
            <input
              ref={fileRef2}
              type="file"
              accept="image/*"
              onChange={handleImage}
              style={{ display: "none" }}
            />
          </label>
          <button
            className={styles.mediaDismiss}
            onClick={() => {
              setShowMediaPrompt(false);
              setMediaPromptDismissed(true);
            }}
          >
            Skip
          </button>
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
                ? `${fmt(recTime)}  Listening -- keep talking, auto-sends on silence...`
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
          title={recState === "recording" ? "Stop recording" : "Speak"}
        >
          {recState === "recording" ? (
            <StopIcon />
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

        {input.trim() && recState === "idle" && (
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

function WaveVisualizer({ bars, state }) {
  const isActive = state === "listening" || state === "speaking";
  const color =
    state === "listening" || state === "speaking"
      ? "var(--accent)"
      : state === "thinking"
        ? "var(--gold)"
        : "var(--border-warm)";
  const midpoint = Math.floor(bars.length / 2);
  return (
    <div className={styles.waveViz} aria-hidden="true">
      {bars.map((h, i) => {
        const distFromCenter = Math.abs(i - midpoint) / midpoint;
        const scaledH = h * (1 - distFromCenter * 0.3);
        return (
          <span
            key={i}
            className={styles.waveVizBar}
            style={{
              height: `${Math.max(3, scaledH)}px`,
              background: color,
              opacity: isActive ? 0.8 + (1 - distFromCenter) * 0.2 : 0.5,
              transition: isActive
                ? "height 0.05s ease, opacity 0.2s"
                : "height 0.4s ease, opacity 0.4s",
            }}
          />
        );
      })}
    </div>
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
        className={`${styles.bubble} ${isUser ? styles.userBubble : styles.aawazBubble} ${isLast ? styles.lastBubble : ""}`}
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

function StopIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
      <rect x="4" y="4" width="16" height="16" rx="2" />
    </svg>
  );
}
