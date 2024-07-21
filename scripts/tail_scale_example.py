import requests
import time
from requests.auth import HTTPBasicAuth

# Base URL for the BACnet RPC server
base_url = "http://100.234.23.125:5000"

# BACnet device instances
device_instances = list(range(10, 21))

# Points to read from each device with corrected format and additional descriptions
points = [
    {"object_identifier": "analog-input,1019", "property_identifier": "present-value", "description": "Discharge Air Temperature (DA-T)"},
    {"object_identifier": "analog-input,1106", "property_identifier": "present-value", "description": "Zone Temperature (ZN-T)"},
    {"object_identifier": "analog-output,2014", "property_identifier": "present-value", "description": "Heating Valve Output (HTG-O)"},
    {"object_identifier": "analog-output,2131", "property_identifier": "present-value", "description": "Air Damper Output (DPR-O)"},
    {"object_identifier": "analog-value,1103", "property_identifier": "present-value", "description": "Zone Temperature Setpoint (ZN-SP)"},
    {"object_identifier": "analog-value,3384", "property_identifier": "present-value", "description": "Supply Air Flow Setpoint (SAFLOW-SP)"},
    {"object_identifier": "analog-value,3515", "property_identifier": "present-value", "description": "Supply Air Flow (SA-F)"},
    {"object_identifier": "multi-state-value,3290", "property_identifier": "present-value", "description": "Effective Occupancy (EFF-OCC)"},
]

# Function to read multiple points from a BACnet device
def read_multiple(device_instance):
    url = f"{base_url}/bacnet/read-multiple"
    payload = {
        "device_instance": device_instance,
        "requests": [{"object_identifier": p["object_identifier"], "property_identifier": p["property_identifier"]} for p in points]
    }
    headers = {
        "accept": "application/json",
        "Authorization": "Basic YmVuOmJlbg==",
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=payload, headers=headers, auth=HTTPBasicAuth('ben', 'ben'))
    return response.json()

# Main loop to read points at regular intervals
interval = 60  # Interval in seconds

while True:
    for device_instance in device_instances:
        try:
            result = read_multiple(device_instance)
            if result['success']:
                print(f"Device {device_instance} response: {result}")
                # Extract data and print alongside additional information
                for request, point in zip(result['data']['requests'], points):
                    object_identifier = request['object_identifier']
                    property_identifier = request['property_identifier']
                    value = request['value']
                    description = point['description']
                    print(f"Device Instance: {device_instance}, Object Identifier: {object_identifier}, Property Identifier: {property_identifier}, Value: {value}, Description: {description}")
                    
                    # Pseudo-code for SQL database input
                    # conn = sqlite3.connect('bacnet_data.db')  # Connect to your database
                    # cursor = conn.cursor()
                    # cursor.execute('''
                    #     INSERT INTO bacnet_readings (device_instance, object_identifier, property_identifier, value, description, timestamp)
                    #     VALUES (?, ?, ?, ?, ?, ?)
                    # ''', (device_instance, object_identifier, property_identifier, value, description, time.time()))
                    # conn.commit()
                    # conn.close()
            else:
                print(f"Device {device_instance} error: {result.get('message', 'Unknown error')}")
        except Exception as e:
            print(f"Error reading device {device_instance}: {e}")
    time.sleep(interval)
