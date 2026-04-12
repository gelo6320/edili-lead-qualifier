from __future__ import annotations

import json
from dataclasses import replace

from lead_qualifier.domain.bot_config import BotConfig
from lead_qualifier.domain.lead import LeadImageAsset, LeadRuntimeMetadata, LeadState, StoredMessage


def build_empty_lead_state(config: BotConfig, *, contact_name: str = "") -> LeadState:
    return LeadState(
        field_values={key: "" for key in config.field_keys},
        qualification_status=config.default_status,
        missing_fields=config.required_field_keys,
        summary="",
        metadata=LeadRuntimeMetadata(
            latest_contact_name=contact_name.strip(),
        ),
    )


def with_contact_name(lead_state: LeadState, contact_name: str) -> LeadState:
    cleaned_name = contact_name.strip()
    if not cleaned_name or cleaned_name == lead_state.metadata.latest_contact_name:
        return lead_state
    return replace(
        lead_state,
        metadata=replace(lead_state.metadata, latest_contact_name=cleaned_name),
    )


def with_initial_template(
    lead_state: LeadState,
    *,
    template_id: str,
    template_name: str,
    language_code: str,
    template_body: str,
    rendered_text: str,
    body_parameters: list[str],
) -> LeadState:
    return replace(
        lead_state,
        metadata=replace(
            lead_state.metadata,
            initial_template_id=template_id.strip(),
            initial_template_name=template_name.strip(),
            initial_template_language=language_code.strip(),
            initial_template_body=template_body.strip(),
            initial_template_rendered_text=rendered_text.strip(),
            initial_template_parameters=[value.strip() for value in body_parameters if value.strip()],
        ),
    )
def infer_initial_template_from_history(lead_state: LeadState, history: list[StoredMessage]) -> LeadState:
    if lead_state.metadata.has_initial_template:
        return lead_state

    for message in history:
        if message.role != "assistant":
            continue
        try:
            payload = json.loads(message.api_content)
        except json.JSONDecodeError:
            continue
        if payload.get("kind") != "outbound_template":
            continue
        return with_initial_template(
            lead_state,
            template_id=str(payload.get("template_id", "")).strip(),
            template_name=str(payload.get("template_name", "")).strip(),
            language_code=str(payload.get("language_code", "")).strip(),
            template_body=str(payload.get("template_body", "")).strip(),
            rendered_text=str(payload.get("rendered_text", "")).strip(),
            body_parameters=[
                str(value).strip()
                for value in payload.get("body_parameters", [])
                if str(value).strip()
            ],
        )

    return lead_state


def with_image_asset(lead_state: LeadState, image_asset: LeadImageAsset) -> LeadState:
    if not image_asset.media_id and not image_asset.public_url and not image_asset.message_id:
        return lead_state

    existing_images = [
        image
        for image in lead_state.metadata.images
        if not (
            (image_asset.message_id and image.message_id == image_asset.message_id)
            or (image_asset.media_id and image.media_id == image_asset.media_id)
            or (image_asset.public_url and image.public_url == image_asset.public_url)
        )
    ]
    existing_images.append(image_asset)
    return replace(
        lead_state,
        metadata=replace(
            lead_state.metadata,
            images=existing_images,
        ),
    )
