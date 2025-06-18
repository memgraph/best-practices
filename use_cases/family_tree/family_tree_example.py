from gqlalchemy import Memgraph
import pandas as pd
import time
import sys
from datetime import datetime, timedelta

# Initialize Memgraph connection
memgraph = Memgraph(host="127.0.0.1", port=7687)


def load_family_data(csv_file):
    """Load family data from CSV file"""
    print(f"📂 Loading data from {csv_file}...")
    df = pd.read_csv(csv_file)
    return df


def create_person_nodes(df):
    """Create person nodes from DataFrame"""
    print("👥 Creating person nodes...")
    
    for _, row in df.iterrows():
        query = """
        CREATE (p:Person {
            id: $id,
            name: $name,
            family_id: $family_id,
            gender: $gender,
            dob: date($dob)
        })
        """
        memgraph.execute(query, {
            'id': row['id'],
            'name': row['name'],
            'family_id': row['family_id'],
            'gender': row['gender'],
            'dob': row['dob']
        })


def create_family_relationships(df):
    """Create family relationships based on mother_id and father_id from CSV"""
    print("🔗 Creating family relationships...")
    
    # Create mother-child relationships
    for _, row in df.iterrows():
        if pd.notna(row['mother_id']) and row['mother_id'] != '':
            query = """
            MATCH (mother:Person {id: $mother_id}), (child:Person {id: $child_id})
            CREATE (mother)-[:MOTHER_OF]->(child)
            """
            memgraph.execute(query, {
                'mother_id': int(row['mother_id']),
                'child_id': row['id']
            })
    
    # Create father-child relationships
    for _, row in df.iterrows():
        if pd.notna(row['father_id']) and row['father_id'] != '':
            query = """
            MATCH (father:Person {id: $father_id}), (child:Person {id: $child_id})
            CREATE (father)-[:FATHER_OF]->(child)
            """
            memgraph.execute(query, {
                'father_id': int(row['father_id']),
                'child_id': row['id']
            })


def switch_to_analytical_mode():
    """Switch Memgraph to analytical storage mode"""
    print("🔄 Switching to analytical storage mode...")
    memgraph.execute("STORAGE MODE IN_MEMORY_ANALYTICAL;")

def clear_database():
    print("🔄 Clearing database...")
    memgraph.execute("DROP GRAPH;")


def create_indexes():
    """Create indexes for better query performance"""
    print("📊 Creating indexes...")
    
    # Label index for Person
    memgraph.execute("CREATE INDEX ON :Person;")
    
    # Label-property indexes
    memgraph.execute("CREATE INDEX ON :Person(id);")
    memgraph.execute("CREATE INDEX ON :Person(name);")
    memgraph.execute("CREATE INDEX ON :Person(family_id);")
    
    print("✅ Indexes created successfully")


def enable_ttl():
    """Enable TTL with 30-second expiration"""
    print("⏰ Enabling TTL with 30-second expiration...")
    
    # Enable TTL to run every 5 seconds
    memgraph.execute('ENABLE TTL EVERY "5s";')
    
    # Set TTL for all Person nodes to expire in 30 seconds
    expiration_time = int((datetime.now() + timedelta(seconds=30)).timestamp() * 1000000)
    
    query = """
    MATCH (p:Person)
    SET p:TTL, p.ttl = $expiration_time
    """
    memgraph.execute(query, {'expiration_time': expiration_time})
    
    print(f"✅ TTL set for all persons to expire at {datetime.fromtimestamp(expiration_time/1000000)}")


