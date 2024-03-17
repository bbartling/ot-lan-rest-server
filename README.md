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