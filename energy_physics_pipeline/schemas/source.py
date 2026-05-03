"""SourceManifest — every external lookup logs one of these."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict


class RetrievalMethod(str, Enum):
    api = "api"
    git = "git"
    hf = "hf"
    manual = "manual"
    fixture = "fixture"
    claude_deep_research = "claude_deep_research"


class AllowedUse(str, Enum):
    research = "research"
    commercial = "commercial"
    noncommercial = "noncommercial"
    unknown = "unknown"


class SourceManifest(BaseModel):
    source_id: str
    uri: str
    retrieval_method: RetrievalMethod
    retrieved_at: datetime
    license_spdx_or_text: str
    allowed_use: AllowedUse
    geography_restrictions: Optional[str] = None
    checksum: str
    local_slice_size_mb: float = 0.0
    bulk_data_stored: bool = False
    citation: str
    rights_notes: str = ""
    # Per CPU hardening §H8 — entries that cannot be verified from any
    # primary URL are demoted to `non_authority=True`. License-promotion
    # consumers must refuse to use these entries as authority.
    non_authority: bool = False

    model_config = ConfigDict(extra="forbid")
