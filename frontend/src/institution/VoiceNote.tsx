import { useEffect, useRef, useState } from "react";

const bars = 32;
const blankWave = Array<number>(bars).fill(0.09);

export function clockTime(seconds: number) {
  const whole = Math.max(0, Math.floor(seconds));
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}

export function Waveform({
  samples,
  progress = 1,
}: {
  samples: number[];
  progress?: number;
}) {
  return (
    <span className="voice-waveform" aria-hidden="true">
      {samples.map((value, index) => (
        <i
          key={index}
          data-played={index < progress * samples.length || undefined}
          style={{ height: `${Math.max(8, value * 100)}%` }}
        />
      ))}
    </span>
  );
}

export function VoicePlayer({ url, blob }: { url: string; blob: Blob }) {
  const audio = useRef<HTMLAudioElement>(null);
  const [position, setPosition] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [samples, setSamples] = useState(blankWave);
  const [error, setError] = useState(false);
  useEffect(() => {
    if (typeof AudioContext === "undefined") return;
    let active = true;
    const context = new AudioContext();
    void blob
      .arrayBuffer()
      .then((data) => {
        if (active) return context.decodeAudioData(data);
      })
      .then((decoded) => {
        if (!active || !decoded) return;
        const track = decoded.getChannelData(0);
        const width = Math.max(1, Math.floor(track.length / bars));
        const peaks = blankWave.map((_, index) => {
          let peak = 0;
          for (
            let sample = index * width;
            sample < Math.min((index + 1) * width, track.length);
            sample += 8
          )
            peak = Math.max(peak, Math.abs(track[sample]));
          return peak;
        });
        const max = Math.max(0.06, ...peaks);
        setSamples(peaks.map((peak) => Math.sqrt(peak / max)));
      })
      .catch(() => {})
      .finally(() => {
        if (context.state !== "closed") void context.close().catch(() => {});
      });
    return () => {
      active = false;
      if (context.state !== "closed") void context.close().catch(() => {});
    };
  }, [blob]);
  return (
    <div className="inbox-voice-player">
      <audio
        ref={audio}
        src={url}
        preload="metadata"
        onLoadedMetadata={(event) => {
          const value = event.currentTarget.duration;
          setDuration(Number.isFinite(value) ? value : 0);
        }}
        onTimeUpdate={(event) => setPosition(event.currentTarget.currentTime)}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        onError={() => setError(true)}
      />
      <button
        type="button"
        className="inbox-tool-button voice-play"
        aria-label={playing ? "Pausar audio" : "Reproducir audio"}
        onClick={() => {
          if (!audio.current) return;
          if (audio.current.paused)
            void audio.current.play().catch(() => setError(true));
          else audio.current.pause();
        }}
      >
        <span aria-hidden="true">{playing ? "Ⅱ" : "▶"}</span>
      </button>
      <div className="inbox-voice-track">
        <Waveform
          samples={samples}
          progress={duration ? position / duration : 0}
        />
        {duration > 0 && (
          <input
            type="range"
            aria-label="Posición del audio"
            min={0}
            max={duration}
            step={0.1}
            value={Math.min(position, duration)}
            aria-valuetext={`${clockTime(position)} de ${clockTime(duration)}`}
            onChange={(event) => {
              if (audio.current)
                audio.current.currentTime = Number(event.target.value);
            }}
          />
        )}
        <small>
          {clockTime(position)}
          {duration > 0 ? ` / ${clockTime(duration)}` : ""}
        </small>
        {error && (
          <small role="status">
            No se pudo reproducir el audio. Puedes descargarlo.
          </small>
        )}
      </div>
    </div>
  );
}

type RecordingSession = {
  stream?: MediaStream;
  recorder?: MediaRecorder;
  context?: AudioContext;
  timer?: number;
  cancelled: boolean;
};

