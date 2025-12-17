import { useEffect, useState, useRef } from 'react'
import { useRoomContext } from '@livekit/components-react'
import { RoomEvent } from 'livekit-client'

interface TranscriptEntry {
  speaker: 'user' | 'assistant'
  participantIdentity: string
  participantSid: string
  text: string
  timestamp: string
}

export default function TranscriptPanel() {
  const [transcripts, setTranscripts] = useState<TranscriptEntry[]>([])
  const scrollRef = useRef<HTMLDivElement>(null)
  const room = useRoomContext()

  useEffect(() => {
    if (!room) return

    const handleData = (
      payload: Uint8Array,
      participant: any,
      _kind: any,
      topic?: string
    ) => {
      try {
        const decoded = new TextDecoder().decode(payload)
        const data = JSON.parse(decoded)

        // Handle transcripts from the 'transcripts' topic
        if (topic === 'transcripts' && data?.text) {
          const entry: TranscriptEntry = {
            speaker: data.speaker === 'assistant' ? 'assistant' : 'user',
            participantIdentity: data.participantIdentity || participant?.identity || 'Unknown',
            participantSid: data.participantSid || participant?.sid || 'unknown',
            text: data.text,
            timestamp: data.timestamp || new Date().toISOString(),
          }

          setTranscripts((prev) => {
            // Avoid duplicates
            const isDuplicate = prev.some(
              (t) => t.text === entry.text && t.timestamp === entry.timestamp
            )
            if (isDuplicate) return prev

            const next = [...prev, entry]
            // Keep last 50 messages
            return next.slice(-50)
          })
        }

        // Also handle LiveKit's built-in transcription topic
        if (topic === 'lk.transcription' && data?.text) {
          const entry: TranscriptEntry = {
            speaker: data.speaker === 'assistant' || data.speaker === 'agent' ? 'assistant' : 'user',
            participantIdentity: data.participantIdentity || participant?.identity || 'Unknown',
            participantSid: data.participantSid || participant?.sid || 'unknown',
            text: data.text,
            timestamp: data.timestamp || new Date().toISOString(),
          }

          setTranscripts((prev) => {
            const isDuplicate = prev.some(
              (t) => t.text === entry.text && t.timestamp === entry.timestamp
            )
            if (isDuplicate) return prev

            const next = [...prev, entry]
            return next.slice(-50)
          })
        }
      } catch (err) {
        console.error('Failed to parse transcript data:', err)
      }
    }

    room.on(RoomEvent.DataReceived, handleData)

    return () => {
      room.off(RoomEvent.DataReceived, handleData)
    }
  }, [room])

  // Auto-scroll to bottom when new transcripts arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [transcripts])

  const formatTime = (timestamp: string) => {
    try {
      const date = new Date(timestamp)
      return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })
    } catch {
      return ''
    }
  }

  return (
    <div className="flex flex-col h-full bg-gray-800 rounded-lg border border-gray-700">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-700">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <span>Live Transcript</span>
          <span className="text-sm text-gray-400 ml-auto bg-gray-700 px-2 py-1 rounded">
            {transcripts.length} messages
          </span>
        </h3>
      </div>

      {/* Transcript List */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 space-y-3"
      >
        {transcripts.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="text-5xl mb-4">💬</div>
            <p className="text-gray-400">Transcripts will appear here...</p>
            <p className="text-gray-500 text-sm mt-2">
              Start speaking to see the conversation
            </p>
          </div>
        ) : (
          transcripts.map((entry, index) => (
            <div
              key={`${entry.timestamp}-${index}`}
              className={`p-3 rounded-lg ${
                entry.speaker === 'assistant'
                  ? 'bg-blue-900/30 border-l-4 border-blue-500'
                  : 'bg-green-900/30 border-l-4 border-green-500'
              }`}
            >
              {/* Speaker and Time */}
              <div className="flex items-center justify-between mb-1">
                <span
                  className={`font-semibold text-sm flex items-center gap-2 ${
                    entry.speaker === 'assistant'
                      ? 'text-blue-300'
                      : 'text-green-300'
                  }`}
                >
                  <span
                    className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs ${
                      entry.speaker === 'assistant'
                        ? 'bg-blue-600'
                        : 'bg-green-600'
                    }`}
                  >
                    {entry.speaker === 'assistant' ? '🤖' : '👤'}
                  </span>
                  {entry.speaker === 'assistant'
                    ? 'Trinity AI'
                    : entry.participantIdentity}
                </span>
                <span className="text-xs text-gray-500">
                  {formatTime(entry.timestamp)}
                </span>
              </div>

              {/* Transcript Text */}
              <p className="text-white text-sm leading-relaxed pl-8">
                {entry.text}
              </p>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
