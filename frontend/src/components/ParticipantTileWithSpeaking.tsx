import { ParticipantTile, useIsSpeaking, useParticipantInfo } from '@livekit/components-react'
import type { Participant } from 'livekit-client'

interface ParticipantTileProps {
  participant: Participant
}

export default function ParticipantTileWithSpeaking({ participant }: ParticipantTileProps) {
  const isSpeaking = useIsSpeaking(participant)
  const { identity, name } = useParticipantInfo({ participant })

  return (
    <div
      className={`relative transition-all duration-300 ${
        isSpeaking
          ? 'ring-4 ring-green-500 ring-opacity-70 shadow-lg shadow-green-500/50 animate-pulse-ring'
          : 'ring-1 ring-gray-600'
      } rounded-lg overflow-hidden`}
    >
      <ParticipantTile participant={participant} />

      {/* Speaking Indicator Badge */}
      {isSpeaking && (
        <div className="absolute top-2 left-2 bg-green-500 text-white px-2 py-1 rounded-full text-xs font-bold flex items-center gap-1 animate-pulse">
          <span className="w-2 h-2 bg-white rounded-full"></span>
          Speaking
        </div>
      )}

      {/* Participant Name Badge */}
      <div className="absolute bottom-2 left-2 bg-black/70 text-white px-3 py-1 rounded-full text-sm">
        {name || identity}
      </div>
    </div>
  )
}
