from gqlalchemy import Memgraph
import os

# Connect to Memgraph
memgraph = Memgraph("localhost", 7687)

def ingest_sample_data():
    try:
        # Clean data between multiple runs
        memgraph.execute("STORAGE MODE IN_MEMORY_ANALYTICAL")
        memgraph.execute("DROP GRAPH")

        # Create buildings
        memgraph.execute("CREATE (b1:Building {id: 1, name: 'Office Building A', address: '123 Main St', totalEnergyConsumption: 1500.0})")
        memgraph.execute("CREATE (b2:Building {id: 2,name: 'Office Building B', address: '456 Oak Ave', totalEnergyConsumption: 2000.0})")

        # Create devices
        memgraph.execute("CREATE (d1:Device {id: 1,name: 'HVAC System 1', type: 'HVAC', powerConsumption: 500.0, status: 'active'})")
        memgraph.execute("CREATE (d2:Device {id: 2, name: 'Lighting System 1', type: 'Lighting', powerConsumption: 200.0, status: 'active'})")

        # Create meters
        memgraph.execute("CREATE (m1:Meter {id: 1, serialNumber: 'MTR001', type: 'Electric'})")
        memgraph.execute("CREATE (m2:Meter {id: 2, serialNumber: 'MTR002', type: 'Water'})")

        # Create readings
        memgraph.execute("CREATE (r1:Reading {id: 1, value: 450.0, unit: 'kWh'})")
        memgraph.execute("CREATE (r2:Reading {id: 2, value: 180.0, unit: 'kWh'})")

        # Create relationships
        memgraph.execute("MATCH (b1:Building {name: 'Office Building A'}), (d1:Device {name: 'HVAC System 1'}) CREATE (b1)-[:HAS_DEVICE]->(d1)")
        memgraph.execute("MATCH (b1:Building {name: 'Office Building A'}), (d2:Device {name: 'Lighting System 1'}) CREATE (b1)-[:HAS_DEVICE]->(d2)")
        memgraph.execute("MATCH (b1:Building {name: 'Office Building A'}), (m1:Meter {serialNumber: 'MTR001'}) CREATE (b1)-[:HAS_METER]->(m1)")
        memgraph.execute("MATCH (b2:Building {name: 'Office Building B'}), (m2:Meter {serialNumber: 'MTR002'}) CREATE (b2)-[:HAS_METER]->(m2)")
        memgraph.execute("MATCH (d1:Device {name: 'HVAC System 1'}), (r1:Reading {value: 450.0}) CREATE (d1)-[:HAS_READING]->(r1)")
        memgraph.execute("MATCH (d2:Device {name: 'Lighting System 1'}), (r2:Reading {value: 180.0}) CREATE (d2)-[:HAS_READING]->(r2)")

        print("Sample data ingested successfully!")

    except Exception as e:
        print(f"Error ingesting data: {str(e)}")

if __name__ == "__main__":
    ingest_sample_data() 