from gqlalchemy import Memgraph
import random
import time

# Establish a connection to Memgraph
memgraph = Memgraph(host='127.0.0.1', port=7687)

# Clean up any existing data
memgraph.execute("MATCH (n) DETACH DELETE n;")
memgraph.execute("DROP INDEX ON :Person(address.country);")

# Sample data for addresses
countries = ["USA", "Canada", "UK", "Germany", "France", "Italy", "Spain", "Australia", "Japan", "Brazil"]
cities = ["New York", "Toronto", "London", "Berlin", "Paris", "Rome", "Madrid", "Sydney", "Tokyo", "Rio de Janeiro"]
streets = ["Main St", "Oak Ave", "Pine Rd", "Maple Dr", "Elm St", "Cedar Ave", "Birch Rd", "Spruce Dr", "Willow St", "Ash Ave"]

# Create 2000 Person nodes with nested address
for i in range(2000):
    name = f"Person_{i}"
    address = {
        'street': f"{random.randint(1,999)} {random.choice(streets)}",
        'city': random.choice(cities),
        'country': random.choice(countries)
    }
    query = f"""
    CREATE (:Person {{name: '{name}', address: {{street: '{address['street']}', city: '{address['city']}', country: '{address['country']}'}}}})
    """
    memgraph.execute(query)

# Query to time (e.g., find all people in the UK)
country_to_query = "UK"
query = f"""
MATCH (p:Person)
WHERE p.address.country = '{country_to_query}'
RETURN p
"""

start = time.time()
results = list(memgraph.execute_and_fetch(query))
time_no_index = time.time() - start
print(f"Query time without index: {time_no_index:.4f} seconds. Results: {len(results)}")

# Create nested index
memgraph.execute("CREATE INDEX ON :Person(address.country);")

# Wait a moment for index to be created
import time as t
t.sleep(2)

start = time.time()
results = list(memgraph.execute_and_fetch(query))
time_with_index = time.time() - start
print(f"Query time with index: {time_with_index:.4f} seconds. Results: {len(results)}") 