import { act, renderHook } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { clockTime, useVoiceRecording } from "../institution/VoiceNote";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

it("meters a recording, counts seconds, prepares the audio, and releases the microphone on cancel", async () => {
  vi.useFakeTimers();
  const stopTrack = vi.fn();
  const onFile = vi.fn();
  const onError = vi.fn();
  vi.stubGlobal("navigator", {
    mediaDevices: {
      getUserMedia: async () => ({ getTracks: () => [{ stop: stopTrack }] }),
    },
  });
  class Recorder {
    static isTypeSupported = () => true;
    mimeType = "audio/webm;codecs=opus";
    state = "inactive";
    ondataavailable?: (event: { data: Blob }) => void;
    onstop?: () => void;
    start() {
      this.state = "recording";
    }
    stop() {
      this.state = "inactive";
      this.ondataavailable?.({ data: new Blob(["voice"]) });
      this.onstop?.();
    }
  }
  class Meter {
    close = async () => {};
    resume = async () => {};
    createMediaStreamSource = () => ({ connect: vi.fn() });
    createAnalyser = () => ({
      fftSize: 256,
      getByteTimeDomainData: (data: Uint8Array) => data.fill(162),
    });
  }
  vi.stubGlobal("MediaRecorder", Recorder);
  vi.stubGlobal("AudioContext", Meter);
  const clock = vi.spyOn(performance, "now").mockReturnValue(0);
  const { result } = renderHook(() => useVoiceRecording(onFile, onError));
  await act(async () => {
    await result.current.start();
  });
  expect(result.current.status).toBe("recording");
  clock.mockReturnValue(2500);
  act(() => {
    vi.advanceTimersByTime(100);
  });
  expect(clockTime(result.current.elapsed)).toBe("0:02");
  expect(result.current.samples.at(-1)).toBeGreaterThan(0.5);
  act(() => result.current.stop());
  expect(result.current.status).toBe("idle");
  expect(onFile.mock.calls[0][0].name).toBe("nota-de-voz.webm");
  await act(async () => {
    await result.current.start();
  });
  act(() => result.current.stop(true));
  expect(onFile).toHaveBeenCalledTimes(1);
  expect(stopTrack).toHaveBeenCalledTimes(2);
  expect(onError).not.toHaveBeenCalled();
});
