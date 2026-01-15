import asyncio
from dotenv import load_dotenv
import json
from livekit import api

load_dotenv(".env.local")

 
PHONE_NUMBERS = [
    "+916294148399"      
]

async def test_phone_formats():
    livekit_api = api.LiveKitAPI()
    
    for phone in PHONE_NUMBERS:
        print(f"\nStarted to call Phone number: {phone}")
        
        dial_info = {
            "phone_number": phone,
            "transfer_to": None,
        }
        
        room_name = f"test-{phone.replace('+', '').replace(':', '-')}-{int(asyncio.get_event_loop().time())}"
        
        try:
            await livekit_api.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(
                    room=room_name,
                    agent_name="outbound-call-agent",
                    metadata=json.dumps(dial_info),
                )
            )
            
            print(f"Dispatched call for number: {phone}")
            
            
        except Exception as e:
            print(f"Error dispatching: {e}")
    
    await livekit_api.aclose()

if __name__ == "__main__":
    asyncio.run(test_phone_formats())