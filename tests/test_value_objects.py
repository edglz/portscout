import pytest

from portscout.domain.value_objects import (
    InvalidPortSpecError,
    InvalidTargetError,
    PortSpec,
    Target,
    get_profile,
)


@pytest.mark.parametrize(
    "value",
    ["192.168.1.1", "10.0.0.0/24", "example.com", "sub.domain.co.uk", "::1", "fe80::/10"],
)
def test_valid_targets(value: str) -> None:
    assert Target(value).value == value


@pytest.mark.parametrize("value", ["", "   ", "999.999.999.999", "not a host!", "-bad.com"])
def test_invalid_targets(value: str) -> None:
    with pytest.raises(InvalidTargetError):
        Target(value)


def test_target_is_trimmed() -> None:
    assert Target("  8.8.8.8  ").value == "8.8.8.8"


@pytest.mark.parametrize("value", ["22", "22,80,443", "1-1024", "80,8000-8100"])
def test_valid_portspecs(value: str) -> None:
    assert PortSpec(value).value == value


@pytest.mark.parametrize("value", ["", "-1", "70000", "80,", "abc", "80-"])
def test_invalid_portspecs(value: str) -> None:
    with pytest.raises(InvalidPortSpecError):
        PortSpec(value)


def test_profiles_lookup() -> None:
    assert get_profile("full").requires_privilege is True
    assert get_profile("quick").requires_privilege is False
    with pytest.raises(KeyError):
        get_profile("nope")
