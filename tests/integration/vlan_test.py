# SPDX-License-Identifier: LGPL-2.1-or-later

from contextlib import contextmanager
import time

import pytest

import libnmstate
from libnmstate.error import NmstateValueError
from libnmstate.error import NmstateVerificationError
from libnmstate.schema import VLAN
from libnmstate.schema import Interface
from libnmstate.schema import InterfaceState
from libnmstate.schema import InterfaceType

from .testlib import assertlib
from .testlib import statelib
from .testlib.apply import apply_with_description
from .testlib.assertlib import assert_mac_address
from .testlib.env import nm_minor_version
from .testlib.vlan import vlan_interface

VLAN_IFNAME = "eth1.101"
VLAN2_IFNAME = "eth1.102"


@pytest.mark.tier1
def test_add_and_remove_vlan(eth1_up):
    with vlan_interface(
        VLAN_IFNAME, 101, eth1_up[Interface.KEY][0][Interface.NAME]
    ) as desired_state:
        assertlib.assert_state(desired_state)

    current_state = statelib.show_only((VLAN_IFNAME,))
    assert not current_state[Interface.KEY]


@pytest.fixture
def vlan_on_eth1(eth1_up):
    with vlan_interface(
        VLAN_IFNAME, 101, eth1_up[Interface.KEY][0][Interface.NAME]
    ) as desired_state:
        base_iface_name = desired_state[Interface.KEY][0][VLAN.CONFIG_SUBTREE][
            VLAN.BASE_IFACE
        ]
        iface_states = statelib.show_only((base_iface_name, VLAN_IFNAME))
        yield iface_states


@pytest.mark.tier1
def test_vlan_iface_uses_the_mac_of_base_iface(vlan_on_eth1):
    assert_mac_address(vlan_on_eth1)


def test_add_and_remove_two_vlans_on_same_iface(eth1_up):
    with two_vlans_on_eth1() as desired_state:
        assertlib.assert_state(desired_state)

    vlan_interfaces = [i[Interface.NAME] for i in desired_state[Interface.KEY]]
    current_state = statelib.show_only(vlan_interfaces)
    assert not current_state[Interface.KEY]


@pytest.mark.tier1
def test_two_vlans_on_eth1_change_mtu(eth1_up):
    with two_vlans_on_eth1() as desired_state:
        eth1_state = eth1_up[Interface.KEY][0]
        desired_state[Interface.KEY].append(eth1_state)
        for iface in desired_state[Interface.KEY]:
            iface[Interface.MTU] = 2000
        apply_with_description(
            "Set the MTU to 2000 for eth1, eth1.101, eth1.102 devices",
            desired_state,
        )

        eth1_102_state = next(
            ifstate
            for ifstate in desired_state[Interface.KEY]
            if ifstate[Interface.NAME] == VLAN2_IFNAME
        )
        eth1_state[Interface.MTU] = 2200
        eth1_102_state[Interface.MTU] = 2200
        apply_with_description(
            "Set the MTU to 2200 for eth1, eth1.102 devices",
            desired_state,
        )

        eth1_vlan_iface_cstate = statelib.show_only((VLAN_IFNAME,))
        assert eth1_vlan_iface_cstate[Interface.KEY][0][Interface.MTU] == 2000


@pytest.mark.tier1
def test_two_vlans_on_eth1_change_base_iface_mtu(eth1_up):
    with two_vlans_on_eth1() as desired_state:
        eth1_state = eth1_up[Interface.KEY][0]
        desired_state[Interface.KEY].append(eth1_state)
        for iface in desired_state[Interface.KEY]:
            iface[Interface.MTU] = 2000
        apply_with_description(
            "Set the MTU to 2000 for eth1, eth1.101, eth1.102 devices",
            desired_state,
        )

        eth1_state[Interface.MTU] = 2200
        apply_with_description(
            "Set the MTU to 2200 for eth1 device",
            eth1_up,
        )
        eth1_vlan_iface_cstate = statelib.show_only((VLAN_IFNAME,))
        assert eth1_vlan_iface_cstate[Interface.KEY][0][Interface.MTU] == 2000