def execute_family_queries():
    """Execute various family tree queries"""
    print("\n🔍 Executing family tree queries...")
    
    # Query 1: Find all families
    print("\n1️⃣ All families in the database:")
    result = memgraph.execute_and_fetch("""
        MATCH (p:Person)
        RETURN p.family_id as family_id, 
               collect(p.name) as members,
               count(p) as member_count
        ORDER BY family_id
    """)
    for row in result:
        print(f"Family {row['family_id']}: {row['members']} ({row['member_count']} members)")
    
    # Query 2: Find mother-child relationships
    print("\n2️⃣ Mother-child relationships:")
    result = memgraph.execute_and_fetch("""
        MATCH (m:Person)-[:MOTHER_OF]->(c:Person)
        RETURN m.name as mother, c.name as child
        ORDER BY m.name
    """)
    for row in result:
        print(f"{row['mother']} → {row['child']}")
    
    # Query 3: Find father-child relationships
    print("\n3️⃣ Father-child relationships:")
    result = memgraph.execute_and_fetch("""
        MATCH (f:Person)-[:FATHER_OF]->(c:Person)
        RETURN f.name as father, c.name as child
        ORDER BY f.name
    """)
    for row in result:
        print(f"{row['father']} → {row['child']}")
    
    # Query 4: Find siblings (deduced from shared parents)
    print("\n4️⃣ Sibling relationships (deduced from shared parents):")
    result = memgraph.execute_and_fetch("""
        MATCH (p:Person)-[:MOTHER_OF|FATHER_OF]->(c1:Person)
        MATCH (p:Person)-[:MOTHER_OF|FATHER_OF]->(c2:Person)
        WHERE c1.id < c2.id
        RETURN c1.name as sibling1, c2.name as sibling2, p.name as parent
        ORDER BY p.name, c1.name
    """)
    for row in result:
        print(f"{row['sibling1']} ↔ {row['sibling2']} (children of {row['parent']})")
    
    # Query 5: Find full siblings (same mother AND father)
    print("\n5️⃣ Full sibling relationships (same mother and father):")
    result = memgraph.execute_and_fetch("""
        MATCH (mom:Person)-[:MOTHER_OF]->(c1:Person)
        MATCH (mom:Person)-[:MOTHER_OF]->(c2:Person)
        MATCH (dad:Person)-[:FATHER_OF]->(c1:Person)
        MATCH (dad:Person)-[:FATHER_OF]->(c2:Person)
        WHERE c1.id < c2.id
        RETURN c1.name as sibling1, c2.name as sibling2, 
               mom.name as mother, dad.name as father
        ORDER BY mom.name, dad.name, c1.name
    """)
    for row in result:
        print(f"{row['sibling1']} ↔ {row['sibling2']} (children of {row['mother']} & {row['father']})")
    
    # Query 6: Path traversal - Find all paths between family members
    print("\n6️⃣ Path traversal - All paths between family members:")
    result = memgraph.execute_and_fetch("""
        MATCH p=(start:Person {name: 'John Smith'})-[:MOTHER_OF|FATHER_OF *1..5]-(end:Person)
        WHERE end.name <> 'John Smith'
        RETURN start.name as start_person, 
               end.name as end_person, 
               size(p) as path_length,
               [node in nodes(p) | node.name] as path
        ORDER BY path_length, end.name
        LIMIT 10
    """)
    for row in result:
        print(f"{row['start_person']} → {row['end_person']} (length: {row['path_length']})")
        print(f"  Path: {' → '.join(row['path'])}")
    
    # Query 7: Shortest path between two specific people
    print("\n7️⃣ Shortest path between John Smith and Emma Smith:")
    result = memgraph.execute_and_fetch("""
        MATCH p=(start:Person {name: 'John Smith'})-[:MOTHER_OF|FATHER_OF *wShortest (r, n | 1)]-(end:Person {name: 'Emma Smith'})
        RETURN start.name as start_person,
               end.name as end_person,
               size(p) as path_length,
               [node in nodes(p) | node.name] as path
    """)
    for row in result:
        print(f"Shortest path: {row['start_person']} → {row['end_person']} (length: {row['path_length']})")
        print(f"Path: {' → '.join(row['path'])}")
    
    # Query 8: Find all reachable family members from a starting point
    print("\n8️⃣ All reachable family members from John Smith (within 3 hops):")
    result = memgraph.execute_and_fetch("""
        MATCH p=(start:Person {name: 'John Smith'})-[:MOTHER_OF|FATHER_OF *1..3]-(end:Person)
        WHERE end.name <> 'John Smith'
        RETURN DISTINCT end.name as reachable_person
        ORDER BY end.name
    """)
    for row in result:
        print(f"{row['reachable_person']}")
    
    # Query 9: Family statistics
    print("\n9️⃣ Family statistics:")
    result = memgraph.execute_and_fetch("""
        MATCH (p:Person)
        WITH p.family_id as family_id, collect(p) as members
        RETURN family_id,
               size(members) as total_members,
               size([m in members WHERE m.gender = 'M']) as males,
               size([m in members WHERE m.gender = 'F']) as females,
               [m in members | m.name] as member_names
        ORDER BY family_id
    """)
    for row in result:
        print(f"Family {row['family_id']}: {row['total_members']} members ({row['males']}M, {row['females']}F)")
        print(f"  Members: {', '.join(row['member_names'])}")
    
    # Query 10: Find grandparents (2-hop parent relationships)
    print("\n🔟 Grandparent relationships:")
    result = memgraph.execute_and_fetch("""
        MATCH (grandparent:Person)-[:MOTHER_OF|FATHER_OF]->(parent:Person)-[:MOTHER_OF|FATHER_OF]->(child:Person)
        RETURN grandparent.name as grandparent, 
               parent.name as parent, 
               child.name as child
        ORDER BY grandparent.name, parent.name
    """)
    for row in result:
        print(f"{row['grandparent']} → {row['parent']} → {row['child']}")
    
    # Query 11: Find people with no parents (root nodes in family tree)
    print("\n1️⃣1️⃣ People with no parents (family tree roots):")
    result = memgraph.execute_and_fetch("""
        MATCH (p:Person)
        WHERE NOT EXISTS((:Person)-[:MOTHER_OF|FATHER_OF]->(p))
        RETURN p.name as root_person, p.family_id as family_id
        ORDER BY p.family_id, p.name
    """)
    for row in result:
        print(f"{row['root_person']} (Family {row['family_id']})")
    
    # Query 12: Find people with no children (leaf nodes in family tree)
    print("\n1️⃣2️⃣ People with no children (family tree leaves):")
    result = memgraph.execute_and_fetch("""
        MATCH (p:Person)
        WHERE NOT EXISTS((p)-[:MOTHER_OF|FATHER_OF]->(:Person))
        RETURN p.name as leaf_person, p.family_id as family_id
        ORDER BY p.family_id, p.name
    """)
    for row in result:
        print(f"{row['leaf_person']} (Family {row['family_id']})")
    
    # Query 13: Find maternal and paternal grandparents separately
    print("\n1️⃣3️⃣ Maternal and paternal grandparents:")
    result = memgraph.execute_and_fetch("""
        MATCH (maternal_grandmother:Person)-[:MOTHER_OF]->(mother:Person)-[:MOTHER_OF]->(child:Person)
        RETURN 'Maternal Grandmother' as relationship_type, 
               maternal_grandmother.name as grandparent, 
               mother.name as parent, 
               child.name as child
        UNION
        MATCH (maternal_grandfather:Person)-[:FATHER_OF]->(mother:Person)-[:MOTHER_OF]->(child:Person)
        RETURN 'Maternal Grandfather' as relationship_type,
               maternal_grandfather.name as grandparent, 
               mother.name as parent, 
               child.name as child
        UNION
        MATCH (paternal_grandmother:Person)-[:MOTHER_OF]->(father:Person)-[:FATHER_OF]->(child:Person)
        RETURN 'Paternal Grandmother' as relationship_type,
               paternal_grandmother.name as grandparent, 
               father.name as parent, 
               child.name as child
        UNION
        MATCH (paternal_grandfather:Person)-[:FATHER_OF]->(father:Person)-[:FATHER_OF]->(child:Person)
        RETURN 'Paternal Grandfather' as relationship_type,
               paternal_grandfather.name as grandparent, 
               father.name as parent, 
               child.name as child
        ORDER BY relationship_type, grandparent.name
    """)
    for row in result:
        print(f"{row['relationship_type']}: {row['grandparent']} → {row['parent']} → {row['child']}")


