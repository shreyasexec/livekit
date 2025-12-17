import { useEffect, useMemo, useState, useRef } from 'react';
import { LiveKitRoom, useVoiceAssistant, RoomAudioRenderer, BarVisualizer, useRoomContext } from '@livekit/components-react';
import { RoomEvent } from 'livekit-client';
import '@livekit/components-styles';

interface VoiceAgentProps {
  token: string;
  serverUrl: string;
  onDisconnect: () => void;
}

interface VoiceAssistantUIProps {
  onDisconnect: () => void;
}

function VoiceAssistantUI({ onDisconnect }: VoiceAssistantUIProps) {
  const { state, audioTrack } = useVoiceAssistant();
  const room = useRoomContext();
  const [transcripts, setTranscripts] = useState<
    { speaker: string; text: string; timestamp?: string; participantIdentity?: string }[]
  >([]);
  const [agentState, setAgentState] = useState<string>('initializing');
  const [userState, setUserState] = useState<string>('idle');
  const transcriptEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new transcripts arrive
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcripts]);

  useEffect(() => {
    if (!room) return;

    const handleData = (payload: Uint8Array, participant: any, _kind: any, topic?: string) => {
      try {
        const decoded = new TextDecoder().decode(payload);
        const data = JSON.parse(decoded);

        // Handle transcripts
        if (topic === 'transcripts' && data?.text) {
          const speakerType = data.speaker || 'user';
          const participantIdentity = data.participantIdentity || participant?.identity || 'Unknown';
          setTranscripts((prev) => {
            // Avoid duplicates
            const isDuplicate = prev.some(
              (t) => t.text === data.text && t.timestamp === data.timestamp
            );
            if (isDuplicate) return prev;
            const next = [...prev, {
              speaker: speakerType,
              text: data.text,
              timestamp: data.timestamp,
              participantIdentity: participantIdentity
            }];
            return next.slice(-30); // keep the list reasonably short
          });
        }

        // Handle agent status
        if (topic === 'agent_status' && data?.state) {
          setAgentState(data.state);
        }

        // Handle user status
        if (topic === 'user_status' && data?.state) {
          setUserState(data.state);
        }
      } catch (err) {
        console.error('Failed to parse data payload', err);
      }
    };

    room.on(RoomEvent.DataReceived, handleData);
    return () => {
      room.off(RoomEvent.DataReceived, handleData);
    };
  }, [room]);

  const transcriptList = useMemo(
    () =>
      transcripts.map((t, idx) => {
        const isAgent = t.speaker === 'assistant';
        const displayName = isAgent
          ? 'Trinity AI'
          : (t.participantIdentity || 'You');
        return (
          <div
            key={`${t.timestamp || idx}-${idx}`}
            className={`flex gap-3 p-3 rounded-lg ${
              isAgent ? 'bg-blue-900/30 border-l-4 border-blue-500' : 'bg-green-900/30 border-l-4 border-green-500'
            }`}
          >
            <div className="flex-shrink-0">
              <span className={`inline-flex items-center justify-center w-8 h-8 rounded-full text-xs font-bold ${
                isAgent ? 'bg-blue-600 text-white' : 'bg-green-600 text-white'
              }`}>
                {isAgent ? '🤖' : '👤'}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-xs font-semibold ${
                  isAgent ? 'text-blue-300' : 'text-green-300'
                }`}>
                  {displayName}
                </span>
                {t.timestamp && (
                  <span className="text-xs text-gray-500">
                    {new Date(t.timestamp).toLocaleTimeString()}
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-100 break-words">{t.text}</p>
            </div>
          </div>
        );
      }),
    [transcripts]
  );

  // Determine speaking status
  const isAgentSpeaking = agentState.includes('speaking') || state === 'speaking';
  const isUserSpeaking = userState.includes('speaking') || state === 'listening';

  return (
    <div className="h-screen flex flex-col items-center justify-center bg-gray-900">
      <div className="w-full max-w-4xl p-8 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-800 rounded-lg p-6 shadow-2xl">
          <h2 className="text-white text-2xl font-bold text-center mb-6">Trinity AI Voice Agent</h2>

          {/* Speaking Status Indicators */}
          <div className="flex justify-center gap-4 mb-4">
            <div className={`flex items-center gap-2 px-4 py-2 rounded-full transition-all ${
              isUserSpeaking
                ? 'bg-green-600 text-white animate-pulse'
                : 'bg-gray-700 text-gray-400'
            }`}>
              <span className="text-lg">👤</span>
              <span className="text-sm font-semibold">
                {isUserSpeaking ? 'You\'re Speaking' : 'You'}
              </span>
            </div>

            <div className={`flex items-center gap-2 px-4 py-2 rounded-full transition-all ${
              isAgentSpeaking
                ? 'bg-blue-600 text-white animate-pulse'
                : 'bg-gray-700 text-gray-400'
            }`}>
              <span className="text-lg">🤖</span>
              <span className="text-sm font-semibold">
                {isAgentSpeaking ? 'Agent Speaking' : 'Agent'}
              </span>
            </div>
          </div>

          <div className="h-64 mb-4">
            <BarVisualizer state={state} barCount={5} trackRef={audioTrack} className="h-full" />
          </div>

          <p className="text-center text-gray-300 text-lg capitalize mb-2">{state}</p>
          <p className="text-center text-gray-400 text-sm">Speak naturally - the agent will respond</p>

          <button
            onClick={onDisconnect}
            className="w-full mt-6 bg-red-600 hover:bg-red-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 focus:ring-offset-gray-800"
          >
            Disconnect
          </button>
        </div>

        <div className="bg-gray-800 rounded-lg p-6 shadow-2xl border border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-white text-xl font-semibold">Live Transcript</h3>
            <span className="text-xs text-gray-400 bg-gray-700 px-2 py-1 rounded">
              {transcripts.length} messages
            </span>
          </div>
          <div className="h-80 overflow-y-auto space-y-3 pr-2 scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800">
            {transcriptList.length > 0 ? (
              <>
                {transcriptList}
                <div ref={transcriptEndRef} />
              </>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <div className="text-6xl mb-4">💬</div>
                <p className="text-gray-400 text-sm">Transcripts will appear here</p>
                <p className="text-gray-500 text-xs mt-2">Start speaking to see the conversation</p>
              </div>
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
      <VoiceAssistantUI onDisconnect={onDisconnect} />
    </LiveKitRoom>
  );
}