@pytest.mark.tier1
def test_two_vlans_on_eth1_change_mtu_rollback(eth1_up):
    with two_vlans_on_eth1() as desired_state:
        eth1_state = eth1_up[Interface.KEY][0]
        desired_state[Interface.KEY].append(eth1_state)
        for iface in desired_state[Interface.KEY]:
            iface[Interface.MTU] = 2000
        apply_with_description(
            "Set the MTU to 2000 for eth1, eth1.101, eth1.102 devices",
            desired_state,
        )

        for iface in desired_state[Interface.KEY]:
            iface[Interface.MTU] = 2200
        apply_with_description(
            "Set the MTU to 2200 for eth1, eth1.101, eth1.102 devices",
            desired_state,
            commit=False,
        )
        libnmstate.rollback()

        time.sleep(5)  # Give some time for NetworkManager to rollback

        eth1_vlan_iface_cstate = statelib.show_only((VLAN_IFNAME,))
        assert eth1_vlan_iface_cstate[Interface.KEY][0][Interface.MTU] == 2000


def test_rollback_for_vlans(eth1_up):
    current_state = libnmstate.show()
    desired_state = create_two_vlans_state()

    desired_state[Interface.KEY][1]["invalid_key"] = "foo"
    with pytest.raises((NmstateVerificationError, NmstateValueError)):
        libnmstate.apply(desired_state)

    time.sleep(5)  # Give some time for NetworkManager to rollback
    current_state_after_apply = libnmstate.show()
    assert current_state == current_state_after_apply


def test_set_vlan_iface_down(eth1_up):
    with vlan_interface(
        VLAN_IFNAME, 101, eth1_up[Interface.KEY][0][Interface.NAME]
    ):
        apply_with_description(
            "Bring down the vlan device eth1.101",
            {
                Interface.KEY: [
                    {
                        Interface.NAME: VLAN_IFNAME,
                        Interface.TYPE: InterfaceType.VLAN,
                        Interface.STATE: InterfaceState.DOWN,
                    }
                ]
            },
        )

        assertlib.assert_absent(VLAN_IFNAME)


def test_add_new_base_iface_with_vlan():
    iface_base = "dummy00"
    desired_state = {
        Interface.KEY: [
            {
                Interface.NAME: "dummy00.101",
                Interface.TYPE: InterfaceType.VLAN,
                Interface.STATE: InterfaceState.UP,
                VLAN.CONFIG_SUBTREE: {
                    VLAN.ID: 101,
                    VLAN.BASE_IFACE: iface_base,
                },
            },
            {
                Interface.NAME: iface_base,
                Interface.TYPE: InterfaceType.DUMMY,
                Interface.STATE: InterfaceState.UP,
            },
        ]
    }
    try:
        apply_with_description(
            "Bring up the dummy device dummy00, configure the vlan device dummy00.101 with vlan ID 101 on the base interface dummy00",
            desired_state,
        )
    finally:
        for ifstate in desired_state[Interface.KEY]:
            ifstate[Interface.STATE] = InterfaceState.ABSENT
        apply_with_description(
            "Delete the dummy device dummy00 and delete the vlan device dummy00.101",
            desired_state,
            verify_change=False,
        )


def test_add_vlan_with_mismatching_name_and_id(eth1_up):
    with vlan_interface(
        VLAN_IFNAME, 200, eth1_up[Interface.KEY][0][Interface.NAME]
    ) as desired_state:
        assertlib.assert_state(desired_state)


