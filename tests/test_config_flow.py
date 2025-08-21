"""Test the ld2410 config flow."""

from unittest.mock import patch

from custom_components.ld2410.api.ld2410 import LD2410AccountConnectionError, LD2410AuthenticationError

from custom_components.ld2410.const import (
    CONF_RETRY_COUNT,
)
from homeassistant.config_entries import SOURCE_BLUETOOTH, SOURCE_IGNORE, SOURCE_USER
from homeassistant.const import (
    CONF_ADDRESS,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SENSOR_TYPE,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from . import (
    USER_INPUT,
    LD2410b_SERVICE_INFO,
    LD2410b_2_SERVICE_INFO,
    LD2410b_NOT_CONNECTABLE,
    NOT_LD2410_INFO,
    init_integration,
    patch_async_setup_entry
)

try:
    from tests.common import MockConfigEntry
except ImportError:
    from .mocks import MockConfigEntry

DOMAIN = "ld2410"

async def test_bluetooth_discovery_requires_password(hass: HomeAssistant) -> None:
    """Test discovery via bluetooth with a valid device that needs a password."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_BLUETOOTH},
        data=LD2410b_SERVICE_INFO,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "password"

    with patch_async_setup_entry() as mock_setup_entry:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_PASSWORD: "abc123"},
        )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "HLK-LD2410 96D8"
    assert result["data"] == {
        CONF_ADDRESS: "42:6C:99:4F:96:D8",
        CONF_SENSOR_TYPE: "ld2410",
        CONF_PASSWORD: "abc123",
    }

    assert len(mock_setup_entry.mock_calls) == 1


async def test_bluetooth_discovery_already_setup(hass: HomeAssistant) -> None:
    """Test discovery via bluetooth with a valid device when already setup."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ADDRESS: "42:6C:99:4F:96:D8",
            CONF_NAME: "test-name",
            CONF_PASSWORD: "test-password",
            CONF_SENSOR_TYPE: "ld2410",
        },
        unique_id="426c994f96d8",
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_BLUETOOTH},
        data=LD2410b_SERVICE_INFO,
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_async_step_bluetooth_not_ld2410(hass: HomeAssistant) -> None:
    """Test discovery via bluetooth not ld2410."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_BLUETOOTH},
        data=NOT_LD2410_INFO,
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_supported"


async def test_async_step_bluetooth_not_connectable(hass: HomeAssistant) -> None:
    """Test discovery via bluetooth and its not connectable ld2410."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_BLUETOOTH},
        data=LD2410b_NOT_CONNECTABLE,
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_supported"

