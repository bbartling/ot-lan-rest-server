# bacpypes3RcpServer

This is some experimentation with the sample app from the bacpypes3 repo `samples/rpc-server.py`.
https://github.com/JoelBender/BACpypes3/blob/main/samples/rpc-server.py


This dedicated RPC server app has been tested on a Raspberry Pi 3 Model B+ running [Armbian Jammy Linux](https://www.armbian.com/rpi4b/) with a CLI interface. The device is outfitted with 4 GB of RAM and 16 GB of storage on an SD card. It's ideally suited for deployment within the intranet or LAN of buildings to facilitate interactions with BACnet control systems. This enables IoT frameworks or Building Automation Systems (BAS) to seamlessly interface with the RPC app, allowing for efficient reading or writing of data.

## setup
```bash
$ python -m pip install bacpypes3 ifaddr fastapi uvicorn

```

## run app
```bash
$ python rpc-server.py --host 0.0.0.0 --port 8080  --debug
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
    "property_identifier": "out-of-service",
    "read_result": false
}

```

Read property of a different property_identifier which can be unique to the BACnet device. TODO see bacpypes3 folder...

![Alt text](/read_prop.JPG)

If successful should return:
```bash
{
  "success": false,
  "message": "property: write-access-denied",
  "data": {
    "device_instance": 201201,
    "object_identifier": "analog-value,300",
    "property_identifier": "present-value",
    "written_value": 10,
    "priority": 10
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
```

TODO on implementing future:
* whois request for a range of instance ID's
* read multiple request
* point discovery
* who is router-to-network
* read point proirity array