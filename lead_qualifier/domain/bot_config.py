from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


DEFAULT_QUALIFICATION_STATUSES = [
    "new",
    "in_progress",
    "qualified",
    "follow_up",
]


class BotFieldConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    key: str = Field(..., description="Chiave univoca del campo.")
    label: str = Field(..., description="Etichetta leggibile del campo.")
    description: str = Field(..., description="Descrizione operativa usata nel prompt.")
    required: bool = Field(default=True)
    options: list[str] = Field(default_factory=list, description="Valori ammessi opzionali.")

    @field_validator("key", "label", "description", mode="before")
    @classmethod
    def _strip_required_strings(cls, value: object) -> str:
        return str(value or "").strip()

    @field_validator("options", mode="before")
    @classmethod
    def _normalize_options(cls, value: object) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("options deve essere una lista.")
        return [str(item).strip() for item in value if str(item).strip()]

    @model_validator(mode="after")
    def _validate_options(self) -> "BotFieldConfig":
        if self.options:
            self.options = list(dict.fromkeys(self.options))
        return self


class BotConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Identificatore univoco del bot.")
    name: str = Field(..., description="Nome leggibile del bot.")
    company_name: str = Field(..., description="Nome azienda/brand del tenant.")
    company_description: str = Field(
        default="",
        description="Descrizione sintetica dell'azienda e del suo posizionamento.",
    )
    service_area: str = Field(
        default="",
        description="Zona operativa dell'azienda.",
    )
    company_services: list[str] = Field(
        default_factory=list,
        description="Servizi principali offerti dall'azienda.",
    )
    agent_name: str = Field(default="Giulia", description="Nome dell'agente.")
    phone_number_id: str = Field(default="", description="Phone Number ID Meta associato al bot.")
    default_template_name: str = Field(default="", description="Template outbound predefinito.")
    template_language: str = Field(default="it", description="Lingua template Meta.")
    booking_url: str = Field(default="", description="URL opzionale per prenotare una chiamata.")
    lead_manager_page_id: str = Field(
        default="",
        description="Page ID usato dal lead manager per instradare il lead qualificato.",
    )
    qualification_statuses: list[str] = Field(
        default_factory=lambda: DEFAULT_QUALIFICATION_STATUSES.copy(),
        description="Stati disponibili per la qualifica.",
    )
    fields: list[BotFieldConfig] = Field(
        default_factory=list,
        description="Campi da raccogliere dal lead.",
    )

    @field_validator(
        "id",
        "name",
        "company_name",
        "company_description",
        "service_area",
        "agent_name",
        "phone_number_id",
        "default_template_name",
        "template_language",
        "booking_url",
        "lead_manager_page_id",
        mode="before",
    )
    @classmethod
    def _strip_strings(cls, value: object) -> str:
        return str(value or "").strip()

    @field_validator("company_services", mode="before")
    @classmethod
    def _normalize_company_services(cls, value: object) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("company_services deve essere una lista.")
        return [str(item).strip() for item in value if str(item).strip()]

    @field_validator("qualification_statuses", mode="before")
    @classmethod
    def _normalize_statuses(cls, value: object) -> list[str]:
        if value is None:
            return DEFAULT_QUALIFICATION_STATUSES.copy()
        if not isinstance(value, list):
            raise ValueError("qualification_statuses deve essere una lista.")
        statuses = [str(item).strip() for item in value if str(item).strip()]
        return statuses or DEFAULT_QUALIFICATION_STATUSES.copy()

    @model_validator(mode="after")
    def _validate_config(self) -> "BotConfig":
        self.qualification_statuses = list(dict.fromkeys(self.qualification_statuses))
        self.company_services = list(dict.fromkeys(self.company_services))
        if not self.fields:
            raise ValueError("Ogni bot deve avere almeno un campo da raccogliere.")

        field_keys = [field.key for field in self.fields]
        if len(field_keys) != len(set(field_keys)):
            raise ValueError("Le chiavi dei campi devono essere univoche.")

        return self

    @property
    def required_fields(self) -> list[BotFieldConfig]:
        return [field for field in self.fields if field.required]

    @property
    def field_keys(self) -> list[str]:
        return [field.key for field in self.fields]

    @property
    def required_field_keys(self) -> list[str]:
        return [field.key for field in self.required_fields]

    @property
    def default_status(self) -> str:
        return self.qualification_statuses[0]