@pytest.mark.tier1
def test_add_vlan_and_modify_vlan_id(eth1_up):
    with vlan_interface(
        VLAN_IFNAME, 101, eth1_up[Interface.KEY][0][Interface.NAME]
    ) as desired_state:
        assertlib.assert_state(desired_state)
        desired_state[Interface.KEY][0][VLAN.CONFIG_SUBTREE][VLAN.ID] = 200
        apply_with_description(
            "Set the vlan ID to 200 for the base interface eth1", desired_state
        )
        assertlib.assert_state(desired_state)

    assertlib.assert_absent(VLAN_IFNAME)


@pytest.mark.tier1
def test_vlan_enable_and_disable_accept_all_mac_addresses(eth1_up):
    with vlan_interface(
        VLAN_IFNAME, 101, eth1_up[Interface.KEY][0][Interface.NAME]
    ) as d_state:
        d_state[Interface.KEY][0][Interface.ACCEPT_ALL_MAC_ADDRESSES] = True
        apply_with_description(
            "Enable accept all mac address for eth1 device", d_state
        )
        assertlib.assert_state(d_state)

        d_state[Interface.KEY][0][Interface.ACCEPT_ALL_MAC_ADDRESSES] = False
        apply_with_description(
            "Disable accept all mac address for eth1 device", d_state
        )
        assertlib.assert_state(d_state)

    assertlib.assert_absent(VLAN_IFNAME)


@contextmanager
def two_vlans_on_eth1():
    desired_state = create_two_vlans_state()
    apply_with_description(
        "Create the vlan interface eth1.101 with the vlan ID 101 and base interface eth1, create the vlan interface eth1.102 with the vlan ID 102 and base interface eth1",
        desired_state,
    )
    try:
        yield desired_state
    finally:
        apply_with_description(
            "Remove the vlan interface eth1.101 and eth1.102",
            {
                Interface.KEY: [
                    {
                        Interface.NAME: VLAN_IFNAME,
                        Interface.TYPE: InterfaceType.VLAN,
                        Interface.STATE: InterfaceState.ABSENT,
                    },
                    {
                        Interface.NAME: VLAN2_IFNAME,
                        Interface.TYPE: InterfaceType.VLAN,
                        Interface.STATE: InterfaceState.ABSENT,
                    },
                ]
            },
        )


def create_two_vlans_state():
    return {
        Interface.KEY: [
            {
                Interface.NAME: VLAN_IFNAME,
                Interface.TYPE: InterfaceType.VLAN,
                Interface.STATE: InterfaceState.UP,
                VLAN.CONFIG_SUBTREE: {VLAN.ID: 101, VLAN.BASE_IFACE: "eth1"},
            },
            {
                Interface.NAME: VLAN2_IFNAME,
                Interface.TYPE: InterfaceType.VLAN,
                Interface.STATE: InterfaceState.UP,
                VLAN.CONFIG_SUBTREE: {VLAN.ID: 102, VLAN.BASE_IFACE: "eth1"},
            },
        ]
    }


def test_preserve_existing_vlan_conf(eth1_up):
    with vlan_interface(
        VLAN_IFNAME, 101, eth1_up[Interface.KEY][0][Interface.NAME]
    ) as desired_state:
        apply_with_description(
            "Set up the vlan interface eth1.101",
            {
                Interface.KEY: [
                    {
                        Interface.NAME: VLAN_IFNAME,
                    }
                ]
            },
        )
        assertlib.assert_state(desired_state)


