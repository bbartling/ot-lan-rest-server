"""
FastAPI based simple RPC server

In addition to the BACpypes3 package, also install these packages:

    fastapi
    uvicorn[standard]

This application takes all of the usual BACpypes command line arguments and
adds a `--host` and `--port` for the web service, and `--log-level` for
uvicorn debugging.

Run on default args
$ python app/rpc-server.py --tls --basic-auth-username=me --basic-auth-password=1234 --debug

Dont forget to make certs with the bash script and when browsing into the app
make sure you are browing is on the URL https if using the -tls arg

"""
from __future__ import annotations

import asyncio
import os
import math
import re
import argparse
import uvicorn
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Query, Depends, status, Path
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

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

from models import BaseResponse, WritePropertyRequest

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# globals
args: argparse.Namespace
service: Application


def get_current_username(credentials: HTTPBasicCredentials = Depends(HTTPBasic())):
    correct_username = os.getenv("BASIC_AUTH_USERNAME", "default_username")
    correct_password = os.getenv("BASIC_AUTH_PASSWORD", "default_password")

    if credentials.username == correct_username and credentials.password == correct_password:
        return credentials.username
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )


def nan_or_inf_check(encoded_value):
    if isinstance(encoded_value, float):
        if math.isnan(encoded_value):
            return "NaN"
        elif math.isinf(encoded_value):
            return "Inf" if encoded_value > 0 else "-Inf"
    return encoded_value


async def _read_property(device_instance: int, object_identifier: str, property_identifier: str):
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


async def _write_property(device_instance: int, object_identifier: ObjectIdentifier,
                          property_identifier: str, value: str, priority: int = -1):
    _log.debug(f" Write Prop Device Instance: {device_instance}")
    _log.debug(f" Write Prop Object Identifier: {object_identifier}")
    _log.debug(f" Write Prop Property Identifier: {property_identifier}")
    _log.debug(f" Write Prop Value: {value}")
    _log.debug(f" Write Prop Value Type {type(value)}")
    _log.debug(f" Write Prop Priority: {priority}")

    device_address = await get_device_address(device_instance)
    property_identifier, property_array_index = parse_property_identifier(property_identifier)
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


async def validate_object_identifier(
    object_identifier: str = Path(..., description="Bacpypes3 format for obj id is 'analog-input,2' for example")
):
    try:
        WritePropertyRequest.validate_object_identifier(object_identifier)
        return object_identifier
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

async def validate_property_identifier(property_identifier: str = Query("present-value", description="Default prop id of 'present-value' is inserted")):
    try:
        if property_identifier:
            WritePropertyRequest.validate_property_identifier(property_identifier)
        return property_identifier
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def validate_device_instance(device_instance: int = Path(..., ge=0, le=4194303, description="The device instance ID like '201201' for example")):
    return device_instance


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
    _log.debug("config")
    global service

    object_list = []
    for obj in service.objectIdentifier.values():
        _log.debug("    - obj: %r", obj)
        object_list.append(sequence_to_json(obj))

    return {"BACpypes": dict(settings), "application": object_list}


@app.get("/bacnet/whois/{device_instance}")
async def who_is(device_instance: int = Depends(validate_device_instance),
                 address: Optional[str] = None, 
                 username: str = Depends(get_current_username)):
    _log.debug("who_is %r address=%r", device_instance, address)
    global service

    destination: Address = Address(address) if address else GlobalBroadcast()
    _log.debug("    - destination: %r", destination)

    i_ams = await service.who_is(device_instance, device_instance, destination)

    result = [sequence_to_json(i_am) for i_am in i_ams]
    return result


@app.get("/bacnet/{device_instance}/{object_identifier}/")
async def read_bacnet_property(
    device_instance: int = Depends(validate_device_instance),
    object_identifier: str = Depends(validate_object_identifier),
    property_identifier: str = Depends(validate_property_identifier), 
    username: str = Depends(get_current_username)
):
    _log.debug("read_bacnet_property %r %r %r", device_instance, object_identifier, property_identifier)

    read_result = None
    try:
        read_result = await _read_property(device_instance, object_identifier, property_identifier)

        if isinstance(read_result, tuple):
            _, encoded_value = read_result
            success = True
            message = "BACnet read request successfully invoked"
        else:
            success = False
            message = read_result
    except Exception as e:
        _log.error(f"Unexpected error during read operation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=read_result
        )

    response_data = {
        "device_instance": device_instance,
        "object_identifier": object_identifier,
        "property_identifier": property_identifier,
        "read_result": encoded_value,
    }

    response = BaseResponse(
        success=success,
        message=message,
        data=response_data
    )
    return response


@app.post("/bacnet/write", response_model=BaseResponse)
async def bacnet_write_property(request_body: WritePropertyRequest, request: Request, username: str = Depends(get_current_username)):
    request = await request.json()
    _log.debug(f"request Parsed BACnet POST data: {request}")

    device_instance = request['device_instance']
    object_identifier = request['object_identifier']
    property_identifier = request['property_identifier']
    value = request['value']
    priority = request['priority']

    _log.debug(f"Request Device Instance: {device_instance}")
    _log.debug(f"Request Object Identifier: {object_identifier}")
    _log.debug(f"Request Property Identifier: {property_identifier}")
    _log.debug(f"Request Value: {value}")
    _log.debug(f"Request Priority: {priority}")

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
            message = write_result
    except Exception as e:
        _log.error(f"Unexpected error during write operation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=write_result
        )

    response_data = {
        "device_instance": device_instance,
        "object_identifier": object_identifier,
        "property_identifier": property_identifier,
        "written_value": value,
        "priority": priority
    }

    response = BaseResponse(
        success=success,
        message=message,
        data=response_data
    )
    return response


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
        default="./certs/certificate.pem"
    )
    parser.add_argument(
        "--ssl-keyfile",
        type=str,
        help="Path to the SSL key file",
        default="./certs/private.key"
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
