import chainlit as cl
from chainlit.input_widget import Select

from api_client.frontend_config import get_api_base_url
from api_client.triage_api_client import fetch_agent_trace, submit_triage_claim
from constants.claim_action_names import (
    CLAIM_ID_PAYLOAD_KEY,
    SHOW_TRACE_ACTION_NAME,
    VIEW_CLAIM_ACTION_NAME,
)
from constants.policy_type_options import (
    DEFAULT_POLICY_TYPE_OPTION,
    POLICY_TYPE_SETTING_WIDGET_ID,
    PolicyTypeOption,
)
from constants.triage_api_status_codes import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_OK,
    HTTP_STATUS_UNPROCESSABLE_ENTITY,
)
from utils.claim_session_history import (
    get_active_trace_element,
    get_stored_claims,
    set_active_trace_element,
    store_claim,
)
from utils.message_streaming import send_streamed_message
from utils.triage_claim_payload import classify_attachments
from utils.triage_report_formatting import (
    format_agent_trace_markdown,
    format_claim_summary_label,
    format_safety_error_markdown,
    format_triage_response_markdown,
    format_unexpected_error_markdown,
    format_validation_error_markdown,
)

IMAGE_MIME_PREFIX = "image/"
PDF_MIME_TYPE = "application/pdf"

WELCOME_MESSAGE = (
    "Attach a damage photo and/or type a description of the incident, then send. "
    "I'll run it through the claim triage agent and show you the structured report. "
    'Use the "Show agent trace" button on any report to open its reasoning trace in '
    'a side panel, and revisit earlier claims from the "Claims this session" list.'
)
THINKING_STEP_NAME = "Thinking"
THINKING_STEP_RUNNING_MESSAGE = "Submitting to the triage agent..."
SHOW_TRACE_BUTTON_LABEL = "Show agent trace"
TRACE_PANEL_ELEMENT_NAME = "Agent trace"
TRACE_OPENED_MESSAGE = f"_Opened the {TRACE_PANEL_ELEMENT_NAME} panel._"
TRACE_UNAVAILABLE_MESSAGE = "_The agent trace for this claim could not be retrieved._"
CLAIM_HISTORY_MESSAGE_TITLE = "**Claims this session** — click one to view it again."
UNKNOWN_CLAIM_MESSAGE = "_That claim is no longer available in this session._"


@cl.on_chat_start
async def start_chat() -> None:
    await cl.ChatSettings(
        [
            Select(
                id=POLICY_TYPE_SETTING_WIDGET_ID,
                label="Policy type",
                values=[option.value for option in PolicyTypeOption],
                initial_index=list(PolicyTypeOption).index(DEFAULT_POLICY_TYPE_OPTION),
            ),
        ]
    ).send()
    cl.user_session.set(POLICY_TYPE_SETTING_WIDGET_ID, DEFAULT_POLICY_TYPE_OPTION.value)
    await send_streamed_message(WELCOME_MESSAGE)


@cl.on_settings_update
async def update_settings(settings: dict) -> None:
    cl.user_session.set(POLICY_TYPE_SETTING_WIDGET_ID, settings[POLICY_TYPE_SETTING_WIDGET_ID])


