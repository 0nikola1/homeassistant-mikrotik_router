#!/usr/bin/env python3
"""Test script to check config flow schema."""

import sys
import os
sys.path.insert(0, '/workspaces/homeassistant-mikrotik_router')

try:
    import voluptuous as vol
    from homeassistant.const import (
        CONF_NAME, CONF_HOST, CONF_PORT, CONF_USERNAME, CONF_PASSWORD,
        CONF_SSL, CONF_VERIFY_SSL
    )
    from custom_components.mikrotik_router.const import (
        DOMAIN, CONF_POE_INTERFACES, CONF_POE_GROUPS
    )

    print("Testing basic schema creation...")

    # Test basic schema
    schema_dict = {
        vol.Required(CONF_NAME, default="Test"): str,
        vol.Required(CONF_HOST, default="10.0.0.1"): str,
        vol.Required(CONF_USERNAME, default="admin"): str,
        vol.Required(CONF_PASSWORD, default=""): str,
        vol.Optional(CONF_PORT, default=8728): int,
        vol.Optional(CONF_SSL, default=False): bool,
        vol.Optional(CONF_VERIFY_SSL, default=False): bool,
        vol.Optional("poe_only_mode", default=False): bool,
    }

    schema = vol.Schema(schema_dict)
    print("✓ Basic schema created successfully")

    # Test schema with empty POE interfaces
    schema_dict_empty = schema_dict.copy()
    schema_dict_empty[vol.Optional(CONF_POE_INTERFACES, default=[])] = [str]
    schema_dict_empty[vol.Optional(CONF_POE_GROUPS, default="")] = str

    schema_empty = vol.Schema(schema_dict_empty)
    print("✓ Schema with empty POE options created successfully")

    # Test validation with empty POE
    test_data_empty = {
        CONF_NAME: "Test Router",
        CONF_HOST: "192.168.1.1",
        CONF_USERNAME: "admin",
        CONF_PASSWORD: "password",
        CONF_POE_INTERFACES: [],
        CONF_POE_GROUPS: ""
    }

    result_empty = schema_empty(test_data_empty)
    print(f"✓ Schema validation with empty POE successful: {result_empty}")

    # Test schema with POE interfaces
    schema_dict_poe[vol.Optional(CONF_POE_INTERFACES, default=[])] = vol.MultiSelect(poe_interfaces)
    schema_dict_poe[vol.Optional(CONF_POE_GROUPS, default="")] = str

    schema_poe = vol.Schema(schema_dict_poe)
    print("✓ Schema with POE MultiSelect created successfully")

    # Test validation
    test_data = {
        CONF_NAME: "Test Router",
        CONF_HOST: "192.168.1.1",
        CONF_USERNAME: "admin",
        CONF_PASSWORD: "password",
        CONF_POE_INTERFACES: ["ether1"],
        CONF_POE_GROUPS: "Cameras: ether1,ether2"
    }

    result = schema_poe(test_data)
    print(f"✓ Schema validation successful: {result}")

    print("All tests passed!")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)