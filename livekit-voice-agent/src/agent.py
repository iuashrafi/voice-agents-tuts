from dotenv import load_dotenv
import logging
from google.genai import types
from livekit import agents, rtc
from livekit.agents import AgentServer, AgentSession, Agent, room_io
from livekit.plugins import noise_cancellation, silero, google
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from prompts import SOP_PROMPT
 
logger = logging.getLogger("gemini-live-voice-agent")

load_dotenv(".env.local")


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="")
    # TODO: add a hang up fxn



def prewarm(proc: agents.JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: agents.JobContext): 
    # session = AgentSession(
    #     stt="assemblyai/universal-streaming:en",
    #     llm="openai/gpt-4.1-mini",
    #     tts="cartesia/sonic-3:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
    #     vad=silero.VAD.load(),
    #     turn_detection=MultilingualModel(),
    # )

    # await ctx.connect() 
    await ctx.connect(auto_subscribe=True) # Force agent to auto join outbound rooms


    logger.info(f"Call started - Room: {ctx.room.name}")


    session = AgentSession(
        llm=google.realtime.RealtimeModel(
            model="gemini-2.5-flash-native-audio-preview-09-2025",
            voice="Puck",
            temperature=0.8,
            instructions=SOP_PROMPT,  
        ),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
        thinking_config=types.ThinkingConfig(
            include_thoughts=False,  # Disable thinking for faster responses
        ),
    )

    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: noise_cancellation.BVCTelephony() if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP else noise_cancellation.BVC(),
            ),
        ),
    )

    await session.generate_reply(
        instructions="Greet the user and offer your assistance."
    )


if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            agent_name="test_agent",  # Must match dispatch rule!
        )
    )