@pytest.mark.skipif(
    nm_minor_version() < 41,
    reason="Modifying VLAN protocol is not supported on NM 1.41-.",
)
def test_change_vlan_protocol(vlan_on_eth1):
    dot1q_state = {
        Interface.KEY: [
            {
                Interface.NAME: VLAN_IFNAME,
                Interface.TYPE: InterfaceType.VLAN,
                Interface.STATE: InterfaceState.UP,
                VLAN.CONFIG_SUBTREE: {
                    VLAN.ID: 102,
                    VLAN.BASE_IFACE: "eth1",
                    VLAN.PROTOCOL: "802.1q",
                },
            }
        ]
    }
    qinq_state = {
        Interface.KEY: [
            {
                Interface.NAME: VLAN_IFNAME,
                Interface.TYPE: InterfaceType.VLAN,
                Interface.STATE: InterfaceState.UP,
                VLAN.CONFIG_SUBTREE: {
                    VLAN.ID: 102,
                    VLAN.BASE_IFACE: "eth1",
                    VLAN.PROTOCOL: "802.1ad",
                },
            }
        ]
    }
    apply_with_description(
        "Create the vlan interface eth1.101 with vlan ID 102, base interface eth1, vlan protocol 802.1ad",
        qinq_state,
    )
    assertlib.assert_state_match(qinq_state)

    apply_with_description(
        "Create the vlan interface eth1.101 with vlan ID 102, base interface eth1, vlan protocol 802.1q",
        dot1q_state,
    )
    assertlib.assert_state_match(dot1q_state)


@pytest.mark.skipif(
    nm_minor_version() < 41,
    reason="Modifying VLAN protocol is not supported on NM 1.41-.",
)
def test_add_qinq_vlan(eth1_up):
    with vlan_interface(
        VLAN_IFNAME,
        102,
        "eth1",
        protocol="802.1ad",
    ) as desired_state:
        assertlib.assert_state_match(desired_state)
    assertlib.assert_absent(VLAN_IFNAME)


def test_configure_vlan_with_reaorder_headers(vlan_on_eth1):
    flags_state = {
        Interface.KEY: [
            {
                Interface.NAME: VLAN_IFNAME,
                Interface.TYPE: InterfaceType.VLAN,
                Interface.STATE: InterfaceState.UP,
                VLAN.CONFIG_SUBTREE: {
                    VLAN.ID: 102,
                    VLAN.BASE_IFACE: "eth1",
                    VLAN.REORDER_HEADERS: True,
                },
            }
        ]
    }
    apply_with_description(
        "Configure the interface eth1.101 with vlan ID 102, base interface eth1, reorder headers flag enabled",
        flags_state,
    )
    assertlib.assert_state_match(flags_state)

    flags_state[Interface.KEY][0][VLAN.CONFIG_SUBTREE][
        VLAN.REORDER_HEADERS
    ] = False
    apply_with_description(
        "Configure the interface eth1.101 with vlan ID 102, base interface eth1, reorder headers flag disabled",
        flags_state,
    )
    assertlib.assert_state_match(flags_state)


def test_configure_vlan_with_loose_binding(vlan_on_eth1):
    flags_state = {
        Interface.KEY: [
            {
                Interface.NAME: VLAN_IFNAME,
                Interface.TYPE: InterfaceType.VLAN,
                Interface.STATE: InterfaceState.UP,
                VLAN.CONFIG_SUBTREE: {
                    VLAN.ID: 102,
                    VLAN.BASE_IFACE: "eth1",
                    VLAN.LOOSE_BINDING: True,
                },
            }
        ]
    }
    apply_with_description(
        "Configure the interface eth1.101 with vlan ID 102, base interface eth1, loose binding flag enabled",
        flags_state,
    )
    assertlib.assert_state_match(flags_state)

    flags_state[Interface.KEY][0][VLAN.CONFIG_SUBTREE][
        VLAN.LOOSE_BINDING
    ] = False
    apply_with_description(
        "Configure the interface eth1.101 with vlan ID 102, base interface eth1, loose binding flag disabled",
        flags_state,
    )
    assertlib.assert_state_match(flags_state)


