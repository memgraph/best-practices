import requests

# GraphQL endpoint
GRAPHQL_URL = 'http://localhost:4000/graphql'

def execute_query(query, variables=None):
    headers = {
        'Content-Type': 'application/json',
    }
    
    payload = {
        'query': query,
        'variables': variables or {}
    }
    
    try:
        response = requests.post(GRAPHQL_URL, headers=headers, json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes
        resp_json = response.json()
        if 'errors' in resp_json:
            print(f"GraphQL Errors: {resp_json['errors']}")
            exit(1)
        return resp_json
    except requests.exceptions.RequestException as e:
        print(f"Error executing query: {str(e)}")
        exit(1)

def query_buildings():
    print("Querying buildings...")
    query = """
    query {
        buildings {
            id
            name
            address
            totalEnergyConsumption
            devices {
                name
                type
                powerConsumption
            }
            meters {
                serialNumber
                type
            }
        }
    }
    """
    
    result = execute_query(query)
    if result and 'data' in result:
        print("\nBuildings Query Result:")
        for building in result['data']['buildings']:
            print(f"\nBuilding: {building['name']}")
            print(f"Address: {building['address']}")
            print(f"Total Energy Consumption: {building['totalEnergyConsumption']}")
            print("\nDevices:")
            for device in building['devices']:
                print(f"- {device['name']} ({device['type']}): {device['powerConsumption']} kW")
            print("\nMeters:")
            for meter in building['meters']:
                print(f"- {meter['serialNumber']} ({meter['type']})")
    print("Done!")

def query_devices_with_readings():
    print("Querying devices with readings...")
    query = """
    query {
        devices {
            id
            name
            type
            powerConsumption
            status
            readings {
                value
                unit
            }
        }
    }
    """
    
    result = execute_query(query)
    if result and 'data' in result:
        print("\nDevices with Readings Query Result:")
        for device in result['data']['devices']:
            print(f"\nDevice: {device['name']}")
            print(f"Type: {device['type']}")
            print(f"Power Consumption: {device['powerConsumption']} kW")
            print(f"Status: {device['status']}")
            print("Readings:")
            for reading in device['readings']:
                print(f"- {reading['value']} {reading['unit']}")
    print("Done!")

if __name__ == "__main__":
    print("Querying GraphQL server...")
    query_buildings()
    query_devices_with_readings()
