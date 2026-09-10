import logging
import textwrap

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    RunContext,
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
    def __init__(self) -> None:
        super().__init__(
            llm=inference.LLM(model="google/gemma-4-31b-it"),
            instructions=textwrap.dedent(
                """\
                You are a city service assistant helping residents report service issues.
                For this demo, handle only missed trash pickup requests.

                When a resident wants to report an issue, understand the issue and collect
                their name, phone number, and a short useful description. Do not ask again
                for information the resident has already provided. Use issue_type
                "missed_pickup" for this workflow.

                Once all required information is available, call create_case exactly once.
                Never claim a case was created unless the tool reports success. On success,
                clearly tell the resident the returned case number. If the tool fails,
                apologize briefly and explain that the case could not be created.

                If a resident asks about an existing case, use lookup_case. If they request
                an update and you know the database case ID, use update_case.

                Keep every response short, natural for speech, and ask one question at a time.
                Use plain text only. Do not mention tool names, JSON, or internal systems.
                """
            ),
        )
        self.case_api = CaseApiClient()

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


server = AgentServer()


@server.rtc_session(agent_name="effigov-case-agent")
async def entrypoint(ctx: JobContext) -> None:
    ctx.log_context_fields = {"room": ctx.room.name}
    session = AgentSession(
        stt=inference.STT(model="deepgram/flux-general", language="en"),
        tts=inference.TTS(model="inworld/inworld-tts-2", voice="Ashley"),
        turn_handling=TurnHandlingOptions(turn_detection=inference.TurnDetector()),
    )
    await session.start(agent=EffiGovAgent(), room=ctx.room)
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(server)
