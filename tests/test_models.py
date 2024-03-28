# test_models.py
import pytest
from app.models import WritePropertyRequest

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