def verify_ttl_deletion():
    """Verify that TTL has deleted the data"""
    print("\n🔍 Verifying TTL deletion...")
    
    # Check if any Person nodes remain
    result = memgraph.execute_and_fetch("MATCH (p:Person) RETURN count(p) as remaining_persons")
    remaining = list(result)[0]['remaining_persons']
    
    if remaining == 0:
        print("✅ TTL successfully deleted all person nodes!")
    else:
        print(f"⚠️ {remaining} person nodes still remain in the database")
    
    # Check if any relationships remain
    result = memgraph.execute_and_fetch("MATCH ()-[r:MOTHER_OF|FATHER_OF]->() RETURN count(r) as remaining_relationships")
    remaining_rel = list(result)[0]['remaining_relationships']
    
    if remaining_rel == 0:
        print("✅ TTL successfully deleted all family relationships!")
    else:
        print(f"⚠️ {remaining_rel} family relationships still remain in the database")


def main():
    """Main function to run the family tree example"""
    print("🌳 Family Tree Example with Memgraph")
    print("=" * 50)
    
    try:
        # Step 1: Switch to analytical mode
        switch_to_analytical_mode()
        clear_database()
        
        # Step 2: Clear existing data
        print("🗑️ Clearing existing data...")
        memgraph.execute("DROP GRAPH;")
        
        # Step 3: Load and create data from all three CSV files
        csv_files = ['family_tree_1.csv', 'family_tree_2.csv', 'family_tree_3.csv']
        for csv_file in csv_files:
            df = load_family_data(csv_file)
            create_person_nodes(df)
            create_family_relationships(df)
        
        # Step 4: Create indexes
        create_indexes()
        
        # Step 5: Enable TTL
        enable_ttl()
        
        # Step 6: Execute family queries
        execute_family_queries()
        
        # Step 7: Wait for TTL to expire
        print(f"\n⏳ Waiting 30 seconds for TTL to expire...")
        print("   (Data will be automatically deleted)")
        time.sleep(50)
        
        # Step 8: Verify TTL deletion
        verify_ttl_deletion()
        
        print("\n🎉 Family tree example completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 