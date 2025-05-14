import time
from gqlalchemy import Memgraph

# Connect to Memgraph
memgraph = Memgraph()

# Enable TTL to run every second
try:
    memgraph.execute("ENABLE TTL EVERY '1s'")
except Exception as e:
    # TTL probably already enabled
    pass

# Create a node with TTL set to expire in 5 seconds
create_query = """
CREATE (:TTL {name: 'temp_node', ttl: timestamp() + 5000000})
"""
memgraph.execute(create_query)
print("Node created with TTL set to expire in 5 seconds.")

# Verify the node exists
result = list(memgraph.execute_and_fetch("MATCH (n:TTL {name: 'temp_node'}) RETURN n"))
if result:
    print("Node exists immediately after creation.")
else:
    # This should not happen
    raise Exception("Node not found immediately after creation.")

# Wait for 10 seconds to allow TTL to expire
print("Waiting for 10 seconds to allow TTL to expire...")
time.sleep(10)

# Check if the node has been deleted
result = list(memgraph.execute_and_fetch("MATCH (n:TTL {name: 'temp_node'}) RETURN n"))
if result:
    # This should not happen and node should be deleted
    raise Exception("Node still exists after TTL expiration.")
else:
    print("Node has been deleted after TTL expiration.")
