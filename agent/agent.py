"""LiveKit resident-facing agent and adapter to the EffiGov case API.

LiveKit events are normalized into call and transcript API requests here, keeping
SDK-specific objects out of the backend and dashboard layers.
"""

import asyncio
import logging
import textwrap

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    RunContext,
    StopResponse,
    TurnHandlingOptions,
    cli,
    function_tool,
    inference,
)

from case_api import CaseApiClient, CaseApiError


# Prefer the documented local file while accepting the common .env filename.
load_dotenv(".env.local")
load_dotenv(".env")
logger = logging.getLogger(__name__)


class EffiGovAgent(Agent):
    """Constrained voice workflow for reporting and managing missed pickups."""

    def __init__(self, case_api: CaseApiClient, call_id: int | None) -> None:
        super().__init__(
            llm=inference.LLM(model="google/gemma-4-31b-it"),
            instructions=textwrap.dedent(
                """\
                You are a city service assistant helping residents report service issues.
                You represent Sacramento County City and Trash Services. You can help with
                missed trash pickup reports, recycling and trash schedule questions, existing
                trash-service cases, and general trash or recycling questions.

                If a request is outside trash or recycling services and is not an emergency,
                explain briefly that it is outside this team's scope and ask whether the
                resident would like to be routed to the appropriate city department. Do not
                claim that a transfer happened: this demo cannot actually route calls. If they
                want help after that, suggest contacting the city's main service line.

                If the resident describes an immediate emergency, danger, medical emergency,
                fire, crime in progress, or urgent need for police, begin with a brief caring
                acknowledgment, then tell them to call 911 now. For example: "I'm so sorry to
                hear that. That sounds serious. Please call 911 now for immediate help."
                Keep that response short and do not attempt to handle the emergency yourself.

                The session starts with a spoken greeting that already explains the available
                help, including general questions about trash pickup. If the resident then
                says hello or greets you, respond briefly, such as "Hi, how can I help today?"
                Do not repeat the menu unless the resident asks what you can help with.

                When a resident wants to report an issue, understand the issue and collect
                their name, phone number, and a short useful description. Do not ask again
                for information the resident has already provided. Use issue_type
                "missed_pickup" for this workflow.

                For general trash or recycling schedule questions, always use
                lookup_service_schedule. If the city is not known from the current
                conversation, ask which city they are in before calling the tool. Never
                invent schedule information. Clearly say that returned schedules are for
                this demo. If the tool says the city is unsupported, explain that this demo
                has service information only for its supported locations. If a schedule
                question turns into a missed-pickup report, continue into the existing case
                creation flow and ask only for information that is still missing.

                Once all required information is available, call create_case exactly once.
                Never claim a case was created unless the tool reports success. On success,
                clearly tell the resident the returned case number and say their missed
                pickup has been sent to the sanitation team for follow-up. Use reassuring
                wording such as "We'll arrange a follow-up pickup as soon as possible," but
                do not promise an exact arrival time. If the tool fails, apologize briefly
                and explain that the case could not be created.

                After completing a resident's request, ask whether they need anything else.
                If they say no, no thanks, goodbye, or otherwise indicate they are finished,
                use end_conversation. Do not use it until the resident clearly indicates the
                conversation is over.

                If a resident asks about an existing case, use lookup_case. If they request
                an update and you know the database case ID, use update_case.

                Keep every response short, natural for speech, and ask one question at a time.
                Use plain text only. Do not mention tool names, JSON, or internal systems.
                """
            ),
        )
        self.case_api = case_api
        self.call_id = call_id

    @function_tool
    async def create_case(
        self,
        context: RunContext,
        name: str,
        phone: str,
        issue_type: str,
        description: str,
    ) -> dict[str, str | bool]:
        """Create a city service case after collecting all required information.

        Args:
            name: Resident's name.
            phone: Resident's phone number.
            issue_type: Use "missed_pickup" for the supported workflow.
            description: Short description of the missed pickup.
        """
        try:
            case = await self.case_api.create_case(name, phone, issue_type, description)
        except CaseApiError as error:
            return {"success": False, "message": str(error)}

        if self.call_id is not None:
            try:
                await self.case_api.update_call(
                    self.call_id,
                    {
                        "case_id": case["id"],
                        "caller_name": name,
                        "phone": phone,
                        "issue_type": issue_type,
                    },
                )
            except CaseApiError:
                logger.warning("Case %s was created but could not be linked to call", case["id"])

        return {
            "success": True,
            "case_id": str(case["id"]),
            "case_number": str(case["case_number"]),
            "status": str(case["status"]),
        }

    @function_tool
    async def lookup_case(
        self,
        context: RunContext,
        case_number: str | None = None,
        phone: str | None = None,
    ) -> dict[str, str | bool]:
        """Look up the newest matching case by a case number or phone number.

        Args:
            case_number: Human-readable case number, such as EG-1001.
            phone: Resident's phone number when a case number is unavailable.
        """
        if not case_number and not phone:
            return {"success": False, "message": "A case number or phone number is required."}

        try:
            cases = await self.case_api.lookup_case(case_number, phone)
        except CaseApiError as error:
            return {"success": False, "message": str(error)}

        if not cases:
            return {"success": False, "message": "No matching case was found."}

        case = cases[0]
        return {
            "success": True,
            "case_id": str(case["id"]),
            "case_number": str(case["case_number"]),
            "status": str(case["status"]),
            "description": str(case["description"]),
        }

    @function_tool
    async def lookup_service_schedule(
        self, context: RunContext, city: str
    ) -> dict[str, str | bool]:
        """Look up demo trash and recycling pickup information for a city.

        Use this for schedule questions only after the resident has provided a city.

        Args:
            city: The resident's city, such as Folsom or Elk Grove.
        """
        try:
            schedule = await self.case_api.lookup_service_schedule(city)
        except CaseApiError as error:
            return {"success": False, "message": str(error)}

        if schedule is None or "detail" in schedule:
            return {
                "success": False,
                "message": str(schedule.get("detail", "No schedule information was found."))
                if schedule
                else "No schedule information was found.",
            }

        trash = schedule["trash"]
        recycling = schedule["recycling"]
        return {
            "success": True,
            "city": str(schedule["city"]),
            "trash": f"{trash['day']} at {trash['time']}",
            "recycling": f"{recycling['day']} at {recycling['time']}",
            "is_demo_data": bool(schedule["is_demo_data"]),
        }

    @function_tool
    async def update_case(
        self,
        context: RunContext,
        case_id: int,
        notes: str | None = None,
        status: str | None = None,
        description: str | None = None,
    ) -> dict[str, str | bool]:
        """Update an existing case after looking it up and obtaining its database ID.

        Args:
            case_id: Numeric database ID returned by lookup_case.
            notes: New case notes, if requested.
            status: New case status, if requested.
            description: Replacement description, if requested.
        """
        updates = {
            field: value
            for field, value in {
                "notes": notes,
                "status": status,
                "description": description,
            }.items()
            if value is not None
        }
        if not updates:
            return {"success": False, "message": "No case updates were provided."}

        try:
            case = await self.case_api.update_case(case_id, updates)
        except CaseApiError as error:
            return {"success": False, "message": str(error)}

        return {
            "success": True,
            "case_id": str(case["id"]),
            "case_number": str(case["case_number"]),
            "status": str(case["status"]),
        }

    @function_tool
    async def end_conversation(self, context: RunContext) -> StopResponse:
        """End the call after the resident says they do not need further help."""
        farewell = "You're all set. Thanks for calling EffiGov City Services. Have a good day."

        if self.call_id is not None:
            try:
                await self.case_api.add_transcript(self.call_id, "agent", farewell)
            except CaseApiError:
                logger.warning("Could not save the closing transcript message")

        speech = context.session.say(
            farewell,
            allow_interruptions=False,
            add_to_chat_ctx=False,
        )
        await speech

        if self.call_id is not None:
            try:
                await self.case_api.update_call(self.call_id, {"status": "completed"})
            except CaseApiError:
                logger.warning("Could not complete call %s", self.call_id)

        context.session.shutdown(drain=False)
        return StopResponse()


