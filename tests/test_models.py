import pytest
from pydantic import ValidationError
from app.models import (
    WritePropertyRequest,
    ReadMultiplePropertiesRequest,
    ReadMultiplePropertiesRequestWrapper,
    DeviceInstanceValidator,
    DeviceInstanceRange,
    nan_or_inf_check,
)


@pytest.mark.parametrize(
    "device_instance, object_identifier, property_identifier, value, priority, expected_exception",
    [
        (123, "analog-value,11", "present-value", 42, None, None),  # Passing test
        (123, "analog-value,-11", "present-value", 42, None, ValueError),  # Fail test based on -11
        (123, "analog-value,asdf", "present-value", 42, None, ValueError),  # Fail test based on asdf
        (123, "asdf123-value,11", "present-value", 42, None, ValueError),  # Fail test based on asdf123
        (123, "analog-value,11", "present1234-value", 42, None, ValueError),  # Fail test based on present1234
        (123, "analog-value,11", "present-value", "test", None, None),  # Passing test with string value
        (123, "analog-value,11", "present-value", 42.5, None, None),  # Passing test with float value
        (123, "analog-value,11", "present-value", 42, 5, None),  # Passing test with priority
        (123, "analog-value,11", "present-value", 42, 17, ValueError),  # Fail test with invalid priority
    ]
)
def test_write_property_request(device_instance, object_identifier, property_identifier, value, priority, expected_exception):
    if expected_exception is None:
        assert WritePropertyRequest(
            device_instance=device_instance,
            object_identifier=object_identifier,
            property_identifier=property_identifier,
            value=value,
            priority=priority
        )
    else:
        with pytest.raises(expected_exception):
            WritePropertyRequest(
                device_instance=device_instance,
                object_identifier=object_identifier,
                property_identifier=property_identifier,
                value=value,
                priority=priority
            )


@pytest.mark.parametrize(
    "device_instance, requests, expected_exception",
    [
        # Valid cases
        (201201, [{"object_identifier": "analog-input,2", "property_identifier": "present-value"}], None),
        (201201, [{"object_identifier": "analog-input,2", "property_identifier": "units"}], None),
        (201201, [{"object_identifier": "analog-value,301", "property_identifier": "description"}], None),
        
        # Invalid object_identifier cases
        (201201, [{"object_identifier": "analog-input,-2", "property_identifier": "present-value"}], ValidationError),
        (201201, [{"object_identifier": "analog-input,asdf", "property_identifier": "present-value"}], ValidationError),
        (201201, [{"object_identifier": "asdf-input,2", "property_identifier": "present-value"}], ValidationError),

        # Invalid property_identifier cases
        (201201, [{"object_identifier": "analog-input,2", "property_identifier": "invalid-property"}], ValidationError),

        # Mixed valid and invalid cases
        (201201, [
            {"object_identifier": "analog-input,2", "property_identifier": "present-value"},
            {"object_identifier": "analog-input,2", "property_identifier": "units"},
            {"object_identifier": "analog-value,301", "property_identifier": "description"},
            {"object_identifier": "analog-fart,301", "property_identifier": "description"}
        ], ValidationError)
    ]
)
def test_read_multiple_properties_request(device_instance, requests, expected_exception):
    if expected_exception is None:
        assert ReadMultiplePropertiesRequestWrapper(
            device_instance=device_instance,
            requests=[ReadMultiplePropertiesRequest(**req) for req in requests]
        )
    else:
        with pytest.raises(expected_exception):
            ReadMultiplePropertiesRequestWrapper(
                device_instance=device_instance,
                requests=[ReadMultiplePropertiesRequest(**req) for req in requests]
            )


@pytest.mark.parametrize(
    "device_instance, expected_exception",
    [
        (0, None),  # Minimum valid device instance
        (4194303, None),  # Maximum valid device instance
        (-1, ValidationError),  # Below minimum
        (4194304, ValidationError),  # Above maximum
        ("not-an-int", ValidationError),  # Invalid type
    ]
)
def test_device_instance_validator(device_instance, expected_exception):
    if expected_exception is None:
        assert DeviceInstanceValidator(device_instance=device_instance)
    else:
        with pytest.raises(expected_exception):
            DeviceInstanceValidator(device_instance=device_instance)


@pytest.mark.parametrize(
    "encoded_value, expected_result",
    [
        (float('nan'), "NaN"),  # Test for NaN
        (float('inf'), "Inf"),  # Test for positive infinity
        (float('-inf'), "-Inf"),  # Test for negative infinity
        (42.0, 42.0),  # Test for regular float
        (42, 42),  # Test for integer
        ("test", "test"),  # Test for string
    ]
)
def test_nan_or_inf_check(encoded_value, expected_result):
    assert nan_or_inf_check(encoded_value) == expected_result


@pytest.mark.parametrize(
    "start_instance, end_instance, expected_exception",
    [
        (0, 4194303, None),  # Valid range
        (0, 0, None),  # Single valid instance
        (4194303, 4194303, None),  # Single valid instance at max range
        (-1, 4194303, ValidationError),  # Invalid start instance
        (0, 4194304, ValidationError),  # Invalid end instance
        (4194304, 0, ValidationError),  # Invalid range
        ("not-an-int", 4194303, ValidationError),  # Invalid type for start instance
        (0, "not-an-int", ValidationError),  # Invalid type for end instance
    ]
)
def test_device_instance_range(start_instance, end_instance, expected_exception):
    if expected_exception is None:
        assert DeviceInstanceRange(
            start_instance=start_instance,
            end_instance=end_instance
        )
    else:
        with pytest.raises(expected_exception):
            DeviceInstanceRange(
                start_instance=start_instance,
                end_instance=end_instance
            )
