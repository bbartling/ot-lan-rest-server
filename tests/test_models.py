# test_models.py
import pytest
from pydantic import ValidationError
from app.models import WritePropertyRequest, ReadMultiplePropertiesRequest, ReadMultiplePropertiesRequestWrapper


@pytest.mark.parametrize(
    "device_instance, object_identifier, property_identifier, value, priority, expected_exception",
    [
        (123, "analog-value,11", "present-value", 42, None, None),  # Passing test
        (123, "analog-value,-11", "present-value", 42, None, ValueError),  # Fail test based on -11
        (123, "analog-value,asdf", "present-value", 42, None, ValueError),  # Fail test based on asdf
        (123, "asdf123-value,11", "present-value", 42, None, ValueError),  # Fail test based on asdf123
        (123, "analog-value,11", "present1234-value", 42, None, ValueError),  # Fail test based on present1234
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