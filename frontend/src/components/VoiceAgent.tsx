import { useEffect, useMemo, useState } from 'react';
import { LiveKitRoom, useVoiceAssistant, RoomAudioRenderer, BarVisualizer, useRoomContext } from '@livekit/components-react';
import { RoomEvent } from 'livekit-client';
import '@livekit/components-styles';

interface VoiceAgentProps {
  token: string;
  serverUrl: string;
  onDisconnect: () => void;
}

function VoiceAssistantUI() {
  const { state, audioTrack } = useVoiceAssistant();
  const room = useRoomContext();
  const [transcripts, setTranscripts] = useState<
    { speaker: string; text: string; timestamp?: string }[]
  >([]);

  useEffect(() => {
    if (!room) return;

    const handleData = (payload: Uint8Array, participant: any, _kind: any, topic?: string) => {
      if (topic !== 'transcripts') return;
      try {
        const decoded = new TextDecoder().decode(payload);
        const data = JSON.parse(decoded);
        if (!data?.text) return;
        const speakerName = data.speaker || participant?.identity || 'unknown';

        setTranscripts((prev) => {
          const next = [...prev, { speaker: speakerName, text: data.text, timestamp: data.timestamp }];
          // keep the list reasonably short
          return next.slice(-30);
        });
      } catch (err) {
        console.error('Failed to parse transcript payload', err);
      }
    };

    room.on(RoomEvent.DataReceived, handleData);
    return () => {
      room.off(RoomEvent.DataReceived, handleData);
    };
  }, [room]);

  const transcriptList = useMemo(
    () =>
      transcripts.map((t, idx) => (
        <div key={`${t.timestamp || idx}-${idx}`} className="flex gap-2 text-sm text-gray-200">
          <span className="px-2 py-1 rounded bg-gray-700 uppercase text-xs font-semibold">
            {t.speaker === 'assistant' ? 'Agent' : 'You'}
          </span>
          <span className="text-gray-100">{t.text}</span>
        </div>
      )),
    [transcripts]
  );

  return (
    <div className="h-screen flex flex-col items-center justify-center bg-gray-900">
      <div className="w-full max-w-4xl p-8 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-800 rounded-lg p-6 shadow-2xl">
          <h2 className="text-white text-2xl font-bold text-center mb-6">AI Voice Agent</h2>

          <div className="h-64 mb-4">
            <BarVisualizer state={state} barCount={5} trackRef={audioTrack} className="h-full" />
          </div>

          <p className="text-center text-gray-300 text-lg capitalize">{state}</p>
          <p className="text-center text-gray-400 text-sm mt-4">Speak naturally - the agent will respond</p>
        </div>

        <div className="bg-gray-800 rounded-lg p-6 shadow-2xl border border-gray-700">
          <h3 className="text-white text-xl font-semibold mb-4">Live Transcript</h3>
          <div className="h-64 overflow-y-auto space-y-3 pr-2 scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800">
            {transcriptList.length > 0 ? (
              transcriptList
            ) : (
              <p className="text-gray-500 text-sm">Transcripts will appear here once you start talking.</p>
            )}
          </div>
        </div>
      </div>

      <RoomAudioRenderer />
    </div>
  );
}

export default function VoiceAgent({ token, serverUrl, onDisconnect }: VoiceAgentProps) {
  return (
    <LiveKitRoom
      token={token}
      serverUrl={serverUrl}
      connect={true}
      audio={true}
      video={false}
      onDisconnected={onDisconnect}
    >
      <VoiceAssistantUI />
    </LiveKitRoom>
  );
}
