from __future__ import annotations

import asyncio
import os
import math
import re
import argparse
from contextlib import asynccontextmanager
from typing import Optional, List, Tuple

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Query, Depends, status, Path, Body
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from bacpypes3.debugging import ModuleLogger
from bacpypes3.argparse import SimpleArgumentParser
from bacpypes3.pdu import Address, GlobalBroadcast
from bacpypes3.primitivedata import (
    Atomic,
    ObjectIdentifier,
    Null,
    PropertyIdentifier,
    ObjectType,
)
from bacpypes3.constructeddata import Sequence, AnyAtomic, Array, List as BacpypesList
from bacpypes3.apdu import ErrorRejectAbortNack, PropertyReference, ErrorType
from bacpypes3.apdu import AbortReason, AbortPDU, ErrorRejectAbortNack
from bacpypes3.app import Application
from bacpypes3.settings import settings
from bacpypes3.json.util import (
    atomic_encode,
    sequence_to_json,
    extendedlist_to_json_list,
)

from bacpypes3.vendor import get_vendor_info

from models import (
    BaseResponse,
    WritePropertyRequest,
    ReadMultiplePropertiesRequest,
    ReadMultiplePropertiesRequestWrapper,
    DeviceInstanceValidator,
    nan_or_inf_check, 
    DeviceInstanceRange
)


# some debugging
_debug = 0
_log = ModuleLogger(globals())

# globals
args: argparse.Namespace
service: Application


def get_current_username(credentials: HTTPBasicCredentials = Depends(HTTPBasic())):
    correct_username = os.getenv("BASIC_AUTH_USERNAME", "default_username")
    correct_password = os.getenv("BASIC_AUTH_PASSWORD", "default_password")

    if (
        credentials.username == correct_username
        and credentials.password == correct_password
    ):
        return credentials.username
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )


async def _read_property(
    device_instance: int, object_identifier: str, property_identifier: str
):
    _log.debug("_read_property %r %r", device_instance, object_identifier)
    global service

    device_address = await get_device_address(device_instance)

    try:
        property_value = await service.read_property(
            device_address, ObjectIdentifier(object_identifier), property_identifier
        )
        _log.debug("    - property_value: %r", property_value)
    except ErrorRejectAbortNack as err:
        _log.error("    - exception: %r", err)
        return f"BACnet error/reject/abort: {err}"
    except ValueError as ve:
        _log.error("    - exception: %r", ve)
        return f"BACnet value error: {ve}"

    if isinstance(property_value, AnyAtomic):
        property_value = property_value.get_value()

    if isinstance(property_value, Atomic):
        encoded_value = atomic_encode(property_value)
    elif isinstance(property_value, Sequence):
        encoded_value = sequence_to_json(property_value)
    elif isinstance(property_value, (Array, List)):
        encoded_value = extendedlist_to_json_list(property_value)
    else:
        return f"JSON encoding: {property_value}"

    encoded_value = nan_or_inf_check(encoded_value)
    return property_identifier, encoded_value


async def _write_property(
    device_instance: int,
    object_identifier: ObjectIdentifier,
    property_identifier: str,
    value: str,
    priority: int = -1,
):
    _log.debug(f" Write Prop Device Instance: {device_instance}")
    _log.debug(f" Write Prop Object Identifier: {object_identifier}")
    _log.debug(f" Write Prop Property Identifier: {property_identifier}")
    _log.debug(f" Write Prop Value: {value}")
    _log.debug(f" Write Prop Value Type {type(value)}")
    _log.debug(f" Write Prop Priority: {priority}")

    device_address = await get_device_address(device_instance)
    property_identifier, property_array_index = parse_property_identifier(
        property_identifier
    )
    if value == "null":
        _log.debug(f" Null hit! {type(value)}")
        if priority is None:
            return "BACnet Error, null is only for releasing overrides and requires a priority to release that override"
        value = Null(())

    try:
        object_identifier = ObjectIdentifier(object_identifier)
    except ErrorRejectAbortNack as err:
        _log.error("    - exception on point ObjectIdentifier conversion: %r", err)
        return str(err)

    try:
        response = await service.write_property(
            device_address,
            object_identifier,
            property_identifier,
            value,
            property_array_index,
            priority,
        )
        _log.debug("    - response: %r", response)
        return response
    except ErrorRejectAbortNack as err:
        _log.error("    - exception: %r", err)
        return str(err)


