import { useState } from 'react'
import { LiveKitRoom, RoomAudioRenderer, VideoConference } from '@livekit/components-react'
import '@livekit/components-styles'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const LIVEKIT_URL = import.meta.env.VITE_LIVEKIT_URL || 'ws://localhost:7880'

interface TokenResponse {
  token: string
  url: string
}

function App() {
  const [roomName, setRoomName] = useState('')
  const [participantName, setParticipantName] = useState('')
  const [token, setToken] = useState('')
  const [connecting, setConnecting] = useState(false)
  const [error, setError] = useState('')

  const generateToken = async () => {
    if (!roomName || !participantName) {
      setError('Please enter both room name and your name')
      return
    }

    setConnecting(true)
    setError('')

    try {
      const response = await fetch(`${API_URL}/api/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          room_name: roomName,
          participant_name: participantName,
        }),
      })

      if (!response.ok) {
        throw new Error(`Failed to get token: ${response.statusText}`)
      }

      const data: TokenResponse = await response.json()
      setToken(data.token)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect')
      setConnecting(false)
    }
  }

  const handleDisconnect = () => {
    setToken('')
    setConnecting(false)
  }

  if (token) {
    return (
      <div className="room-container">
        <LiveKitRoom
          token={token}
          serverUrl={LIVEKIT_URL}
          connect={true}
          audio={true}
          video={true}
          onDisconnected={handleDisconnect}
        >
          <VideoConference />
          <RoomAudioRenderer />
        </LiveKitRoom>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="bg-gray-800 p-8 rounded-lg shadow-2xl w-full max-w-md border border-gray-700">
        <h1 className="text-3xl font-bold mb-2 text-center text-white">
          LiveKit AI Voice Agent
        </h1>
        <p className="text-gray-400 text-center mb-8">
          Join a room to chat with the AI agent
        </p>

        {error && (
          <div className="mb-6 p-4 bg-red-900/50 border border-red-500 rounded-lg">
            <p className="text-red-200 text-sm">{error}</p>
          </div>
        )}

        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Room Name
            </label>
            <input
              type="text"
              value={roomName}
              onChange={(e) => setRoomName(e.target.value)}
              className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg
                       text-white placeholder-gray-400 focus:outline-none focus:ring-2
                       focus:ring-blue-500 focus:border-transparent"
              placeholder="Enter room name (e.g., ai-agent-room)"
              disabled={connecting}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Your Name
            </label>
            <input
              type="text"
              value={participantName}
              onChange={(e) => setParticipantName(e.target.value)}
              className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg
                       text-white placeholder-gray-400 focus:outline-none focus:ring-2
                       focus:ring-blue-500 focus:border-transparent"
              placeholder="Enter your name"
              disabled={connecting}
            />
          </div>

          <button
            onClick={generateToken}
            disabled={connecting}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600
                     text-white font-semibold py-3 px-4 rounded-lg transition-colors
                     duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500
                     focus:ring-offset-2 focus:ring-offset-gray-800"
          >
            {connecting ? 'Connecting...' : 'Join Room'}
          </button>
        </div>

        <div className="mt-8 pt-6 border-t border-gray-700">
          <p className="text-sm text-gray-400 text-center">
            💡 Tip: Use room name "ai-agent-room" to join the AI agent's room
          </p>
        </div>
      </div>
    </div>
  )
}

export default App
