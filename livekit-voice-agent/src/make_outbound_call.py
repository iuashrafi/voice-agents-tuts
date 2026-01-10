import asyncio
from dotenv import load_dotenv

from livekit import api
from livekit.protocol.sip import CreateSIPParticipantRequest

load_dotenv(".env.local")

HARDCODED_PHONE = "+916294148399"

SIP_OUTBOUND_TRUNK_ID = 'ST_QZztRa2dSBka'


async def make_outbound_call():
    livekit_api = api.LiveKitAPI()  # reads env vars

    request = CreateSIPParticipantRequest(
        sip_trunk_id=SIP_OUTBOUND_TRUNK_ID,
        sip_call_to=HARDCODED_PHONE,
        room_name="call-room-1",
        participant_identity="callee",
        participant_name="Customer",
        wait_until_answered=False,
        krisp_enabled=True,
    )

    try:
        participant = await livekit_api.sip.create_sip_participant(request)
        print("📞 Call connected:", participant)
    except Exception as e:
        print("❌ Error creating SIP participant:", e)
    finally:
        await livekit_api.aclose()


if __name__ == "__main__":
    asyncio.run(make_outbound_call())
