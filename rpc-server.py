"""
FastAPI based simple RPC server

In addition to the BACpypes3 package, also install these packages:

    fastapi
    uvicorn[standard]

This application takes all of the usual BACpypes command line arguments and
adds a `--host` and `--port` for the web service, and `--log-level` for
uvicorn debugging.

$ python rpc-server.py --host 0.0.0.0 --debug

log into swagger UI on:
http://192.168.0.102:8000/docs
"""
from __future__ import annotations

import asyncio
import math
import re
import argparse
import uvicorn
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse

from bacpypes3.debugging import ModuleLogger
from bacpypes3.argparse import SimpleArgumentParser

from bacpypes3.pdu import Address, GlobalBroadcast
from bacpypes3.primitivedata import Atomic, ObjectIdentifier, Null
from bacpypes3.constructeddata import Sequence, AnyAtomic, Array, List
from bacpypes3.apdu import ErrorRejectAbortNack
from bacpypes3.app import Application

# for serializing the configuration
from bacpypes3.settings import settings
from bacpypes3.json.util import (
    atomic_encode,
    sequence_to_json,
    extendedlist_to_json_list,
)

from pydantic import BaseModel, conint, validator
from typing import Union, Optional

class BaseResponse(BaseModel):
    success: bool
    message: str
    data: dict = None

class WritePropertyRequest(BaseModel):
    device_instance: int
    object_identifier: str
    property_identifier: str
    value: Union[float, int, str]
    priority: Optional[conint(ge=1, le=16)] = None

    @validator('property_identifier')
    def validate_property_identifier(cls, v):
        if not re.match(r"^([A-Za-z-]+)(?:\[([0-9]+)\])?$", v):
            raise ValueError("property_identifier is invalid")
        return v

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# globals
args: argparse.Namespace
service: Application


@asynccontextmanager
async def lifespan(app: FastAPI):
    global args, service

    # build an application
    service = Application.from_args(args)
    if _debug:
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
async def hello_world():
    """
    Redirect to the documentation.
    """
    return RedirectResponse("/docs")

@app.get("/bacpypes/config")
async def config():
    """
    Return the configuration as JSON.
    """
    _log.debug("config")
    global service

    object_list = []
    for obj in service.objectIdentifier.values():
        _log.debug("    - obj: %r", obj)
        object_list.append(sequence_to_json(obj))

    return {"BACpypes": dict(settings), "application": object_list}

@app.get("/bacnet/whois/{device_instance}")
async def who_is(device_instance: int, address: Optional[str] = None):
    """
    Send out a Who-Is request and return the I-Am messages.
    """
    _log.debug("who_is %r address=%r", device_instance, address)
    global service

    # if the address is None in the who_is() call it defaults to a global
    # broadcast but it's nicer to be explicit here
    destination: Address
    if address:
        destination = Address(address)
    else:
        destination = GlobalBroadcast()
    if _debug:
        _log.debug("    - destination: %r", destination)

    # returns a list, there should be only one
    i_ams = await service.who_is(device_instance, device_instance, destination)

    result = []
    for i_am in i_ams:
        if _debug:
            _log.debug("    - i_am: %r", i_am)
        result.append(sequence_to_json(i_am))

    return result

@app.get("/bacnet/{device_instance}/{object_identifier}")
@app.get("/bacnet/{device_instance}/{object_identifier}/{property_identifier}")
async def read_bacnet_property(device_instance: int, object_identifier: str, property_identifier: str = None):
    """
    Read a BACnet property from an object.
    """
    if _debug:
        _log.debug("read_bacnet_property %r %r %r", device_instance, object_identifier, property_identifier)

    # Set property_identifier to "present-value" if it's not provided
    if property_identifier is None:
        property_identifier = "present-value"

    read_result = None
    encoded_value = None
    try:
        read_result = await _read_property(device_instance, object_identifier, property_identifier)

        if isinstance(read_result, tuple):
            _, encoded_value = read_result
            success = True
            message = "BACnet read request successfully invoked"
        else:
            success = False
            message = read_result  # Some bacpypes error string

    except Exception as e:  # Catch-all for unexpected errors
        _log.error(f"Unexpected error during read operation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=read_result
        )

    # Constructing the response data
    response_data = {
        "device_instance": device_instance,
        "object_identifier": object_identifier,
        "property_identifier": property_identifier,
        "read_result": encoded_value,
    }

    # Constructing and returning the response
    response = BaseResponse(
        success=success,
        message=message,
        data=response_data
    )
    return response


