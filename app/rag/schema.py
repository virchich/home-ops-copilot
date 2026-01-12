"""Document metadata schema for RAG ingestion.

This module defines the structure for document metadata used during ingestion.
Metadata enables:
1. Filtering: "Only search furnace docs" when question mentions furnace
2. Better citations: "From: Furnace Manual, Page 12" vs "document_3.pdf"
3. Context for LLM: Helps the model understand what it's reading
"""

from enum import Enum

from pydantic import BaseModel, Field


class DeviceType(str, Enum):
    """Categories of home equipment."""

    FURNACE = "furnace"
    THERMOSTAT = "thermostat"
    ENERGY_METER = "energy_meter"
    WATER_SOFTENER = "water_softener"
    WATER_HEATER = "water_heater"
    HUMIDIFIER = "humidifier"
    HRV = "hrv"  # Heat Recovery Ventilator
    AIR_CONDITIONER = "air_conditioner"
    APPLIANCE = "appliance"
    OTHER = "other"


class DocType(str, Enum):
    """Types of documents."""

    MANUAL = "manual"
    RECEIPT = "receipt"
    WARRANTY = "warranty"
    NOTES = "notes"
    SPEC_SHEET = "spec_sheet"


class Location(str, Enum):
    """Locations in the home."""

    BASEMENT = "basement"
    MAIN_FLOOR = "main_floor"
    SECOND_FLOOR = "second_floor"
    THIRD_FLOOR = "third_floor"
    ATTIC = "attic"
    GARAGE = "garage"
    OUTSIDE = "outside"
    UTILITY_ROOM = "utility_room"
    KITCHEN = "kitchen"
    BATHROOM = "bathroom"


class DocumentMetadata(BaseModel):
    """
    Metadata for a single document in the RAG system.

    This metadata is attached to each document (and its chunks) during ingestion.
    It enables filtering during retrieval and provides context for citations.
    """

    file_name: str = Field(description="Original file name in data/raw_docs/")
    device_type: DeviceType = Field(description="Category of equipment")
    device_name: str = Field(description="Specific model number or name")
    manufacturer: str = Field(description="Brand/manufacturer name")
    doc_type: DocType = Field(default=DocType.MANUAL, description="Type of document")
    location: Location = Field(description="Where in the home this device is located")
    tags: list[str] = Field(default_factory=list, description="Searchable tags for filtering")
    description: str | None = Field(default=None, description="Optional human-readable description")


class MetadataFile(BaseModel):
    """
    Root schema for the metadata.json file.

    Contains a list of all document metadata entries.
    """

    documents: list[DocumentMetadata]
