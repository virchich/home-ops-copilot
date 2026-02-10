"""Shared helper functions for LangGraph workflows.

These utilities are used across multiple workflows (maintenance planner,
troubleshooter, parts helper) to format retrieved chunks and device details
for LLM prompts.
"""

from app.workflows.models import HouseProfile, RetrievedChunk


def format_chunks_as_context(chunks: list[RetrievedChunk]) -> str:
    """Format retrieved chunks as numbered context for LLM prompts.

    Each chunk is formatted with its source and device type metadata,
    separated by horizontal rules for clarity.

    Args:
        chunks: Retrieved document chunks from the RAG index.

    Returns:
        Formatted string with numbered sources, or a fallback message
        if no chunks are available.

    Example:
        >>> chunks = [RetrievedChunk(text="Replace filter every 3 months",
        ...     source="Furnace-Manual.pdf", device_type="furnace", score=0.9)]
        >>> print(format_chunks_as_context(chunks))
        [Source 1: Furnace-Manual.pdf (furnace)]
        Replace filter every 3 months
    """
    if not chunks:
        return "No documentation available."
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(
            f"[Source {i}: {chunk.source} ({chunk.device_type or 'general'})]\n{chunk.text}"
        )
    return "\n\n---\n\n".join(parts)


def format_device_details(house_profile: HouseProfile | None, device_type: str | None) -> str:
    """Extract device details from the house profile for LLM context.

    Formats manufacturer, model, fuel type, and install year into a
    human-readable string for inclusion in LLM prompts.

    Args:
        house_profile: The house profile containing installed systems.
        device_type: The device type key to look up in the profile.

    Returns:
        Formatted string with device details, or empty string if
        the device or profile is not available.

    Example:
        >>> profile = HouseProfile(name="Test", climate_zone="cold",
        ...     systems={"furnace": InstalledSystem(manufacturer="Carrier",
        ...         model="OM9GFRC")})
        >>> print(format_device_details(profile, "furnace"))
        Manufacturer: Carrier
        Model: OM9GFRC
    """
    if not house_profile or not device_type:
        return ""
    system_details = house_profile.systems.get(device_type)
    if not system_details:
        return ""
    parts = []
    if system_details.manufacturer:
        parts.append(f"Manufacturer: {system_details.manufacturer}")
    if system_details.model:
        parts.append(f"Model: {system_details.model}")
    if system_details.fuel_type:
        parts.append(f"Fuel: {system_details.fuel_type}")
    if system_details.install_year:
        parts.append(f"Installed: {system_details.install_year}")
    return "\n".join(parts)