export function useVoiceRecording(
  onFile: (file: File) => void,
  onError: (error: string) => void,
) {
  const [status, setStatus] = useState<"idle" | "opening" | "recording">(
    "idle",
  );
  const [elapsed, setElapsed] = useState(0);
  const [samples, setSamples] = useState(blankWave);
  const live = useRef<RecordingSession | null>(null);

  useEffect(
    () => () => {
      const current = live.current;
      if (!current) return;
      current.cancelled = true;
      if (current.recorder?.state === "recording") current.recorder.stop();
      current.stream?.getTracks().forEach((track) => track.stop());
      if (current.context) void current.context.close().catch(() => {});
      clearInterval(current.timer);
      live.current = null;
    },
    [],
  );

  async function start() {
    if (live.current) return;
    if (
      !navigator.mediaDevices?.getUserMedia ||
      typeof MediaRecorder === "undefined"
    ) {
      onError(
        "Este navegador no ofrece grabación. Adjunta un archivo de audio desde el clip.",
      );
      return;
    }
    const current: RecordingSession = { cancelled: false };
    live.current = current;
    setStatus("opening");
    setElapsed(0);
    setSamples(blankWave);
    const release = () => {
      current.stream?.getTracks().forEach((track) => track.stop());
      if (current.context) void current.context.close().catch(() => {});
      clearInterval(current.timer);
      if (live.current === current) {
        live.current = null;
        setStatus("idle");
      }
    };
    try {
      current.stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: { ideal: 1 } },
      });
      if (current.cancelled) return release();
      const format = [
        "audio/webm;codecs=opus",
        "audio/ogg;codecs=opus",
        "audio/mp4",
      ].find((value) => MediaRecorder.isTypeSupported(value));
      const recorder = new MediaRecorder(
        current.stream,
        format ? { mimeType: format } : undefined,
      );
      current.recorder = recorder;
      const chunks: Blob[] = [];
      let size = 0;
      recorder.ondataavailable = ({ data }) => {
        size += data.size;
        if (size > 5_000_000 && !current.cancelled) {
          current.cancelled = true;
          onError("La grabación superó 5 MB. Graba una nota más corta.");
          if (recorder.state === "recording") recorder.stop();
        } else if (!current.cancelled && data.size) chunks.push(data);
      };
      recorder.onstop = () => {
        release();
        if (current.cancelled) return;
        if (!size) {
          onError("No se capturó audio. Revisa el micrófono y graba de nuevo.");
          return;
        }
        const type = recorder.mimeType || chunks[0]?.type;
        const extension = type?.includes("mp4")
          ? "m4a"
          : type?.includes("ogg")
            ? "ogg"
            : "webm";
        onFile(new File(chunks, `nota-de-voz.${extension}`, { type }));
      };
      recorder.onerror = () => {
        if (current.cancelled) return;
        current.cancelled = true;
        release();
        onError(
          "El micrófono dejó de grabar. Vuelve a intentarlo o adjunta un audio.",
        );
      };
      recorder.start(250);
      const startedAt = performance.now();
      let measure = () => 0.09;
      if (typeof AudioContext !== "undefined") {
        try {
          const context = new AudioContext();
          current.context = context;
          void context.resume().catch(() => {});
          const analyser = context.createAnalyser();
          analyser.fftSize = 256;
          context.createMediaStreamSource(current.stream).connect(analyser);
          const buffer = new Uint8Array(analyser.fftSize);
          measure = () => {
            analyser.getByteTimeDomainData(buffer);
            return Math.min(
              1,
              Math.sqrt(
                buffer.reduce(
                  (sum, value) => sum + ((value - 128) / 128) ** 2,
                  0,
                ) / buffer.length,
              ) * 4,
            );
          };
        } catch {
          // Audio capture still works if the browser cannot meter the input.
        }
      }
      setStatus("recording");
      current.timer = window.setInterval(() => {
        const seconds = (performance.now() - startedAt) / 1000;
        setElapsed(seconds);
        setSamples((previous) => [...previous.slice(1), measure()]);
        if (seconds >= 300 && recorder.state === "recording") recorder.stop();
      }, 100);
    } catch {
      release();
      if (!current.cancelled)
        onError(
          "No se pudo abrir el micrófono. Habilita el permiso en el navegador o adjunta un audio.",
        );
    }
  }

  function stop(cancel = false) {
    const current = live.current;
    if (!current) return;
    current.cancelled = cancel;
    if (current.recorder?.state === "recording") current.recorder.stop();
    else if (cancel) {
      live.current = null;
      setStatus("idle");
    }
  }
  return { start, stop, status, elapsed, samples };
}