def test_configure_vlan_with_gvrp(vlan_on_eth1):
    protocol = VLAN.REGISTRATION_PROTOCOL_GVRP
    flags_state = {
        Interface.KEY: [
            {
                Interface.NAME: VLAN_IFNAME,
                Interface.TYPE: InterfaceType.VLAN,
                Interface.STATE: InterfaceState.UP,
                VLAN.CONFIG_SUBTREE: {
                    VLAN.ID: 102,
                    VLAN.BASE_IFACE: "eth1",
                    VLAN.REGISTRATION_PROTOCOL: protocol,
                },
            }
        ]
    }
    apply_with_description(
        "Configure the interface eth1.101 with vlan ID 102, base interface eth1, registration protocol set to gvrp",
        flags_state,
    )
    assertlib.assert_state_match(flags_state)

    flags_state[Interface.KEY][0][VLAN.CONFIG_SUBTREE][
        VLAN.REGISTRATION_PROTOCOL
    ] = VLAN.REGISTRATION_PROTOCOL_NONE
    apply_with_description(
        "Configure the interface eth1.101 with vlan ID 102, base interface eth1, registration protocol set to none",
        flags_state,
    )
    assertlib.assert_state_match(flags_state)


def test_configure_vlan_with_mvrp(vlan_on_eth1):
    protocol = VLAN.REGISTRATION_PROTOCOL_MVRP
    flags_state = {
        Interface.KEY: [
            {
                Interface.NAME: VLAN_IFNAME,
                Interface.TYPE: InterfaceType.VLAN,
                Interface.STATE: InterfaceState.UP,
                VLAN.CONFIG_SUBTREE: {
                    VLAN.ID: 102,
                    VLAN.BASE_IFACE: "eth1",
                    VLAN.REGISTRATION_PROTOCOL: protocol,
                },
            }
        ]
    }
    apply_with_description(
        "Configure the interface eth1.101 with vlan ID 102, base interface eth1, registration protocol set to mvrp",
        flags_state,
    )
    assertlib.assert_state_match(flags_state)

    flags_state[Interface.KEY][0][VLAN.CONFIG_SUBTREE][
        VLAN.REGISTRATION_PROTOCOL
    ] = VLAN.REGISTRATION_PROTOCOL_NONE
    apply_with_description(
        "Configure the interface eth1.101 with vlan ID 102, base interface eth1, registration protocol set to none",
        flags_state,
    )
    assertlib.assert_state_match(flags_state)


def test_new_vlan_default_to_reorder_headers(eth1_up):
    with vlan_interface(VLAN_IFNAME, 102, "eth1") as desired_state:
        desired_state[Interface.KEY][0][VLAN.CONFIG_SUBTREE][
            VLAN.REORDER_HEADERS
        ] = True
        assertlib.assert_state_match(desired_state)
    assertlib.assert_absent(VLAN_IFNAME)


@pytest.fixture
def vlan_on_eth1_with_reorder_headers_off(vlan_on_eth1):
    desired_state = {
        Interface.KEY: [
            {
                Interface.NAME: VLAN_IFNAME,
                Interface.TYPE: InterfaceType.VLAN,
                Interface.STATE: InterfaceState.UP,
                VLAN.CONFIG_SUBTREE: {
                    VLAN.ID: 102,
                    VLAN.BASE_IFACE: "eth1",
                    VLAN.REORDER_HEADERS: False,
                },
            }
        ]
    }
    apply_with_description(
        "Configure the interface eth1.101 with vlan ID 102, base interface eth1, reorder headers flag disabled",
        desired_state,
    )
    yield


def test_vlan_do_not_override_reorder_headers_if_not_mentioned(
    vlan_on_eth1_with_reorder_headers_off,
):
    desired_state = {
        Interface.KEY: [
            {
                Interface.NAME: VLAN_IFNAME,
                Interface.TYPE: InterfaceType.VLAN,
                Interface.STATE: InterfaceState.UP,
                VLAN.CONFIG_SUBTREE: {
                    VLAN.ID: 102,
                    VLAN.BASE_IFACE: "eth1",
                },
            }
        ]
    }
    apply_with_description(
        "Configure the interface eth1.101 with vlan ID 102, base interface eth1",
        desired_state,
    )
    current_state = statelib.show_only((VLAN_IFNAME,))
    assert not current_state[Interface.KEY][0][VLAN.CONFIG_SUBTREE][
        VLAN.REORDER_HEADERS
    ]
