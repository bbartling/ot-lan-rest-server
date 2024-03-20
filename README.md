# bacpypes3RcpServer

This is some experimentation with the sample app from the bacpypes3 repo `samples/rpc-server.py`.
https://github.com/JoelBender/BACpypes3/blob/main/samples/rpc-server.py


This dedicated RPC server app has been tested on a Raspberry Pi 3 Model B+ running [Armbian Jammy Linux](https://www.armbian.com/rpi4b/) with a CLI interface. Supports tls and Basic Auth through the Fast API interface.

## setup
```bash
$ python -m pip install bacpypes3 ifaddr fastapi uvicorn

```

## Example args to run app on http with setting custom `host`, `port`, and `debug` mode.
```bash
$ python rpc-server.py --host 0.0.0.0 --port 8080  --debug
```

## Example args to run app on http with setting Basic Auth username and password.
```bash
$ python rpc-server.py --basic-auth-username=myusername --basic-auth-password=mypassword
```

## Example arg to run app with transport layer security (TLS)
Generate certs with running the bash script inside the `scripts` directory.

```bash
$ ./scripts/generate_certs.sh
```

Step through the Q/A process for generating the self signed certs about inputing country code, organization, and contact info.

```bash
$ python rpc-server.py --tls
```

## tutorial via Swagger

When the app starts successfully dial into the built in Swagger UI feature of Fast API which can be used to test various BACnet commands.

![Alt text](/swagger_home.JPG)


Test if the BACnet device responds to a `whois` for the devices BACnet instance ID.
![Alt text](/who_is.JPG)

If successful should return:
```bash
[
  {
    "i-am-device-identifier": "device,201201",
    "max-apdu-length-accepted": 286,
    "segmentation-supported": "no-segmentation",
    "vendor-id": 11
  }
]
```

Read request to device `201201 analog-value 301 present-value` which is a temperature sensor.

![Alt text](/read_prop_pv1.JPG)

If successful should return:
```bash
{
  "success": true,
  "message": "BACnet read request successfully invoked",
  "data": {
    "device_instance": 201201,
    "object_identifier": "analog-input,2",
    "property_identifier": "present-value",
    "read_result": 69.42999267578125
  }
}

```

Read property of a different property_identifier which can be unique to the BACnet device. See bacpypes3 repo basetypes.py for more info:
https://github.com/JoelBender/BACpypes3/blob/main/bacpypes3/basetypes.py

![Alt text](/read_prop.JPG)

If successful should return:
```bash
{
  "success": true,
  "message": "BACnet read request successfully invoked",
  "data": {
    "device_instance": 201201,
    "object_identifier": "analog-input,2",
    "property_identifier": "out-of-service",
    "read_result": false
  }
}

```

Write request to device `201201 analog-value 301 present-value` for a value of `10` on BACnet priority `10`.
![Alt text](/write_req1.JPG)

If successful should return:
```bash
{
  "success": true,
  "message": "BACnet write request successfully invoked",
  "data": {
    "device_instance": 201201,
    "object_identifier": "analog-value,301",
    "property_identifier": "present-value",
    "written_value": 10,
    "priority": 10
  }
}
```

Release an override by passing in the value of `null`. 

![Alt text](/write_req2.JPG)

If successful should return:
```bash
{
  "success": true,
  "message": "BACnet write request successfully invoked",
  "data": {
    "device_instance": 201201,
    "object_identifier": "analog-value,301",
    "property_identifier": "present-value",
    "written_value": "null",
    "priority": 10
  }
}
```

TODO on implementing future:
* whois request for a range of instance ID's
* read multiple request
* point discovery
* who is router-to-network
* read point proirity array