"""
LiveKit Agent Server — Entry Point
-----------------------------------
Runs as a separate process alongside FastAPI.

Usage:
    python src/livekit_app.py dev      # Development mode (hot-reload)
    python src/livekit_app.py start    # Production mode
    python src/livekit_app.py --help   # Show CLI help
"""
import json
import os
import sys

# Ensure project root is on sys.path so `from src.xxx` imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from livekit import agents
from livekit.agents import AgentServer, AgentSession, room_io, TurnHandlingOptions
from livekit.plugins import openai, silero, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from src.core.agents.voice_agent import VoiceDataCollectionAgent

server = AgentServer()


@server.rtc_session(agent_name="data-collection-agent")
async def voice_session(ctx: agents.JobContext):
    """Handle an incoming voice call session."""

    # --- Read fields from room metadata (set by FastAPI when creating the room) ---
    fields = None
    if ctx.room.metadata:
        try:
            meta = json.loads(ctx.room.metadata)
            fields = meta.get("fields")
        except (json.JSONDecodeError, TypeError):
            pass

    # --- Build the voice pipeline ---
    session = AgentSession(
        # STT: Deepgram Nova-3 via LiveKit Inference (multilingual, hỗ trợ tiếng Việt)
        stt="deepgram/nova-3:multi",
        # LLM: OpenAI GPT-4.1 mini via LiveKit Inference
        llm="openai/gpt-4.1-mini",
        # TTS: Eleven Labs flash v2.5 via LiveKit Inference
        tts="elevenlabs/eleven_flash_v2_5",
        # VAD: Silero for voice activity detection
        vad=silero.VAD.load(),
        # Turn detection: multilingual model for natural conversation flow
        turn_handling=TurnHandlingOptions(
            turn_detection=MultilingualModel(),
        ),
    )

    # --- Create the agent with dynamic prompt ---
    agent = VoiceDataCollectionAgent(fields=fields)

    # --- Start the session ---
    await session.start(
        room=ctx.room,
        agent=agent,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=noise_cancellation.BVC(),
            ),
        ),
    )

    # --- Generate initial greeting ---
    await session.generate_reply(
        instructions="Chào hỏi khách hàng, giới thiệu bản thân và bắt đầu thu thập thông tin."
    )


if __name__ == "__main__":
    agents.cli.run_app(server)
