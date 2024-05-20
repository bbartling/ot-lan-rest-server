from pydantic import BaseModel, conint, Field, ValidationError, field_validator
from typing import Union, Optional, List
from bacpypes3.primitivedata import PropertyIdentifier, ObjectType

class BaseResponse(BaseModel):
    success: bool
    message: str
    data: dict = None

class WritePropertyRequest(BaseModel):
    device_instance: conint(ge=0, le=4194303) = Field(...)
    object_identifier: str
    property_identifier: str
    value: Union[float, int, str]
    priority: Optional[conint(ge=1, le=16)] = Field(default=None)

    @field_validator('property_identifier')
    def validate_property_identifier(cls, v):
        valid_property_identifiers = set(PropertyIdentifier._enum_map.keys())
        if v not in valid_property_identifiers:
            raise ValueError(f"property_identifier '{v}' is not a valid BACnet property identifier")
        return v

    @field_validator('object_identifier')
    def validate_object_identifier(cls, v):
        if ',' not in v:
            raise ValueError("object_identifier must include a type and an instance number separated by a comma")

        object_type, instance_str = v.split(',', 1)
        valid_object_type_identifiers = set(ObjectType._enum_map.keys())
        if object_type not in valid_object_type_identifiers:
            raise ValueError(f"object_identifier '{object_type}' is not a valid BACnet object type")

        try:
            instance_number = int(instance_str)
            if not (0 < instance_number < (1 << 22) - 1):
                raise ValueError("Instance number out of range")
        except ValueError as e:
            raise ValueError(f"Invalid instance number: {e}")

        return v



class ReadMultiplePropertiesRequest(BaseModel):
    object_identifier: str
    property_identifier: str

    @field_validator('object_identifier')
    def validate_object_identifier(cls, v):
        if ',' not in v:
            raise ValueError("object_identifier must include a type and an instance number separated by a comma")

        object_type, instance_str = v.split(',', 1)
        valid_object_type_identifiers = set(ObjectType._enum_map.keys())
        if object_type not in valid_object_type_identifiers:
            raise ValueError(f"object_identifier '{object_type}' is not a valid BACnet object type")

        try:
            instance_number = int(instance_str)
            if not (0 < instance_number < (1 << 22) - 1):
                raise ValueError("Instance number out of range")
        except ValueError as e:
            raise ValueError(f"Invalid instance number: {e}")

        return v

    @field_validator('property_identifier')
    def validate_property_identifier(cls, v):
        valid_property_identifiers = set(PropertyIdentifier._enum_map.keys())
        if v not in valid_property_identifiers:
            raise ValueError(f"property_identifier '{v}' is not a valid BACnet property identifier")
        return v

class ReadMultiplePropertiesRequestWrapper(BaseModel):
    device_instance: conint(ge=0, le=4194303) = Field(...)
    requests: List[ReadMultiplePropertiesRequest]