async def test_user_setup_ld2410_replaces_ignored(hass: HomeAssistant) -> None:
    """Test setting up a ld2410 replaces an ignored entry."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={}, unique_id="426c994f96d8", source=SOURCE_IGNORE
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.ld2410.config_flow.async_discovered_service_info",
        return_value=[LD2410b_SERVICE_INFO],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "password"

    with patch_async_setup_entry() as mock_setup_entry:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_PASSWORD: "abc123"}
        )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "HLK-LD2410 96D8"
    assert result["data"] == {
        CONF_ADDRESS: "42:6C:99:4F:96:D8",
        CONF_SENSOR_TYPE: "ld2410",
        CONF_PASSWORD: "abc123",
    }

    assert len(mock_setup_entry.mock_calls) == 1

async def test_user_setup_ld2410_1_or_2(hass: HomeAssistant) -> None:
    """Test the user initiated form with valid address."""

    with patch(
        "custom_components.ld2410.config_flow.async_discovered_service_info",
        return_value=[
            LD2410b_SERVICE_INFO,
            LD2410b_2_SERVICE_INFO
        ],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    with patch_async_setup_entry() as mock_setup_entry:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            USER_INPUT,
        )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "HLK-LD2410 96D8"
    assert result["data"] == {
        CONF_ADDRESS: "42:6C:99:4F:96:D8",
        CONF_SENSOR_TYPE: "ld2410"
    }

    assert len(mock_setup_entry.mock_calls) == 1


async def test_user_setup_ld2410_1_or_2_with_password(hass: HomeAssistant) -> None:
    """Test the user initiated form and valid address and a bot with a password."""

    with patch(
        "custom_components.ld2410.config_flow.async_discovered_service_info",
        return_value=[
            LD2410b_SERVICE_INFO,
            LD2410b_2_SERVICE_INFO
        ],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_ADDRESS: "42:6C:99:4F:96:D8"},
    )
    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "password"
    assert result2["errors"] is None

async def test_user_setup_single_bot_with_password(hass: HomeAssistant) -> None:
    """Test the user initiated form for a bot with a password."""

    with patch(
        "homeassistant.components.ld2410.config_flow.async_discovered_service_info",
        return_value=[LD2410b_SERVICE_INFO],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "password"
    assert result["errors"] is None

    with patch_async_setup_entry() as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_PASSWORD: "abc123"},
        )
        await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Bot 923B"
    assert result2["data"] == {
        CONF_ADDRESS: "798A8547-2A3D-C609-55FF-73FA824B923B",
        CONF_PASSWORD: "abc123",
        CONF_SENSOR_TYPE: "bot",
    }

    assert len(mock_setup_entry.mock_calls) == 1


async def test_user_setup_woencrypted_key(hass: HomeAssistant) -> None:
    """Test the user initiated form for a lock."""

    with patch(
        "homeassistant.components.ld2410.config_flow.async_discovered_service_info",
        return_value=[LD2410b_SERVICE_INFO],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "encrypted_choose_method"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "encrypted_key"}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "encrypted_key"
    assert result["errors"] == {}

    with patch(
        "ld2410.LD2410Lock.verify_encryption_key",
        return_value=False,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {

            },
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "encrypted_key"
    assert result["errors"] == {"base": "encryption_key_invalid"}

    with (
        patch_async_setup_entry() as mock_setup_entry,
        patch(
            "ld2410.LD2410Lock.verify_encryption_key",
            return_value=True,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {

            },
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Lock EEFF"
    assert result["data"] == {
        CONF_ADDRESS: "aa:bb:cc:dd:ee:ff",
        CONF_SENSOR_TYPE: "lock",
    }

    assert len(mock_setup_entry.mock_calls) == 1


async def test_user_setup_woencrypted_auth(hass: HomeAssistant) -> None:
    """Test the user initiated form for a lock."""

    with patch(
        "homeassistant.components.ld2410.config_flow.async_discovered_service_info",
        return_value=[LD2410b_SERVICE_INFO],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "encrypted_choose_method"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "encrypted_auth"}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "encrypted_auth"
    assert result["errors"] == {}

    with patch(
        "ld2410.LD2410Lock.async_retrieve_encryption_key",
        side_effect=LD2410AuthenticationError("error from api"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "",
                CONF_PASSWORD: "",
            },
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "encrypted_auth"
    assert result["errors"] == {"base": "auth_failed"}
    assert "error from api" in result["description_placeholders"]["error_detail"]

    with (
        patch_async_setup_entry() as mock_setup_entry,
        patch(
            "ld2410.LD2410Lock.verify_encryption_key",
            return_value=True,
        ),
        patch(
            "ld2410.LD2410Lock.async_retrieve_encryption_key",
            return_value={

            },
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "username",
                CONF_PASSWORD: "password",
            },
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Lock EEFF"
    assert result["data"] == {
        CONF_ADDRESS: "aa:bb:cc:dd:ee:ff",
        CONF_SENSOR_TYPE: "lock",
    }

    assert len(mock_setup_entry.mock_calls) == 1


async def test_user_setup_woencrypted_auth_ld2410_api_down(
    hass: HomeAssistant,
) -> None:
    """Test the user initiated form for a lock when the ld2410 api is down."""

    with patch(
        "homeassistant.components.ld2410.config_flow.async_discovered_service_info",
        return_value=[LD2410b_SERVICE_INFO],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "encrypted_choose_method"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "encrypted_auth"}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "encrypted_auth"
    assert result["errors"] == {}

    with patch(
        "ld2410.LD2410Lock.async_retrieve_encryption_key",
        side_effect=LD2410AccountConnectionError("LD2410 API down"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "",
                CONF_PASSWORD: "",
            },
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "api_error"
    assert result["description_placeholders"] == {"error_detail": "LD2410 API down"}


async def test_user_setup_wolock_or_bot(hass: HomeAssistant) -> None:
    """Test the user initiated form for a lock."""

    with patch(
        "homeassistant.components.ld2410.config_flow.async_discovered_service_info",
        return_value=[
            LD2410b_SERVICE_INFO,
            LD2410b_2_SERVICE_INFO,
        ],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        USER_INPUT,
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "encrypted_choose_method"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "encrypted_key"}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "encrypted_key"
    assert result["errors"] == {}

    with (
        patch_async_setup_entry() as mock_setup_entry,
        patch(
            "ld2410.LD2410Lock.verify_encryption_key",
            return_value=True,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {

            },
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Lock EEFF"
    assert result["data"] == {
        CONF_ADDRESS: "aa:bb:cc:dd:ee:ff",
        CONF_SENSOR_TYPE: "lock",
    }

    assert len(mock_setup_entry.mock_calls) == 1


async def test_user_setup_wosensor(hass: HomeAssistant) -> None:
    """Test the user initiated form with password and valid mac."""
    with patch(
        "homeassistant.components.ld2410.config_flow.async_discovered_service_info",
        return_value=[LD2410b_SERVICE_INFO],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"
    assert result["errors"] is None

    with patch_async_setup_entry() as mock_setup_entry:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Meter EEFF"
    assert result["data"] == {
        CONF_ADDRESS: "aa:bb:cc:dd:ee:ff",
        CONF_SENSOR_TYPE: "hygrometer",
    }

    assert len(mock_setup_entry.mock_calls) == 1


async def test_user_no_devices(hass: HomeAssistant) -> None:
    """Test the user initiated form with password and valid mac."""
    with patch(
        "homeassistant.components.ld2410.config_flow.async_discovered_service_info",
        return_value=[],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


async def test_async_step_user_takes_precedence_over_discovery(
    hass: HomeAssistant,
) -> None:
    """Test manual setup takes precedence over discovery."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_BLUETOOTH},
        data=LD2410b_SERVICE_INFO,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"

    with patch(
        "homeassistant.components.ld2410.config_flow.async_discovered_service_info",
        return_value=[LD2410b_SERVICE_INFO],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
        )
        assert result["type"] is FlowResultType.FORM

    with patch_async_setup_entry() as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={},
        )

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Curtain EEFF"
    assert result2["data"] == {
        CONF_ADDRESS: "aa:bb:cc:dd:ee:ff",
        CONF_SENSOR_TYPE: "curtain",
    }

    assert len(mock_setup_entry.mock_calls) == 1
    # Verify the original one was aborted
    assert not hass.config_entries.flow.async_progress(DOMAIN)


