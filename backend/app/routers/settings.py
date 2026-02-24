from fastapi import APIRouter, Path, HTTPException

from app.config import settings
from app.models.schemas import (
    SystemSetting,
    SettingUpdate,
    SystemSettingsResponse,
)
from app.mock.generators import generate_system_settings, generate_api_statuses

router = APIRouter(prefix="/api/settings", tags=["settings"])

# In-memory store for mock data mutations
_mock_settings: list[dict] | None = None


def _get_mock_settings() -> list[dict]:
    global _mock_settings
    if _mock_settings is None:
        _mock_settings = generate_system_settings()
    return _mock_settings


@router.get("", response_model=SystemSettingsResponse)
async def get_settings():
    """All system settings plus API connectivity statuses."""
    if settings.use_mock_data:
        return SystemSettingsResponse(
            settings=_get_mock_settings(),
            api_statuses=generate_api_statuses(),
            trading_mode=settings.trading_mode,
        )

    from app.services.supabase_client import get_supabase

    client = get_supabase()
    settings_result = client.table("system_settings").select("*").execute()
    api_statuses = generate_api_statuses()  # Always mock connectivity checks for now
    return SystemSettingsResponse(
        settings=settings_result.data,
        api_statuses=api_statuses,
        trading_mode=settings.trading_mode,
    )


@router.put("/{key}", response_model=SystemSetting)
async def update_setting(
    key: str = Path(..., description="Setting key to update"),
    update: SettingUpdate = ...,
):
    """Update a system setting value. Respects editable and requires_approval flags."""
    if settings.use_mock_data:
        all_settings = _get_mock_settings()
        setting = next((s for s in all_settings if s["key"] == key), None)
        if setting is None:
            raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
        if not setting["editable"]:
            raise HTTPException(
                status_code=403,
                detail=f"Setting '{key}' is read-only. Changes to risk constants require human approval outside the dashboard.",
            )
        setting["value"] = update.value
        return setting

    from app.services.supabase_client import get_supabase

    client = get_supabase()
    # Check if setting exists and is editable
    existing = (
        client.table("system_settings")
        .select("*")
        .eq("key", key)
        .single()
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    if not existing.data["editable"]:
        raise HTTPException(
            status_code=403,
            detail=f"Setting '{key}' is read-only. Changes to risk constants require human approval outside the dashboard.",
        )
    result = (
        client.table("system_settings")
        .update({"value": update.value})
        .eq("key", key)
        .execute()
    )
    return result.data[0]