async def get_device_address(device_instance: int) -> Address:
    device_info = service.device_info_cache.instance_cache.get(device_instance, None)
    if device_info:
        device_address = device_info.device_address
        _log.debug(f" gda - Cached address: {device_address}")
    else:
        i_ams = await service.who_is(device_instance, device_instance)
        if not i_ams:
            raise ValueError(f" gda - Device not found: {device_instance}")
        if len(i_ams) > 1:
            raise ValueError(f" gda - Multiple devices found: {device_instance}")
        device_address = i_ams[0].pduSource
        _log.debug(f" gda - Resolved address: {device_address}")
    return device_address


def parse_property_identifier(property_identifier: str):
    property_index_re = re.compile(r"^([A-Za-z-]+)(?:\[([0-9]+)\])?$")
    property_index_match = property_index_re.match(property_identifier)
    if not property_index_match:
        return "Property specification incorrect"
    property_identifier, property_array_index = property_index_match.groups()
    property_array_index = (
        int(property_array_index) if property_array_index is not None else None
    )
    return property_identifier, property_array_index



async def perform_who_is(start_instance: int, end_instance: int):
    global service

    try:
        i_ams = await service.who_is(start_instance, end_instance)
        if not i_ams:
            no_response_str = f"No response(s) on WhoIs start_instance {start_instance} end_instance {end_instance}"
            _log.error(" - " + no_response_str)
            return no_response_str
        
        result = []
        for i_am in i_ams:
            _log.debug("    - i_am: %r", i_am)

            device_address: Address = i_am.pduSource
            device_identifier: ObjectIdentifier = i_am.iAmDeviceIdentifier

            _log.debug(f"{device_identifier} @ {device_address}")

            try:
                device_description: str = await service.read_property(
                    device_address, device_identifier, "description"
                )
                _log.debug(f"    description: {device_description}")
            except ErrorRejectAbortNack as err:
                # some devices don't support the "description" property
                device_description = f"Error: {err}"
                _log.error(f"{device_identifier} description error: {err}")

            result.append({
                "i-am-device-identifier": f"{device_identifier}",
                "device-address": f"{device_address}",
                "device-description": device_description,
                "max-apdu-length-accepted": i_am.maxAPDULengthAccepted,
                "segmentation-supported": str(i_am.segmentationSupported),
                "vendor-id": i_am.vendorID,
            })

        return result

    except Exception as e:
        _log.error(f"Exception in perform_who_is: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global args, service

    service = Application.from_args(args)
    _log.debug("lifespan service: %r", service)
    yield


app = FastAPI(lifespan=lifespan)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": str(exc.detail), "data": None},
    )

@app.get("/")
async def hello_world(username: str = Depends(get_current_username)):
    return RedirectResponse("/docs")


@app.get("/bacpypes/config")
async def config(username: str = Depends(get_current_username)):
    global service

    object_list = []
    for obj in service.objectIdentifier.values():
        _log.debug("    - obj: %r", obj)
        object_list.append(sequence_to_json(obj))

    return {"BACpypes": dict(settings), "application": object_list}


@app.get("/bacnet/whois/{device_instance}")
async def who_is(
    device_instance: int = Depends(DeviceInstanceValidator.validate_instance),
    username: str = Depends(get_current_username),
):
    _log.debug("who_is %r device_instance=%r", device_instance)

    result = await perform_who_is(device_instance, device_instance)
    _log.debug(" result - result=%r", result)

    if result:
        success = True
        message = "BACnet WhoIs request successfully invoked"
    else:
        success = False
        message = i_ams

    response_data = {
        "device_instance": device_instance,
        "result": result,
    }

    response = BaseResponse(success=success, message=message, data=response_data)
    return response