@app.post("/bacnet/write", response_model=BaseResponse)
async def bacnet_write_property(request: WritePropertyRequest):
    if _debug:
        _log.debug(f"Parsed BACnet POST data: {request.model_dump_json()}")

    # Extracting the request data
    device_instance = request.device_instance
    object_identifier = request.object_identifier
    property_identifier = request.property_identifier
    value = request.value
    priority = request.priority

    if _debug:
        _log.debug(f"Device Instance: {device_instance}")
        _log.debug(f"Object Identifier: {object_identifier}")
        _log.debug(f"Property Identifier: {property_identifier}")
        _log.debug(f"Value: {value}")
        _log.debug(f"Priority: {priority}")

    write_result = None
    try:
        write_result = await _write_property(
            device_instance=device_instance,
            object_identifier=object_identifier,
            property_identifier=property_identifier,
            value=value,
            priority=priority
        )

        if write_result is None:
            success = True
            message = "BACnet write request successfully invoked"
        else:
            success = False
            message = write_result #some bacpypes error string
    except Exception as e:  # Catch-all for unexpected errors
        _log.error(f"Unexpected error during write operation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail= write_result
        )

    # Constructing the response data
    response_data = {
        "device_instance": device_instance,
        "object_identifier": object_identifier,
        "property_identifier": property_identifier,
        "written_value": value,
        "priority": priority
    }

    # Constructing and returning the response
    response = BaseResponse(
        success=success,
        message=message,
        data=response_data
    )
    return response


def nan_or_inf_check(encoded_value):
        # check for NaN
    if isinstance(encoded_value, float) and math.isnan(encoded_value):
        return "NaN"
    # Check for positive infinity
    elif isinstance(encoded_value, float) and math.isinf(encoded_value) and encoded_value > 0:
        return "Inf"
    # Check for negative infinity
    elif isinstance(encoded_value, float) and math.isinf(encoded_value) and encoded_value < 0:
        return "-Inf"
    else:
        return encoded_value


async def _read_property(
    device_instance: int, object_identifier: str, property_identifier: str
):
    """
    Read a property from an object.
    """
    _log.debug("_read_property %r %r", device_instance, object_identifier)
    global service

    device_address = await get_device_address(device_instance)

    try:
        property_value = await service.read_property(
            device_address, ObjectIdentifier(object_identifier), property_identifier
        )
        if _debug:
            _log.debug("    - property_value: %r", property_value)
    except ErrorRejectAbortNack as err:
        if _debug:
            _log.error("    - exception: %r", err)
        return f" BACnet error/reject/abort: {err}"
    except ValueError as ve:
        if _debug:
            _log.error("    - exception: %r", ve)
        return f" BACnet value error: {ve}"

    if isinstance(property_value, AnyAtomic):
        if _debug:
            _log.debug("    - schedule objects")
        property_value = property_value.get_value()

    if isinstance(property_value, Atomic):
        encoded_value = atomic_encode(property_value)
    elif isinstance(property_value, Sequence):
        encoded_value = sequence_to_json(property_value)
    elif isinstance(property_value, (Array, List)):
        encoded_value = extendedlist_to_json_list(property_value)
    else:
        return f"JSON encoding: {property_value}"
    if _debug:
        _log.debug("    - encoded_value: %r", encoded_value)
        _log.debug("    - type encoded_value ", type(encoded_value))

    encoded_value = nan_or_inf_check(encoded_value)
    return property_identifier, encoded_value


async def _write_property(device_instance: int, object_identifier: ObjectIdentifier,
                          property_identifier: str, value: str, priority: int = -1):
    """
    Write a property from an object.
    """
        
    device_address = await get_device_address(device_instance)
    property_identifier, property_array_index = parse_property_identifier(property_identifier)
    if value == "null":
        if priority is None:
            return " BACnet Error, null is only for releasing overrides and requires a priority to release that override"
        value = Null(())
    
    try:
        object_identifier = ObjectIdentifier(object_identifier)
    except ErrorRejectAbortNack as err:
        _log.error("    - exception on point ObjectIdentifier conversion: %r", err)
        return str(err)
    
    try:
        response = await service.write_property(
            device_address, object_identifier, property_identifier, value,
            property_array_index, priority
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
        _log.debug("    - cached address: %r", device_address)
    else:
        i_ams = await service.who_is(device_instance, device_instance)
        if not i_ams:
            return f"Device not found: {device_instance}"
        if len(i_ams) > 1:
            return f"Multiple devices found: {device_instance}"
        device_address = i_ams[0].pduSource
        _log.debug("    - i-am response: %r", device_address)
    return device_address


def parse_property_identifier(property_identifier: str):
    property_index_re = re.compile(r"^([A-Za-z-]+)(?:\[([0-9]+)\])?$")
    property_index_match = property_index_re.match(property_identifier)
    if not property_index_match:
        return "Property specification incorrect"
    property_identifier, property_array_index = property_index_match.groups()
    property_array_index = int(property_array_index) if property_array_index is not None else None
    return property_identifier, property_array_index

async def main() -> None:
    global app, args

    parser = SimpleArgumentParser()
    parser.add_argument(
        "--host",
        help="host address for service",
        default="0.0.0.0",
    )
    parser.add_argument(
        "--port",
        type=int,
        help="host address for service",
        default=8000,
    )
    parser.add_argument(
        "--log-level",
        help="logging level",
        default="info",
    )
    args = parser.parse_args()
    if _debug:
        _log.debug("args: %r", args)

    config = uvicorn.Config(
        app,
        host=args.host,
        port=args.port,
        log_level=args.log_level,
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())