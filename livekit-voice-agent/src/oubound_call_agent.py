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

SIP_OUTBOUND_TRUNK_ID = 'ST_AMQkwPXnuxCa'

class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="")
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
    logger.info(f"🚀 Agent entrypoint called - Room: {ctx.room.name}")
    
    # Connect to the room first
    await ctx.connect()
    
    # Check if this is an outbound call (has metadata with phone number)
    dial_info = None
    if ctx.job.metadata:
        try:
            dial_info = json.loads(ctx.job.metadata)
            logger.info(f"📞 Outbound call detected: {dial_info}")
        except json.JSONDecodeError:
            logger.warning("Could not parse job metadata")
    
    # Create the session
    session = AgentSession(
        llm=google.realtime.RealtimeModel(
            model="gemini-2.5-flash-native-audio-preview-09-2025",
            voice="Puck",
            temperature=0.8,
            instructions=SOP_PROMPT,  
            thinking_config=types.ThinkingConfig(
            include_thoughts=False,
        ),
        ),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
        
    )

    agent = Assistant()

    # If this is an outbound call, dial the number
    if dial_info and "phone_number" in dial_info:
        phone_number = dial_info["phone_number"]
        participant_identity = phone_number
        
        logger.info(f"📱 Dialing {phone_number}...")
        
        # Start session first (before dialing)
        session_started = asyncio.create_task(
            session.start(
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
        )
        
        # Now dial the number
        try:
            await ctx.api.sip.create_sip_participant(
                api.CreateSIPParticipantRequest(
                    room_name=ctx.room.name,
                    sip_trunk_id=SIP_OUTBOUND_TRUNK_ID,
                    sip_call_to=phone_number,
                    participant_identity=participant_identity,
                    participant_name="Customer",
                    wait_until_answered=True,  # Wait for answer!
                    krisp_enabled=True,
                )
            )
            
            # Wait for session to start and participant to join
            await session_started
            participant = await ctx.wait_for_participant(identity=participant_identity)
            logger.info(f"✅ Participant answered: {participant.identity}")
            
            agent.set_participant(participant)
            
            # Greet the caller
            await session.generate_reply(
                instructions="Greet the user and offer your assistance."
            )
            
        except api.TwirpError as e:
            logger.error(
                f"❌ SIP Error: {e.message}, "
                f"Status: {e.metadata.get('sip_status_code')} "
                f"{e.metadata.get('sip_status')}"
            )
            ctx.shutdown()
    
    else:
        # This is an inbound call or regular room join
        logger.info("📥 Inbound call or room join detected")
        
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
        
        await session.generate_reply(
            instructions="Greet the user and offer your assistance."
        )


if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            agent_name="outbound-call-agent",
        )
    )