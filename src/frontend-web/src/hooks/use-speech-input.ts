import { useCallback, useMemo, useRef, useState } from "react";

type SpeechInputState = {
  supported: boolean;
  listening: boolean;
  error: string | null;
  start: () => void;
  stop: () => void;
};

export function useSpeechInput(onTranscript: (text: string) => void): SpeechInputState {
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const [listening, setListening] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const RecognitionCtor = useMemo<SpeechRecognitionConstructor | null>(() => {
    if (typeof window === "undefined") {
      return null;
    }
    return window.SpeechRecognition || window.webkitSpeechRecognition || null;
  }, []);

  const start = useCallback(() => {
    if (!RecognitionCtor) {
      setError("Speech input is not supported in this browser.");
      return;
    }
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    const recognition = new RecognitionCtor();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const result = event.results?.[0]?.[0]?.transcript;
      if (typeof result === "string" && result.trim()) {
        onTranscript(result.trim());
      }
    };
    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      setError(event.error || "Speech input failed.");
      setListening(false);
    };
    recognition.onend = () => {
      setListening(false);
    };
    recognitionRef.current = recognition;
    setError(null);
    setListening(true);
    recognition.start();
  }, [RecognitionCtor, onTranscript]);

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
    setListening(false);
  }, []);

  return { supported: Boolean(RecognitionCtor), listening, error, start, stop };
}
