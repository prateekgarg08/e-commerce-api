from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import (
    openai,
    noise_cancellation,
    silero,
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit.agents import function_tool, get_job_context, RunContext, ToolError
import json
load_dotenv()


class Assistant(Agent):
    

    @function_tool()
    async def navigate_to_page(
        context: RunContext,
        page_name: str
    ):
        """Navigate to a specific page.
        
        Args:
            page_name: The name of the page to navigate to
        
            page_name can be one of the following:
            - home
            - cart
            - products
            - orders
            - wishlist
            - merchants
            

        
        """
        try:
            room = get_job_context().room
            participant_identity = next(iter(room.remote_participants))
            response = await room.local_participant.perform_rpc(
                destination_identity=participant_identity,
                method="navigate_to_page",
                payload=json.dumps({
                    "page_name": page_name
                }),
                response_timeout=10.0,
            )
            return response
        except Exception:
            raise ToolError("Unable to navigate to page")

    @function_tool()
    async def search_product(
        context: RunContext,
        product_name: str
    ):
        """Search for a product.

        Args:
            product_name: The name of the product to search for

        """
        try:
            room = get_job_context().room
            participant_identity = next(iter(room.remote_participants))
            response = await room.local_participant.perform_rpc(
                destination_identity=participant_identity,
                method="search_product",
                payload=json.dumps({
                    "product_name": product_name
                }),
                response_timeout=10.0,
            )
            return response
        except Exception:
            raise ToolError("Unable to search for product")

    def __init__(self) -> None:
        super().__init__(instructions="You are a helpful voice AI assistant. You can help the user to navigate to different pages of the website. You can also help the user to search for products. ")


async def entrypoint(ctx: agents.JobContext):
    await ctx.connect()

    participant = await ctx.wait_for_participant()

    print(f"Participant connected: {participant.name}")

    session = AgentSession(
        stt=openai.STT(model="whisper-1"),
        llm=openai.LLM(model="gpt-4o"),
        tts=openai.TTS(),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
    )

    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_input_options=RoomInputOptions(
            # LiveKit Cloud enhanced noise cancellation
            # - If self-hosting, omit this parameter
            # - For telephony applications, use `BVCTelephony` for best results
            noise_cancellation=noise_cancellation.BVC(), 
        ),
    )

    await session.generate_reply(
        instructions="Greet the user and offer your assistance."
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))