@app.get("/bacnet/{device_instance}/{object_identifier}/")
async def read_bacnet_property(
    device_instance: int = Depends(DeviceInstanceValidator.validate_instance),
    object_identifier: str = Path(
        ..., description="Bacpypes3 format for obj id is 'analog-input,2' for example"
    ),
    property_identifier: str = Query(
        "present-value", description="Default prop id of 'present-value' is inserted"
    ),
    username: str = Depends(get_current_username),
):
    try:
        WritePropertyRequest.validate_object_identifier(object_identifier)
        WritePropertyRequest.validate_property_identifier(property_identifier)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    _log.debug(
        " read - %r %r %r", device_instance, object_identifier, property_identifier
    )

    read_result = None
    try:
        read_result = await _read_property(
            device_instance, object_identifier, property_identifier
        )

        if isinstance(read_result, tuple):
            _, encoded_value = read_result
            success = True
            message = "BACnet read request successfully invoked"
        else:
            success = False
            message = read_result
    except Exception as e:
        _log.error(f"Unexpected error during read operation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=read_result)

    response_data = {
        "device_instance": device_instance,
        "object_identifier": object_identifier,
        "property_identifier": property_identifier,
        "read_result": encoded_value,
    }

    response = BaseResponse(success=success, message=message, data=response_data)
    return response


@app.post("/bacnet/write", response_model=BaseResponse)
async def bacnet_write_property(
    request_body: WritePropertyRequest,
    request: Request,
    username: str = Depends(get_current_username),
):
    request = await request.json()
    _log.debug(f"request Parsed BACnet POST data: {request}")

    device_instance = request["device_instance"]
    object_identifier = request["object_identifier"]
    property_identifier = request["property_identifier"]
    value = request["value"]
    priority = request["priority"]

    _log.debug(f" write - Device Instance: {device_instance}")
    _log.debug(f" write - Object Identifier: {object_identifier}")
    _log.debug(f" write - Property Identifier: {property_identifier}")
    _log.debug(f" write - Value: {value}")
    _log.debug(f" write - Priority: {priority}")

    try:
        write_result = await _write_property(
            device_instance=device_instance,
            object_identifier=object_identifier,
            property_identifier=property_identifier,
            value=value,
            priority=priority,
        )

        if write_result is None:
            success = True
            message = "BACnet write request successfully invoked"
        else:
            success = False
            message = write_result
    except Exception as e:
        _log.error(f"Unexpected error during write operation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=write_result)

    response_data = {
        "device_instance": device_instance,
        "object_identifier": object_identifier,
        "property_identifier": property_identifier,
        "written_value": value,
        "priority": priority,
    }

    response = BaseResponse(success=success, message=message, data=response_data)
    return response


@app.post("/bacnet/read-multiple", response_model=BaseResponse)
async def bacnet_read_multiple_properties(
    request_body: ReadMultiplePropertiesRequestWrapper,
    request: Request,
    username: str = Depends(get_current_username),
):
    address = DeviceInstanceValidator.validate_instance(request_body.device_instance)
    _log.debug(f" rpm - for address: {address}")
    _log.debug(f" rpm - with properties: {request_body.requests}")

    # Transform the request data into a list of strings
    args_list: List[str] = []
    for req in request_body.requests:
        args_list.append(req.object_identifier)
        args_list.append(req.property_identifier)

    # Log the transformed list
    _log.debug(f" rpm - Transformed args_list: {args_list}")

    # get information about the device from the cache
    device_info = await service.device_info_cache.get_device_info(address)

    # using the device info, look up the vendor information
    if device_info:
        vendor_info = get_vendor_info(device_info.vendor_identifier)
        bacnet_address = device_info.device_address
    else:
        # do a WhoIs I think
        device_info = await get_device_address(address)
        vendor_info = get_vendor_info(0)
        bacnet_address = device_info

    _log.debug(f" rpm - device_info: {device_info}")
    _log.debug(f" rpm - bacnet_address: {bacnet_address}")

    parameter_list = []
    while args_list:
        # use the vendor information to translate the object identifier,
        # then use the object type portion to look up the object class
        object_identifier = vendor_info.object_identifier(args_list.pop(0))
        object_class = vendor_info.get_object_class(object_identifier[0])
        if not object_class:
            _log.debug(f" rpm - unrecognized object type: {object_identifier}")
            return BaseResponse(
                success=False,
                message=f"BACnet rpm failed - unrecognized object type: {object_identifier}",
                data=None,
            )

        # save this as a parameter
        parameter_list.append(object_identifier)

        property_reference_list = []
        while args_list:
            # use the vendor info to parse the property reference
            property_reference = PropertyReference(
                args_list.pop(0),
                vendor_info=vendor_info,
            )

            # _log.debug(" rpm - property_reference: %r", property_reference)

            if property_reference.propertyIdentifier not in (
                PropertyIdentifier.all,
                PropertyIdentifier.required,
                PropertyIdentifier.optional,
            ):
                property_type = object_class.get_property_type(
                    property_reference.propertyIdentifier
                )
                # _log.debug(" rpm - property_type: %r", property_type)
                _log.debug(
                    " rpm - property_reference.propertyIdentifier: %r",
                    property_reference.propertyIdentifier,
                )
                if not property_type:
                    _log.debug(
                        f" rpm - unrecognized property: {property_reference.propertyIdentifier}"
                    )
                    return BaseResponse(
                        success=False,
                        message=f"BACnet rpm failed - unrecognized property: {property_reference.propertyIdentifier}",
                        data=None,
                    )

            # save this as a parameter
            property_reference_list.append(property_reference)

            # crude check to see if the next thing is an object identifier
            if args_list and ((":" in args_list[0]) or ("," in args_list[0])):
                break

        # save this as a parameter
        parameter_list.append(property_reference_list)

    if not parameter_list:
        _log.debug(" rpm - object identifier expected")
        return BaseResponse(
            success=False,
            message=f"BACnet rpm failed - object identifier expected",
            data=None,
        )

    try:
        response = await service.read_property_multiple(bacnet_address, parameter_list)
    except ErrorRejectAbortNack as err:
        _log.debug(" rpm - exception: %r", err)
        return BaseResponse(
            success=False, message=f"BACnet rpm failed: {err}", data=None
        )

    except ErrorRejectAbortNack as err:
        _log.debug(f"rpm - exception: {err}")
        return BaseResponse(
            success=False, message=f"BACnet rpm failed: {err}", data=None
        )

    rpm_result = []
    try:
        if response:
            for (
                object_identifier,
                property_identifier,
                property_array_index,
                property_value,
            ) in response:
                if property_array_index is not None:
                    _log.debug(f"property_array_index is not None")
                    _log.debug(
                        f" rpm - {object_identifier} {property_identifier}[{property_array_index}] {property_value}"
                    )
                else:
                    _log.debug(
                        f" rpm - {object_identifier} {property_identifier} {property_value}"
                    )
                if isinstance(property_value, ErrorType):
                    _log.debug(
                        f" rpm - {property_value.errorClass}, {property_value.errorCode}"
                    )
                    rpm_result.append(
                        {
                            "object_identifier": f"{object_identifier}",
                            "property_identifier": f"{property_identifier}",
                            "error": f"{property_value.errorClass}, {property_value.errorCode}",
                        }
                    )
                else:
                    rpm_result.append(
                        {
                            "object_identifier": f"{object_identifier}",
                            "property_identifier": f"{property_identifier}",
                            "value": f"{property_value}",
                        }
                    )

        if response:
            success = True
            message = "BACnet rpm successfully invoked"
        else:
            success = False
            message = "BACnet rpm failed"
    except Exception as e:
        _log.error(f"Unexpected error during rpm operation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Unexpected error during rpm operation"
        )

    response_data = {
        "device_instance": request_body.device_instance,
        "requests": rpm_result,
    }

    return BaseResponse(success=success, message=message, data=response_data)


@app.post("/bacnet/whois")
async def who_is_range(
    range_request: DeviceInstanceRange,
    username: str = Depends(get_current_username),
):

    _log.debug(" - who_is range post %r %r", range_request.start_instance, range_request.end_instance)

    result = await perform_who_is(range_request.start_instance, range_request.end_instance)
    _log.debug(" result - result=%r", result)

    if result:
        success = True
        message = "BACnet WhoIs request successfully invoked"
    else:
        success = False
        message = i_ams

    response_data = {
        "result": result,
    }

    response = BaseResponse(success=success, message=message, data=response_data)
    return response
    

@app.get("/bacnet/point-discovery/")
async def point_discovery(
    device_instance: int = Depends(DeviceInstanceValidator.validate_instance)
):
    """
    Read the entire object list from a device at once, or if that fails, read
    the object identifiers one at a time.
    """
    try:
        i_ams = await service.who_is(device_instance, device_instance)
        if not i_ams:
            return

        i_am = i_ams[0]
        if _debug:
            _log.debug("    - i_am: %r", i_am)

        device_address: Address = i_am.pduSource
        device_identifier: ObjectIdentifier = i_am.iAmDeviceIdentifier
        vendor_info = get_vendor_info(i_am.vendorID)

        _log.debug("    - device_address: %r", device_address)
        _log.debug("    - device_identifier: %r", device_identifier)
        _log.debug("    - vendor_info: %r", vendor_info)

        object_list = []
        names_list = []

        # final json response
        details = []

        try:
            object_list = await service.read_property(
                device_address, device_identifier, "object-list"
            )
            _log.debug("object_list - %r", object_list)

        except AbortPDU as err:
            if err.apduAbortRejectReason != AbortReason.segmentationNotSupported:
                _log.error(f"{device_identifier} object-list abort: {err}\n")
                raise HTTPException(status_code=500, detail="Error reading object-list")

        except ErrorRejectAbortNack as err:
            _log.error(f"{device_identifier} object-list error/reject: {err}\n")
            raise HTTPException(status_code=500, detail="ErrorRejectAbortNack reading object-list")

        if isinstance(object_list, str):
            if "no object class" in object_list:
                _log.debug("Empty Object List Will Attempt Reading One By One")
                _log.debug("This may take a minute....")

                try:
                    # Read the length
                    object_list_length = await service.read_property(
                        device_address,
                        device_identifier,
                        "object-list",
                        array_index=0,
                    )

                    # Ensure object_list_length is an integer
                    try:
                        object_list_length = int(object_list_length)
                    except ValueError:
                        _log.error(f"Invalid object list length: {object_list_length}")
                        raise HTTPException(status_code=500, detail="Invalid object list length")

                    _log.debug(f"object_list_length - {object_list_length}")

                    # Read each element individually
                    for i in range(object_list_length):
                        object_identifier = await service.read_property(
                            device_address,
                            device_identifier,
                            "object-list",
                            array_index=i + 1,
                        )
                        object_list.append(object_identifier)

                except ErrorRejectAbortNack as err:
                    _log.error(f"{device_identifier} object-list length error/reject: {err}\n")
                    raise HTTPException(status_code=500, detail="Error reading object-list length")

        # Loop through each object and attempt to tease out the name
        for object_identifier in object_list:
            object_class = vendor_info.get_object_class(object_identifier[0])

            _log.debug("    - object_class: %r", object_class)

            if object_class is None:
                _log.error(f"unknown object type: {object_identifier}\n")
                continue

            _log.debug(f"    {object_identifier}:")

            try:
                property_value = await service.read_property(
                    device_address, object_identifier, "object-name"
                )
                _log.debug(f" {object_identifier}: {property_value}")

                property_value_str = f"{property_value}"
                names_list.append(property_value_str)

            except bacpypes3.errors.InvalidTag as err:
                _log.error(f"Invalid Tag Error on point: {device_identifier}")
                names_list.append("ERROR - Delete this row")

            except ErrorRejectAbortNack as err:
                _log.error(f"{object_identifier} {object_identifier} error: {err}\n")

        _log.debug("    - device_address: %r", device_address)
        _log.debug("    - object_list: %r", object_list)
        _log.debug("    - names_list: %r", names_list)

        

        if names_list:
            success = True
            message = "BACnet point discovery successfully invoked"
            response_data = {
                "device_instance_id": device_instance,
            "point_object_details": [
                {"identifier": f"{obj_type} {id}", "description": name}
                for (obj_type, id), name in zip(object_list, names_list)
                ]
            }
        else:
            success = False
            message = "BACnet point discovery failed"
            response_data = None

    except Exception as e:
        _log.error(f"Unexpected error during point discovery operation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unexpected error during point discovery operation")

    return BaseResponse(success=True, message="Point discovery successful", data=response_data)



async def main() -> None:
    global app, args

    parser = SimpleArgumentParser()
    parser.add_argument(
        "--host",
        help="Host address for the service",
        default="0.0.0.0",
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Port for the service",
        default=5000,
    )
    parser.add_argument(
        "--log-level",
        help="Logging level for uvicorn",
        default="info",
    )
    parser.add_argument(
        "--basic-auth-username",
        help="Basic Auth Username",
        default="admin",
    )
    parser.add_argument(
        "--basic-auth-password",
        help="Basic Auth Password",
        default="secret",
    )
    parser.add_argument(
        "--tls",
        action="store_true",
        help="Enable TLS by using SSL cert and key from the certs directory",
    )
    parser.add_argument(
        "--ssl-certfile",
        type=str,
        help="Path to the SSL certificate file",
        default="./certs/certificate.pem",
    )
    parser.add_argument(
        "--ssl-keyfile",
        type=str,
        help="Path to the SSL key file",
        default="./certs/private.key",
    )

    args = parser.parse_args()
    _log.debug("args: %r", args)

    os.environ["BASIC_AUTH_USERNAME"] = args.basic_auth_username
    os.environ["BASIC_AUTH_PASSWORD"] = args.basic_auth_password

    if args.tls:
        config = uvicorn.Config(
            app=app,
            host=args.host,
            port=args.port,
            log_level=args.log_level,
            ssl_certfile=args.ssl_certfile,
            ssl_keyfile=args.ssl_keyfile,
        )
    else:
        config = uvicorn.Config(
            app=app,
            host=args.host,
            port=args.port,
            log_level=args.log_level,
        )

    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
