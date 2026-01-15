# Voice Agent  

from dotenv import load_dotenv
import logging
import json
from google.genai import types
from livekit import agents, rtc, api
from livekit.agents import AgentServer, AgentSession, Agent, room_io
from livekit.plugins import noise_cancellation, silero, google
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from prompts import SOP_PROMPT
import asyncio
 
logger = logging.getLogger("gemini-live-voice-agent")

load_dotenv(".env.local")

class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SOP_PROMPT)
        self.participant: rtc.RemoteParticipant | None = None

    def set_participant(self, participant: rtc.RemoteParticipant):
        self.participant = participant

    async def hangup(self):
        """Helper function to hang up the call by deleting the room"""
        job_ctx = agents.get_job_context()
        await job_ctx.api.room.delete_room(
            api.DeleteRoomRequest(room=job_ctx.room.name)
        )


def prewarm(proc: agents.JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: agents.JobContext): 
    logger.info(f"Agent entrypoint called - Room: {ctx.room.name}")
    
    await ctx.connect()
    
    print("ctx metadata=", ctx.job.metadata); 

    # Create the session
    session = AgentSession(
        llm=google.realtime.RealtimeModel(
            model="gemini-2.5-flash-native-audio-preview-09-2025",
            voice="Zephyr",
            temperature=0.6, 
            thinking_config=types.ThinkingConfig(
                include_thoughts=False,
            ),
        ),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),   
    )

    agent = Assistant()

    await session.start(
        room=ctx.room,
        agent=agent,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: noise_cancellation.BVCTelephony() 
                if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP 
                else noise_cancellation.BVC(),
            ),
        ),
    )
    
    participant = await ctx.wait_for_participant()
    agent.set_participant(participant)
    logger.info(f"✅ Web participant joined: {participant.identity}")
    
    await session.generate_reply(
        instructions="Greet the user and offer your assistance."
    )


if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            agent_name="voice-call-agent",
        )
    )