@cl.on_message
async def handle_message(message: cl.Message) -> None:
    description = (message.content or "").strip()
    attachments = [(element.mime, element.path) for element in message.elements]
    classified = classify_attachments(
        attachments, image_mime_prefix=IMAGE_MIME_PREFIX, pdf_mime_type=PDF_MIME_TYPE
    )
    policy_type = cl.user_session.get(
        POLICY_TYPE_SETTING_WIDGET_ID, DEFAULT_POLICY_TYPE_OPTION.value
    )

    base_url = get_api_base_url()
    async with cl.Step(name=THINKING_STEP_NAME, type="run") as thinking_step:
        thinking_step.output = THINKING_STEP_RUNNING_MESSAGE
        await thinking_step.update()
        response = await submit_triage_claim(
            base_url,
            description=description,
            policy_type=policy_type,
            image_paths=classified.image_paths,
            document_path=classified.document_path,
        )

        trace_steps = None
        if response.status_code == HTTP_STATUS_OK:
            claim_id = response.json()["claim_id"]
            trace_response = await fetch_agent_trace(base_url, claim_id)
            if trace_response.status_code == HTTP_STATUS_OK:
                trace_steps = trace_response.json()["steps"]
        thinking_step.output = f"Received HTTP {response.status_code} from the triage API."

    if response.status_code == HTTP_STATUS_BAD_REQUEST:
        await send_streamed_message(format_validation_error_markdown(response.json()))
        return
    if response.status_code == HTTP_STATUS_UNPROCESSABLE_ENTITY:
        await send_streamed_message(format_safety_error_markdown(response.json()))
        return
    if response.status_code != HTTP_STATUS_OK:
        error_markdown = format_unexpected_error_markdown(response.status_code, response.text)
        await send_streamed_message(error_markdown)
        return

    payload = response.json()
    stored_claim = store_claim(payload["claim_id"], payload, trace_steps)

    await _send_claim_report_message(
        payload["claim_id"], payload, stored_claim.sequence_number, stored_claim.claim_year
    )
    await _send_claim_history_message()


@cl.action_callback(SHOW_TRACE_ACTION_NAME)
async def show_trace(action: cl.Action) -> None:
    claim_id = action.payload[CLAIM_ID_PAYLOAD_KEY]
    stored_claim = get_stored_claims().get(claim_id)
    if stored_claim is None:
        await cl.Message(content=UNKNOWN_CLAIM_MESSAGE).send()
        return

    if stored_claim.trace_steps is not None:
        trace_markdown = format_agent_trace_markdown(stored_claim.trace_steps)
    else:
        trace_markdown = TRACE_UNAVAILABLE_MESSAGE

    previous_trace_element = get_active_trace_element()
    if previous_trace_element is not None:
        await previous_trace_element.remove()

    trace_element = cl.Text(name=TRACE_PANEL_ELEMENT_NAME, content=trace_markdown, display="side")
    set_active_trace_element(trace_element)
    await cl.Message(content=TRACE_OPENED_MESSAGE, elements=[trace_element]).send()


@cl.action_callback(VIEW_CLAIM_ACTION_NAME)
async def view_claim(action: cl.Action) -> None:
    claim_id = action.payload[CLAIM_ID_PAYLOAD_KEY]
    stored_claim = get_stored_claims().get(claim_id)
    if stored_claim is None:
        await cl.Message(content=UNKNOWN_CLAIM_MESSAGE).send()
        return
    await _send_claim_report_message(
        claim_id, stored_claim.response, stored_claim.sequence_number, stored_claim.claim_year
    )


async def _send_claim_report_message(
    claim_id: str, response: dict, sequence_number: int, claim_year: int
) -> None:
    await send_streamed_message(
        format_triage_response_markdown(response, sequence_number, claim_year),
        actions=[_build_show_trace_action(claim_id)],
    )


def _build_show_trace_action(claim_id: str) -> cl.Action:
    return cl.Action(
        name=SHOW_TRACE_ACTION_NAME,
        payload={CLAIM_ID_PAYLOAD_KEY: claim_id},
        label=SHOW_TRACE_BUTTON_LABEL,
    )


async def _send_claim_history_message() -> None:
    claims = get_stored_claims()
    actions = [
        cl.Action(
            name=VIEW_CLAIM_ACTION_NAME,
            payload={CLAIM_ID_PAYLOAD_KEY: claim_id},
            label=format_claim_summary_label(
                stored_claim.response, stored_claim.sequence_number, stored_claim.claim_year
            ),
        )
        for claim_id, stored_claim in claims.items()
    ]
    await cl.Message(content=CLAIM_HISTORY_MESSAGE_TITLE, actions=actions).send()
