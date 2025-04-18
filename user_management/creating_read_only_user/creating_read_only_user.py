from gqlalchemy import Memgraph

memgraph = Memgraph()

memgraph.execute("CREATE (n:Node)")

# First user that is created is always the admin user with all privileges
# After this command, you're no longer able to log in without credentials
memgraph.execute("CREATE USER admin IDENTIFIED BY 'test'")


# Create a readonly role with read privileges only
memgraph.execute("CREATE ROLE readonly")
# Grant privilege to execute the MATCH clause
memgraph.execute("GRANT MATCH TO readonly")
# Grant visibility on all node labels
memgraph.execute("GRANT READ ON LABELS * TO readonly")
# Grant visibility on all edge types
memgraph.execute("GRANT READ ON EDGE_TYPES * TO readonly")


memgraph.execute("CREATE USER readonly_user IDENTIFIED BY 'test'")
# Assign the readonly role to the new user
memgraph.execute("SET ROLE FOR readonly_user TO readonly")


# By default, user will be able to log into the default database 'memgraph'
print("Database privileges for admin:")
print(list(memgraph.execute_and_fetch("SHOW DATABASE PRIVILEGES FOR admin")))
print()

print("General privileges for admin:")
print(list(memgraph.execute_and_fetch("SHOW PRIVILEGES FOR admin")))
print()

print("Database privileges for read only user:")
print(list(memgraph.execute_and_fetch("SHOW DATABASE PRIVILEGES FOR readonly_user")))
print()

print("General privileges for read only user:")
print(list(memgraph.execute_and_fetch("SHOW PRIVILEGES FOR readonly_user")))
print()

readonly_connection = Memgraph(username="readonly_user", password="test")
print(list(readonly_connection.execute_and_fetch("MATCH (n) RETURN n")))


try:
    # This will not pass as user does not have permission
    readonly_connection.execute("CREATE (n)")
except Exception as e:
    print(str(e))