async def test_options_flow(hass: HomeAssistant) -> None:
    """Test updating options."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ADDRESS: "aa:bb:cc:dd:ee:ff",
            CONF_NAME: "test-name",
            CONF_PASSWORD: "test-password",
            CONF_SENSOR_TYPE: "bot",
        },
        options={
            CONF_RETRY_COUNT: 10,
        },
        unique_id="aabbccddeeff",
    )
    entry.add_to_hass(hass)

    with patch_async_setup_entry() as mock_setup_entry:
        entry = await init_integration(hass)

        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "init"
        assert result["errors"] is None

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_RETRY_COUNT: 3,
            },
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_RETRY_COUNT] == 3

    assert len(mock_setup_entry.mock_calls) == 2

    # Test changing of entry options.

    with patch_async_setup_entry() as mock_setup_entry:
        entry = await init_integration(hass)

        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "init"
        assert result["errors"] is None

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_RETRY_COUNT: 6,
            },
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_RETRY_COUNT] == 6

    assert len(mock_setup_entry.mock_calls) == 1

    assert entry.options[CONF_RETRY_COUNT] == 6


async def test_options_flow_lock_pro(hass: HomeAssistant) -> None:
    """Test updating options."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ADDRESS: "aa:bb:cc:dd:ee:ff",
            CONF_NAME: "test-name",
            CONF_PASSWORD: "test-password",
            CONF_SENSOR_TYPE: "lock_pro",
        },
        options={CONF_RETRY_COUNT: 10},
        unique_id="aabbccddeeff",
    )
    entry.add_to_hass(hass)

    # Test Force night_latch should be disabled by default.
    with patch_async_setup_entry() as mock_setup_entry:
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "init"
        assert result["errors"] is None

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_RETRY_COUNT: 3,
            },
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY

    assert len(mock_setup_entry.mock_calls) == 1

    # Test Set force night_latch to be enabled.

    with patch_async_setup_entry() as mock_setup_entry:
        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "init"
        assert result["errors"] is None

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
            },
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY

    assert len(mock_setup_entry.mock_calls) == 0


