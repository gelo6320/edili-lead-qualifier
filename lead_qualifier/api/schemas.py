from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

class TemplateSendRequest(BaseModel):
    bot_id: str = Field(..., description="Identificatore del bot da usare.")
    to: str = Field(..., description="Numero WhatsApp del lead in formato internazionale, senza +.")
    template_name: str = Field(..., description="Nome esatto del template approvato in Meta.")
    language_code: str | None = Field(
        default=None,
        description="Codice lingua del template, ad esempio it o it_IT.",
    )
    body_parameters: list[str] = Field(
        default_factory=list,
        description="Parametri testo per il body del template, nell'ordine definito in Meta.",
    )

    @field_validator("bot_id", "to", "template_name", mode="before")
    @classmethod
    def _strip_required_fields(cls, value: object) -> str:
        return str(value or "").strip()

    @field_validator("language_code", mode="before")
    @classmethod
    def _strip_optional_language(cls, value: object) -> str | None:
        stripped = str(value or "").strip()
        return stripped or None

    @field_validator("body_parameters", mode="before")
    @classmethod
    def _normalize_body_parameters(cls, value: object) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("body_parameters deve essere una lista.")
        return [str(item).strip() for item in value if str(item).strip()]


class TemplateTestRequest(BaseModel):
    to: str = Field(..., description="Numero WhatsApp del lead in formato internazionale, senza +.")
    template_name: str | None = Field(
        default=None,
        description="Nome template opzionale. Se omesso usa il template di default del bot.",
    )
    language_code: str | None = Field(
        default=None,
        description="Codice lingua opzionale. Se omesso usa la lingua di default del bot.",
    )
    body_parameters: list[str] = Field(
        default_factory=list,
        description="Parametri testo per il body del template, nell'ordine definito in Meta.",
    )

    @field_validator("to", mode="before")
    @classmethod
    def _strip_required_test_fields(cls, value: object) -> str:
        return str(value or "").strip()

    @field_validator("template_name", "language_code", mode="before")
    @classmethod
    def _strip_optional_test_fields(cls, value: object) -> str | None:
        stripped = str(value or "").strip()
        return stripped or None

    @field_validator("body_parameters", mode="before")
    @classmethod
    def _normalize_test_body_parameters(cls, value: object) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("body_parameters deve essere una lista.")
        return [str(item).strip() for item in value if str(item).strip()]


class SiteCrawlRequest(BaseModel):
    site_url: str = Field(..., description="URL del sito da analizzare con Cloudflare /crawl.")

    @field_validator("site_url", mode="before")
    @classmethod
    def _strip_site_url(cls, value: object) -> str:
        return str(value or "").strip()


class BridgeQualificationRequest(BaseModel):
    page_id: str = Field(..., description="Page ID del lead manager che ha generato il lead.")
    bot_id: str = Field(..., description="Configurazione qualificatore attesa per la pagina.")
    phone: str = Field(..., description="Telefono del lead.")
    full_name: str | None = Field(default=None)
    email: str | None = Field(default=None)
    leadgen_id: str | None = Field(default=None)
    source_label: str | None = Field(default=None)
    form_responses: list[str] = Field(default_factory=list)
    custom_fields: dict[str, str] = Field(default_factory=dict)

    @field_validator("page_id", "bot_id", "phone", "full_name", "email", "leadgen_id", "source_label", mode="before")
    @classmethod
    def _strip_bridge_strings(cls, value: object) -> str | None:
        stripped = str(value or "").strip()
        return stripped or None
