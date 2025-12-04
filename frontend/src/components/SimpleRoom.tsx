import { useEffect, useRef } from 'react'
import {
  LiveKitRoom,
  RoomAudioRenderer,
  useRoomContext,
  useTracks,
} from '@livekit/components-react'
import { Room as LiveKitRoomType, RoomEvent, Track } from 'livekit-client'
import '@livekit/components-styles'

interface RoomProps {
  token: string
  serverUrl: string
  onDisconnect: () => void
}

function RoomContent() {
  const room = useRoomContext()
  const initialized = useRef(false)

  const tracks = useTracks(
    [
      { source: Track.Source.Camera, withPlaceholder: true },
      { source: Track.Source.Microphone, withPlaceholder: false },
    ],
    { onlySubscribed: false }
  )

  useEffect(() => {
    if (!room || initialized.current) return

    console.log('🎤 Initializing room with', room.localParticipant.identity)

    // Log when tracks are published
    room.on(RoomEvent.LocalTrackPublished, (publication) => {
      console.log('✅ Published track:', publication.source, publication.kind)
    })

    room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
      console.log('✅ Subscribed to track from:', participant.identity)
    })

    initialized.current = true
  }, [room])

  return (
    <div className="h-screen flex flex-col bg-gray-900">
      <div className="flex-1 p-4 overflow-hidden">
        {tracks.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <div className="text-6xl mb-4">🎤</div>
              <p className="text-white text-xl mb-2">Connecting to room...</p>
              <p className="text-gray-400">Please grant microphone permission if prompted</p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 h-full">
            {tracks.map((track) => (
              <div
                key={track.publication?.trackSid || `${track.participant.sid}-${track.source}`}
                className="bg-gray-800 rounded-lg p-4 flex flex-col items-center justify-center"
              >
                <div className="text-4xl mb-2">
                  {track.source === Track.Source.Microphone ? '🎤' : '📹'}
                </div>
                <div className="text-white font-semibold">
                  {track.participant.identity}
                </div>
                <div className="text-gray-400 text-sm">
                  {track.source === Track.Source.Microphone ? 'Microphone' : 'Camera'}
                </div>
                {track.publication?.isMuted && (
                  <div className="text-red-400 text-sm mt-2">Muted</div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="p-4 bg-gray-800 border-t border-gray-700">
        <div className="text-center">
          <p className="text-white font-semibold mb-2">
            {tracks.length === 0
              ? 'Waiting for connection...'
              : `${tracks.length} track(s) active`}
          </p>
          <p className="text-sm text-gray-400">
            💡 Speak into your microphone - the AI agent will respond!
          </p>
        </div>
      </div>

      <RoomAudioRenderer />
    </div>
  )
}

export default function SimpleRoom({ token, serverUrl, onDisconnect }: RoomProps) {
  const handleConnected = (room: LiveKitRoomType) => {
    console.log('✅ Connected to room:', room.name)
    console.log('   Participants:', room.remoteParticipants.size + 1)
  }

  const handleDisconnected = (reason?: any) => {
    console.log('❌ Disconnected from room:', reason)
    onDisconnect()
  }

  const handleError = (error: Error) => {
    console.error('❌ Room error:', error)
  }

  const handleMediaDeviceFailure = (error: Error) => {
    console.error('❌ Media device error:', error)
    alert(`Microphone access failed: ${error.message}\n\nPlease:\n1. Check browser permissions\n2. Ensure no other app is using the microphone\n3. Try refreshing the page`)
  }

  return (
    <LiveKitRoom
      token={token}
      serverUrl={serverUrl}
      connect={true}
      audio={true}
      video={false}
      onConnected={handleConnected}
      onDisconnected={handleDisconnected}
      onError={handleError}
      onMediaDeviceFailure={handleMediaDeviceFailure}
      options={{
        audioCaptureDefaults: {
          autoGainControl: true,
          echoCancellation: true,
          noiseSuppression: true,
        },
        publishDefaults: {
          audioBitrate: 20000,
        },
        adaptiveStream: false,
        dynacast: false,
        expWebAudioMix: false,
      }}
    >
      <RoomContent />
    </LiveKitRoom>
  )
}