server = AgentServer()


@server.rtc_session(agent_name="effigov-case-agent")
async def entrypoint(ctx: JobContext) -> None:
    """Run one LiveKit room session and preserve its available call evidence."""
    ctx.log_context_fields = {"room": ctx.room.name}
    case_api = CaseApiClient()
    call_id: int | None = None
    try:
        call_id = int((await case_api.create_call())["id"])
    except CaseApiError:
        logger.warning("Could not create a call record; continuing without live dashboard updates")

    session = AgentSession(
        stt=inference.STT(model="deepgram/flux-general", language="en"),
        tts=inference.TTS(model="inworld/inworld-tts-2", voice="Ashley"),
        turn_handling=TurnHandlingOptions(turn_detection=inference.TurnDetector()),
    )
    await session.start(agent=EffiGovAgent(case_api, call_id), room=ctx.room)

    async def add_transcript(role: str, content: str) -> None:
        if call_id is None or not content:
            return
        try:
            await case_api.add_transcript(call_id, role, content)
        except CaseApiError:
            logger.warning("Could not save %s transcript message", role)

    def on_user_input(event) -> None:
        # LiveKit invokes event callbacks synchronously; queue persistence so it
        # cannot delay speech processing or block subsequent agent turns.
        if event.is_final:
            asyncio.create_task(add_transcript("resident", event.transcript))

    def on_conversation_item(event) -> None:
        # Store only committed agent messages, not transient generation fragments.
        item = event.item
        if getattr(item, "role", None) == "assistant":
            asyncio.create_task(add_transcript("agent", item.raw_text_content))

    session.on("user_input_transcribed", on_user_input)
    session.on("conversation_item_added", on_conversation_item)

    async def finish_call() -> None:
        if call_id is None:
            return
        try:
            await case_api.update_call(call_id, {"status": "completed"})
        except CaseApiError:
            logger.warning("Could not complete call %s", call_id)

    ctx.add_shutdown_callback(finish_call)
    await ctx.connect()
    greeting = "Hi, thanks for calling Sacramento County City and Trash Services. What would you like help with today?"
    await add_transcript("agent", greeting)
    session.say(greeting, add_to_chat_ctx=False)


if __name__ == "__main__":
    cli.run_app(server)
