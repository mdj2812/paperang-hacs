"""Test fixtures for paperang custom component tests.

Requires pytest-homeassistant-custom-component for the ``hass`` fixture.
"""

pytest_plugins = ["pytest_homeassistant_custom_component"]

# The ``hass`` fixture is provided by pytest-homeassistant-custom-component.
# It sets up a fully functional HomeAssistant test instance with the custom
# component loaded, allowing tests to use:
#   hass.config_entries.flow.async_init(...)
#   await hass.async_block_till_done()
#   etc.