async def test_user_setup_worelay_switch_1pm_key(hass: HomeAssistant) -> None:
    """Test the user initiated form for a relay switch 1pm."""

    with patch(
        "homeassistant.components.ld2410.config_flow.async_discovered_service_info",
        return_value=[LD2410b_SERVICE_INFO],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "encrypted_choose_method"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "encrypted_key"}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "encrypted_key"
    assert result["errors"] == {}

    with (
        patch_async_setup_entry() as mock_setup_entry,
        patch(
            "ld2410.LD2410RelaySwitch.verify_encryption_key", return_value=True
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {

            },
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Relay Switch 1PM EEFF"
    assert result["data"] == {
        CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
        CONF_SENSOR_TYPE: "relay_switch_1pm",
    }

    assert len(mock_setup_entry.mock_calls) == 1


async def test_user_setup_worelay_switch_1pm_auth(hass: HomeAssistant) -> None:
    """Test the user initiated form for a relay switch 1pm."""

    with patch(
        "homeassistant.components.ld2410.config_flow.async_discovered_service_info",
        return_value=[LD2410b_SERVICE_INFO],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "encrypted_choose_method"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "encrypted_auth"}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "encrypted_auth"
    assert result["errors"] == {}

    with patch(
        "ld2410.LD2410RelaySwitch.async_retrieve_encryption_key",
        side_effect=LD2410AuthenticationError("error from api"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "",
                CONF_PASSWORD: "",
            },
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "encrypted_auth"
    assert result["errors"] == {"base": "auth_failed"}
    assert "error from api" in result["description_placeholders"]["error_detail"]

    with (
        patch_async_setup_entry() as mock_setup_entry,
        patch(
            "ld2410.LD2410RelaySwitch.async_retrieve_encryption_key",
            return_value={

            },
        ),
        patch(
            "ld2410.LD2410RelaySwitch.verify_encryption_key", return_value=True
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "username",
                CONF_PASSWORD: "password",
            },
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Relay Switch 1PM EEFF"
    assert result["data"] == {
        CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
        CONF_SENSOR_TYPE: "relay_switch_1pm",
    }

    assert len(mock_setup_entry.mock_calls) == 1


async def test_user_setup_worelay_switch_1pm_auth_ld2410_api_down(
    hass: HomeAssistant,
) -> None:
    """Test the user initiated form for a relay switch 1pm when the ld2410 api is down."""

    with patch(
        "homeassistant.components.ld2410.config_flow.async_discovered_service_info",
        return_value=[LD2410b_SERVICE_INFO],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "encrypted_choose_method"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"next_step_id": "encrypted_auth"}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "encrypted_auth"
    assert result["errors"] == {}

    with patch(
        "ld2410.LD2410RelaySwitch.async_retrieve_encryption_key",
        side_effect=LD2410AccountConnectionError("LD2410 API down"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "",
                CONF_PASSWORD: "",
            },
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "api_error"
    assert result["description_placeholders"] == {"error_detail": "LD2410 API down"}
