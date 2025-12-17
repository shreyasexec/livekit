import { useEffect, useState } from 'react'
import {
  LiveKitRoom,
  RoomAudioRenderer,
  useLocalParticipant,
  useTracks,
  VideoConference,
  ControlBar,
  GridLayout,
  ParticipantTile,
} from '@livekit/components-react'
import { Track, Room as LiveKitRoomType } from 'livekit-client'
import '@livekit/components-styles'
import TranscriptPanel from './TranscriptPanel'
import ParticipantTileWithSpeaking from './ParticipantTileWithSpeaking'

interface RoomProps {
  token: string
  serverUrl: string
  onDisconnect: () => void
}

function RoomContent() {
  const { localParticipant } = useLocalParticipant()
  const [micEnabled, setMicEnabled] = useState(true)
  const [cameraEnabled, setCameraEnabled] = useState(false)

  const tracks = useTracks(
    [
      { source: Track.Source.Camera, withPlaceholder: true },
      { source: Track.Source.Microphone, withPlaceholder: false },
    ],
    { onlySubscribed: false }
  )

  useEffect(() => {
    // Enable microphone by default
    localParticipant.setMicrophoneEnabled(true).catch(err => {
      console.error('Failed to enable microphone:', err)
    })
  }, [localParticipant])

  const toggleMic = async () => {
    try {
      await localParticipant.setMicrophoneEnabled(!micEnabled)
      setMicEnabled(!micEnabled)
    } catch (err) {
      console.error('Failed to toggle microphone:', err)
    }
  }

  const toggleCamera = async () => {
    try {
      await localParticipant.setCameraEnabled(!cameraEnabled)
      setCameraEnabled(!cameraEnabled)
    } catch (err) {
      console.error('Failed to toggle camera:', err)
    }
  }

  return (
    <div className="h-screen flex bg-gray-900">
      {/* Left Side - Video and Controls */}
      <div className="flex-1 flex flex-col">
        {/* Video Grid */}
        <div className="flex-1 p-4">
          <GridLayout tracks={tracks} style={{ height: '100%' }}>
            <ParticipantTileWithSpeaking />
          </GridLayout>
        </div>

        {/* Control Bar */}
        <div className="p-4 bg-gray-800 border-t border-gray-700">
          <div className="flex justify-center gap-4">
            <button
              onClick={toggleMic}
              className={`px-6 py-3 rounded-lg font-semibold transition-colors ${
                micEnabled
                  ? 'bg-blue-600 hover:bg-blue-700 text-white'
                  : 'bg-red-600 hover:bg-red-700 text-white'
              }`}
            >
              {micEnabled ? '🎤 Mic On' : '🎤 Mic Off'}
            </button>

            <button
              onClick={toggleCamera}
              className={`px-6 py-3 rounded-lg font-semibold transition-colors ${
                cameraEnabled
                  ? 'bg-blue-600 hover:bg-blue-700 text-white'
                  : 'bg-gray-600 hover:bg-gray-700 text-white'
              }`}
            >
              {cameraEnabled ? '📹 Camera On' : '📹 Camera Off'}
            </button>
          </div>

          <div className="mt-4 text-center text-sm text-gray-400">
            <p>💡 Speak into your microphone - the AI agent will respond to you!</p>
            <p className="mt-1">Participants: {tracks.length}</p>
          </div>
        </div>
      </div>

      {/* Right Side - Transcriptions Panel */}
      <div className="w-96 p-4 border-l border-gray-700">
        <TranscriptPanel />
      </div>

      {/* Audio Renderer */}
      <RoomAudioRenderer />
    </div>
  )
}

export default function Room({ token, serverUrl, onDisconnect }: RoomProps) {
  const [room, setRoom] = useState<LiveKitRoomType>()

  const handleConnected = (room: LiveKitRoomType) => {
    console.log('✅ Connected to room:', room.name)
    setRoom(room)
  }

  const handleDisconnected = () => {
    console.log('❌ Disconnected from room')
    setRoom(undefined)
    onDisconnect()
  }

  const handleError = (error: Error) => {
    console.error('❌ Room error:', error)
    alert(`Connection error: ${error.message}`)
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
      options={{
        // Ensure audio is published with correct source
        audioCaptureDefaults: {
          autoGainControl: true,
          echoCancellation: true,
          noiseSuppression: true,
        },
        // Adaptive stream settings
        adaptiveStream: true,
        dynacast: true,
      }}
    >
      <RoomContent />
    </LiveKitRoom>
  )
}
