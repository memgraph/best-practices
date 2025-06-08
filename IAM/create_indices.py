from sqlalchemy import create_engine, text
from gqlalchemy import Memgraph
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Database configuration
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv('DB_PASS', 'postgres')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_NAME = os.getenv('DB_NAME', 'iam_demo')
MEMGRAPH_HOST = os.getenv('MEMGRAPH_HOST', 'localhost')
MEMGRAPH_PORT = int(os.getenv('MEMGRAPH_PORT', '7687'))

def create_postgresql_indices():
    """Create indices in PostgreSQL for better JOIN performance"""
    print("Creating PostgreSQL indices...")
    
    engine = create_engine(f'postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}')
    
    # List of index creation statements
    index_statements = [
        # Primary key indices (automatically created by PostgreSQL)
        
        # User-Group relationship indices
        "CREATE INDEX IF NOT EXISTS idx_user_groups_user_id ON user_groups(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_user_groups_group_id ON user_groups(group_id)",
        
        # Group-Role relationship indices
        "CREATE INDEX IF NOT EXISTS idx_group_roles_group_id ON group_roles(group_id)",
        "CREATE INDEX IF NOT EXISTS idx_group_roles_role_id ON group_roles(role_id)",
        
        # Role-App relationship indices
        "CREATE INDEX IF NOT EXISTS idx_role_apps_role_id ON role_apps(role_id)",
        "CREATE INDEX IF NOT EXISTS idx_role_apps_app_id ON role_apps(app_id)",
        
        # App-Permission relationship indices
        "CREATE INDEX IF NOT EXISTS idx_app_permissions_app_id ON app_permissions(app_id)",
        "CREATE INDEX IF NOT EXISTS idx_app_permissions_permission_id ON app_permissions(permission_id)",
        
        # Name indices for faster lookups
        "CREATE INDEX IF NOT EXISTS idx_users_name ON users(name)",
        "CREATE INDEX IF NOT EXISTS idx_groups_name ON groups(name)",
        "CREATE INDEX IF NOT EXISTS idx_roles_name ON roles(name)",
        "CREATE INDEX IF NOT EXISTS idx_apps_name ON apps(name)",
        "CREATE INDEX IF NOT EXISTS idx_permissions_name ON permissions(name)"
    ]
    
    with engine.connect() as connection:
        for stmt in index_statements:
            try:
                connection.execute(text(stmt))
                print(f"✓ Created index: {stmt}")
            except Exception as e:
                print(f"✗ Error creating index: {stmt}")
                print(f"  Error: {str(e)}")
        
        connection.commit()
    
    print("PostgreSQL indices created successfully!")

def create_memgraph_indices():
    """Create indices in Memgraph for better query performance"""
    print("\nCreating Memgraph indices...")
    
    memgraph = Memgraph(host=MEMGRAPH_HOST, port=MEMGRAPH_PORT)
    
    # List of index creation statements
    index_statements = [
        # Node property indices
        "CREATE INDEX ON :User(id)",
        "CREATE INDEX ON :User(name)",
        "CREATE INDEX ON :Group(name)",
        "CREATE INDEX ON :Role(name)",
        "CREATE INDEX ON :App(name)",
        "CREATE INDEX ON :Permission(name)"
    ]
    
    for stmt in index_statements:
        try:
            memgraph.execute(stmt)
            print(f"✓ Created index: {stmt}")
        except Exception as e:
            print(f"✗ Error creating index: {stmt}")
            print(f"  Error: {str(e)}")
    
    print("Memgraph indices created successfully!")

def verify_postgresql_indices():
    """Verify that PostgreSQL indices were created"""
    print("\nVerifying PostgreSQL indices...")
    
    engine = create_engine(f'postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}')
    
    query = """
    SELECT 
        schemaname as schema,
        tablename as table,
        indexname as index,
        indexdef as definition
    FROM pg_indexes
    WHERE schemaname = 'public'
    ORDER BY tablename, indexname;
    """
    
    with engine.connect() as connection:
        result = connection.execute(text(query))
        indices = result.fetchall()
        
        print("\nExisting PostgreSQL indices:")
        for idx in indices:
            print(f"\nTable: {idx.table}")
            print(f"Index: {idx.index}")
            print(f"Definition: {idx.definition}")

def verify_memgraph_indices():
    """Verify that Memgraph indices were created"""
    print("\nVerifying Memgraph indices...")
    
    memgraph = Memgraph(host=MEMGRAPH_HOST, port=MEMGRAPH_PORT)
    
    # Get all indices
    result = memgraph.execute_and_fetch("SHOW INDEX INFO;")
    
    print("\nExisting Memgraph indices:")
    for record in result:
        print(f"\nLabel: {record['label']}")
        print(f"Property: {record['property']}")

def main():
    # Create indices
    create_postgresql_indices()
    create_memgraph_indices()
    
    # Verify indices
    verify_postgresql_indices()
    verify_memgraph_indices()

if __name__ == "__main__":
    main() 