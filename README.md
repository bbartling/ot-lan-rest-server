# bacpypes3RcpServer


This dedicated RPC server BACnet app with a web UI to read and write BACnet data to a building automation system (BAS) or some sort of BACnet device. This has been tested on a Raspberry Pi 3 Model B+ running [Armbian Jammy Linux](https://www.armbian.com/rpi4b/) with a CLI interface. Supports tls and Basic Auth through the Fast API web framework. This Linux app is meant to on a intranet or edge environment behind the firewall along side typical operations technology (OT) inside the building.

## Setup Python packages use virtual environment if desired.
```bash
$ python -m pip install bacpypes3 ifaddr fastapi uvicorn

```

### Example args to run app on http with setting custom `host`, `port`, and `debug` mode.
```bash
$ python rpc-server.py --host 0.0.0.0 --port 8080  --debug
```

### Example args to run app on http with setting Basic Auth username for the app of `myusername` and password of `mypassword`. Default app username and pass is `admin` and `secret` which should be changed for security purposes.

```bash
$ python rpc-server.py --basic-auth-username=myusername --basic-auth-password=mypassword
```

If running your app on http without tls support log into swagger UI on:
http://192.168.0.102:8000/docs


## Optional TLS support for the Fast API web app for added security to ecprypte http traffic only, not BACnet...
Generate certs with running the bash script inside the `scripts` directory. Step through the Q/A process for generating the self signed certs about inputing country code, organization, and contact info.

```bash
$ ./scripts/generate_certs.sh
```

### Example arg to run app with transport layer security (TLS)
```bash
$ python rpc-server.py --tls
```

If running your app with tls support log into the Fast API swagger UI:
https://192.168.0.102:5000/docs



Proceed to then enter your credentials for the `Authorize` in the Swagger UI.


## tutorial via Swagger UI

When the app starts successfully dial into the built in Swagger UI feature of Fast API which can be used to test various BACnet commands.

![Alt text](/images/swagger_home.JPG)


Test if the BACnet device responds to a `whois` for the devices BACnet instance ID.
![Alt text](/images/who_is.JPG)

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

![Alt text](/images/read_prop_pv1.JPG)

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

![Alt text](/images/read_prop.JPG)

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
![Alt text](/images/write_req1.JPG)

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

![Alt text](/images/write_req2.JPG)

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
* whois POST request for a range of instance ID's
* read multiple request
* point discovery
* who is router-to-network
* read point proirity array
* read range for BACnet devices that support trend log data