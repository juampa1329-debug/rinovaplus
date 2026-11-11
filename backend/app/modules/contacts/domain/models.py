"""Human-declared CRM identity, separate from authoritative academic records."""

import re
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.schemas import LocalModel

SqlIdentity = Annotated[int, Field(ge=1, le=2147483647)]
DocumentType = Annotated[int, Field(ge=1, le=255)]


class InstitutionalProfile(LocalModel):
    givenNames: Annotated[str, Field(max_length=100)] = ""
    firstSurname: Annotated[str, Field(max_length=30)] = ""
    secondSurname: Annotated[str, Field(max_length=30)] = ""
    documentTypeId: DocumentType | None = None
    document: Annotated[str, Field(max_length=16)] = ""
    email: Annotated[str, Field(max_length=160)] = ""
    aspirationPeriodId: SqlIdentity | None = None

    @model_validator(mode="after")
    def coherent(self):
        self.document = self.document.strip(" ")
        self.email = self.email.strip(" ")
        if bool(self.document) != (self.documentTypeId is not None):
            raise ValueError("Document and actual document type are a pair")
        if self.email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", self.email):
            raise ValueError("Invalid declared email")
        return self

    def empty(self):
        return not any(self.model_dump().values())


class IdentityLookup(LocalModel):
    mode: Literal["identity", "name"] = "identity"
    source: Literal["all", "crm", "applicant", "student"] = "all"
    ownContactId: Annotated[str, Field(max_length=36)] | None = None
    documentTypeId: DocumentType | None = None
    document: Annotated[str, Field(max_length=16)] = ""
    email: Annotated[str, Field(max_length=160)] = ""
    phone: Annotated[str, Field(max_length=50)] = ""
    name: Annotated[str, Field(max_length=200)] = ""
    periodId: SqlIdentity | None = None
    programId: SqlIdentity | None = None
    offset: Annotated[int, Field(ge=0, le=1000000)] = 0

    @model_validator(mode="after")
    def normalize(self):
        if self.ownContactId is not None:
            self.ownContactId = str(UUID(self.ownContactId))
        self.document = self.document.strip(" ")
        self.email = self.email.strip(" ")
        self.phone = self.phone.strip(" ")
        self.name = self.name.strip()
        if self.mode == "identity" and (
            self.periodId is not None or self.programId is not None
        ):
            raise ValueError("Identity comparisons cover every period and program")
        return self

    def available(self):
        if self.mode == "name":
            return len(self.name) >= 3
        return bool(
            (self.documentTypeId is not None and self.document)
            or re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", self.email)
            or (sum(c.isdigit() for c in self.phone) >= 5)
        )

    def usable_email(self):
        return (
            self.email if re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", self.email) else ""
        )
