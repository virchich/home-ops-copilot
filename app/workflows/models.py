"""Models for LangGraph workflows.

This module contains Pydantic models used by the workflow system:
- HouseProfile: Input describing the house and its systems
- Season: Time of year for maintenance planning
- ClimateZone: Geographic climate classification

These models are separate from RAG models (app/rag/models.py) because
they represent workflow inputs/outputs, not RAG pipeline data.
"""

import contextlib
import json
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

from app.rag.schema import DeviceType

# Default location for house profile
DEFAULT_HOUSE_PROFILE_PATH = Path("data/house_profile.json")

# =============================================================================
# ENUMS
# =============================================================================


class Season(str, Enum):
    """Seasons for maintenance planning.

    Each season has different maintenance priorities:
    - SPRING: Post-winter inspection, AC prep, outdoor systems
    - SUMMER: AC maintenance, pest prevention, exterior work
    - FALL: Winterization prep, heating system checks, gutters
    - WINTER: Indoor focus, heating efficiency, freeze prevention
    """

    SPRING = "spring"
    SUMMER = "summer"
    FALL = "fall"
    WINTER = "winter"


class ClimateZone(str, Enum):
    """IECC Climate Zones (simplified).

    Based on International Energy Conservation Code climate zones.
    These affect what maintenance tasks are relevant:
    - COLD: Zones 5-7 (e.g., Canada, northern US) - freeze protection critical
    - MIXED: Zones 3-4 (e.g., mid-Atlantic, midwest) - both heating and cooling
    - HOT_HUMID: Zones 1-2A (e.g., Florida, Gulf Coast) - moisture/mold focus
    - HOT_DRY: Zones 2B-3B (e.g., Arizona, Nevada) - dust/UV/cooling focus

    Reference: https://basc.pnnl.gov/images/iecc-climate-zone-map
    """

    COLD = "cold"
    MIXED = "mixed"
    HOT_HUMID = "hot_humid"
    HOT_DRY = "hot_dry"


class HouseType(str, Enum):
    """Types of residential buildings.

    Affects maintenance scope and complexity:
    - SINGLE_FAMILY: Detached house, full responsibility for all systems
    - TOWNHOUSE: Shared walls, may share some systems
    - CONDO: Unit in larger building, limited system responsibility
    - DUPLEX: Two-unit building
    """

    SINGLE_FAMILY = "single_family"
    TOWNHOUSE = "townhouse"
    CONDO = "condo"
    DUPLEX = "duplex"


# =============================================================================
# SYSTEM MODELS
# =============================================================================


class InstalledSystem(BaseModel):
    """Details about an installed system/device.

    This model captures optional details about a device. The device_type
    is the key, so this model holds supplementary information.

    Example:
        {
            "model": "OM9GFRC",
            "manufacturer": "Carrier",
            "fuel_type": "gas",
            "install_year": 2020,
            "notes": "Annual service contract with ABC HVAC"
        }
    """

    model: str | None = Field(
        default=None,
        description="Model number (e.g., 'OM9GFRC')",
    )
    manufacturer: str | None = Field(
        default=None,
        description="Brand/manufacturer (e.g., 'Carrier')",
    )
    fuel_type: str | None = Field(
        default=None,
        description="Fuel/power source (e.g., 'gas', 'electric', 'propane')",
    )
    install_year: int | None = Field(
        default=None,
        description="Year the system was installed",
    )
    notes: str | None = Field(
        default=None,
        description="Any additional notes (service contracts, quirks, etc.)",
    )


# =============================================================================
# HOUSE PROFILE
# =============================================================================


class HouseProfile(BaseModel):
    """Profile of a house for maintenance planning.

    This model captures everything the maintenance planner needs to know
    about a house to generate relevant, personalized checklists.

    The `systems` field is a dictionary mapping DeviceType to optional details.
    If a device type is present as a key, the house has that system.
    The value can be None (just marking presence) or InstalledSystem (with details).

    Example:
        {
            "name": "123 Main Street",
            "year_built": 1995,
            "climate_zone": "cold",
            "house_type": "single_family",
            "systems": {
                "furnace": {"manufacturer": "Carrier", "fuel_type": "gas"},
                "hrv": {"manufacturer": "Lifebreath"},
                "water_heater": {"fuel_type": "electric"},
                "thermostat": null  // Has one, no details provided
            }
        }
    """

    # Basic info
    name: str = Field(
        description="Identifier for this house (address, nickname, etc.)",
    )
    year_built: int | None = Field(
        default=None,
        description="Year the house was built (affects maintenance needs)",
    )
    square_footage: int | None = Field(
        default=None,
        description="Approximate square footage of living space",
    )

    # Location and climate
    climate_zone: ClimateZone = Field(
        description="Climate zone affecting maintenance priorities",
    )
    house_type: HouseType = Field(
        default=HouseType.SINGLE_FAMILY,
        description="Type of residential building",
    )

    # Installed systems
    # Keys are DeviceType values (as strings), values are optional details
    systems: dict[str, InstalledSystem | None] = Field(
        default_factory=dict,
        description="Mapping of device_type -> optional details. "
        "Presence of a key indicates the system is installed.",
    )

    def has_system(self, device_type: DeviceType) -> bool:
        """Check if a system is installed.

        Args:
            device_type: The type of device to check for.

        Returns:
            True if the system is installed, False otherwise.
        """
        return device_type.value in self.systems

    def get_installed_device_types(self) -> list[DeviceType]:
        """Get list of all installed device types.

        Returns:
            List of DeviceType enums for installed systems.
        """
        result = []
        for key in self.systems:
            with contextlib.suppress(ValueError):
                result.append(DeviceType(key))
        return result


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def load_house_profile(path: Path | None = None) -> HouseProfile:
    """Load a house profile from a JSON file.

    Args:
        path: Path to the JSON file. If None, uses the default location
              (data/house_profile.json).

    Returns:
        Parsed HouseProfile instance.

    Raises:
        FileNotFoundError: If the profile file doesn't exist.
        ValidationError: If the JSON doesn't match the schema.

    Example:
        >>> profile = load_house_profile()
        >>> profile.name
        'Main Residence'
        >>> profile.has_system(DeviceType.FURNACE)
        True
    """
    profile_path = path or DEFAULT_HOUSE_PROFILE_PATH

    with open(profile_path) as f:
        data = json.load(f)

    return HouseProfile(**data)
