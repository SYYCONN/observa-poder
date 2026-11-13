from datetime import date, datetime
import re

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator

BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
STATES = set(
    "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
)


class Deputy(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    _page_number: int = PrivateAttr(default=1)

    id: int = Field(gt=0)
    uri: str = Field(max_length=1000)
    nome: str = Field(min_length=1, max_length=250)
    siglaPartido: str | None = Field(default=None, max_length=40)
    uriPartido: str | None = Field(default=None, max_length=1000)
    siglaUf: str
    idLegislatura: int = Field(gt=0)
    urlFoto: str | None = Field(default=None, max_length=1000)

    @field_validator("nome")
    @classmethod
    def non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("blank name")
        return value

    @field_validator("siglaUf")
    @classmethod
    def valid_state(cls, value: str) -> str:
        if value not in STATES:
            raise ValueError("invalid state")
        return value


class Link(BaseModel):
    model_config = ConfigDict(strict=True)
    rel: str
    href: str


class DeputiesPage(BaseModel):
    model_config = ConfigDict(strict=True)
    dados: list[Deputy]
    links: list[Link]


class DeputyProfile(BaseModel):
    """Campos públicos mínimos usados no perfil; CPF e contatos são descartados."""

    model_config = ConfigDict(extra="ignore", strict=True)

    id: int = Field(gt=0)
    nomeCivil: str = Field(min_length=1, max_length=250)
    dataNascimento: date | None = None


class DeputyProfileResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    dados: DeputyProfile


class DeputyStatus(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    id: int = Field(gt=0)
    idLegislatura: int = Field(gt=0)
    dataHora: datetime
    situacao: str | None = Field(default=None, max_length=100)
    descricaoStatus: str | None = Field(default=None, max_length=1000)


class DeputyHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    dados: list[DeputyStatus]


class BulkDeputyProfile(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    uri: str = Field(max_length=1000)
    nomeCivil: str | None = Field(default=None, max_length=250)
    dataNascimento: date | None = None

    @field_validator("nomeCivil", mode="before")
    @classmethod
    def blank_name_as_none(cls, value):
        return None if value == "" else value

    @field_validator("dataNascimento", mode="before")
    @classmethod
    def parse_optional_birth_date(cls, value):
        if value == "" or value is None:
            return None
        return date.fromisoformat(value) if isinstance(value, str) else value

    @property
    def id(self) -> int:
        match = re.fullmatch(rf"{re.escape(BASE_URL)}/deputados/([1-9][0-9]*)", self.uri)
        if match is None:
            raise ValueError("invalid deputy URI")
        return int(match.group(1))


class BulkDeputyProfilesResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    dados: list[BulkDeputyProfile]


class BulkDeputyStatus(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    ide_cadastro: str = Field(pattern=r"^[1-9][0-9]*$")
    datIni: datetime
    num_legislatura: int = Field(gt=0)
    situacao: str | None = Field(default=None, max_length=100)
    descricao: str | None = Field(default=None, max_length=2000)

    def normalized(self) -> DeputyStatus:
        return DeputyStatus(
            id=int(self.ide_cadastro),
            idLegislatura=self.num_legislatura,
            dataHora=self.datIni,
            situacao=self.situacao,
            descricaoStatus=self.descricao,
        )


class BulkDeputyHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    dados: list[BulkDeputyStatus]
