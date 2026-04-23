#!/usr/bin/env python3
"""
Migration script to transfer data from MongoDB to Memgraph using the migrate.mongodb() procedure.
This script demonstrates how to use Memgraph's built-in migration capabilities to query MongoDB
and create corresponding graph structures in Memgraph.
"""

from gqlalchemy import Memgraph
import sys

# Configuration
MEMGRAPH_HOST = "localhost"
MEMGRAPH_PORT = 7687

def connect_memgraph():
    """Connect to Memgraph."""
    try:
        memgraph = Memgraph(host=MEMGRAPH_HOST, port=MEMGRAPH_PORT)
        # Test the connection
        memgraph.execute_and_fetch("MATCH (n) RETURN count(n) as count")
        print("Successfully connected to Memgraph!")
        return memgraph
    except Exception as e:
        print(f"Failed to connect to Memgraph: {e}")
        return None

def clear_memgraph(memgraph):
    """Clear all data from Memgraph."""
    try:
        memgraph.execute("MATCH (n) DETACH DELETE n")
        print("Cleared all data from Memgraph.")
    except Exception as e:
        print(f"Error clearing Memgraph: {e}")

def migrate_users(memgraph):
    """Migrate users from MongoDB to Memgraph using migrate.mongodb()."""
    print("Migrating users...")
    
    try:
        # Use migrate.mongodb() to get user data
        results = list(memgraph.execute_and_fetch(
            """
            CALL migrate.mongodb("users", 
                {}, 
                {
                    projection: {_id: 1, name: 1, email: 1, age: 1, city: 1, profession: 1, created_at: 1, is_active: 1}
                }, 
                {
                    host: "mongo",
                    port: 27017,
                    username: "root",
                    password: "example",
                    database: "social_network",
                    authSource: "admin"
                }
            )
            YIELD row
            MERGE (u:User {user_id: row._id})
            SET u += row
            RETURN count(u) as users_migrated
            """
        ))
        
        users_migrated = results[0]["users_migrated"] if results else 0
        print(f"Migrated {users_migrated} users.")
        return users_migrated
        
    except Exception as e:
        print(f"Error migrating users: {e}")
        return 0

def migrate_posts(memgraph):
    """Migrate posts from MongoDB to Memgraph using migrate.mongodb()."""
    print("Migrating posts...")
    
    try:
        # Use migrate.mongodb() to get post data
        results = list(memgraph.execute_and_fetch(
            """
            CALL migrate.mongodb("posts", 
                {}, 
                {
                    projection: {_id: 1, user_id: 1, title: 1, content: 1, tags: 1, likes: 1, created_at: 1}
                }, 
                {
                    host: "mongo",
                    port: 27017,
                    username: "root",
                    password: "example",
                    database: "social_network",
                    authSource: "admin"
                }
            )
            YIELD row
            MERGE (p:Post {post_id: row._id})
            SET p += row
            RETURN count(p) as posts_migrated
            """
        ))
        
        posts_migrated = results[0]["posts_migrated"] if results else 0
        print(f"Migrated {posts_migrated} posts.")
        return posts_migrated
        
    except Exception as e:
        print(f"Error migrating posts: {e}")
        return 0

def migrate_comments(memgraph):
    """Migrate comments from MongoDB to Memgraph using migrate.mongodb()."""
    print("Migrating comments...")
    
    try:
        # Use migrate.mongodb() to get comment data
        results = list(memgraph.execute_and_fetch(
            """
            CALL migrate.mongodb("comments", 
                {}, 
                {
                    projection: {_id: 1, post_id: 1, user_id: 1, content: 1, created_at: 1}
                }, 
                {
                    host: "mongo",
                    port: 27017,
                    username: "root",
                    password: "example",
                    database: "social_network",
                    authSource: "admin"
                }
            )
            YIELD row
            MERGE (c:Comment {comment_id: row._id})
            SET c += row
            RETURN count(c) as comments_migrated
            """
        ))
        
        comments_migrated = results[0]["comments_migrated"] if results else 0
        print(f"Migrated {comments_migrated} comments.")
        return comments_migrated
        
    except Exception as e:
        print(f"Error migrating comments: {e}")
        return 0

def create_relationships(memgraph):
    """Create relationships between nodes in Memgraph using migrate.mongodb()."""
    print("Creating relationships...")
    
    # Create FOLLOWS relationships
    follows_created = create_follows_relationships(memgraph)
    
    # Create CREATED relationships (users -> posts)
    created_relationships = create_created_relationships(memgraph)
    
    # Create COMMENTED relationships (users -> comments -> posts)
    commented_relationships = create_commented_relationships(memgraph)
    
    print(f"Created {follows_created} FOLLOWS relationships.")
    print(f"Created {created_relationships} CREATED relationships.")
    print(f"Created {commented_relationships} COMMENTED relationships.")
    
    return follows_created + created_relationships + commented_relationships

def create_follows_relationships(memgraph):
    """Create FOLLOWS relationships between users using migrate.mongodb()."""
    try:
        results = list(memgraph.execute_and_fetch(
            """
            CALL migrate.mongodb("relationships", 
                {type: "follows"}, 
                {
                    projection: {_id: 1, from_user: 1, to_user: 1, created_at: 1}
                }, 
                {
                    host: "mongo",
                    port: 27017,
                    username: "root",
                    password: "example",
                    database: "social_network",
                    authSource: "admin"
                }
            )
            YIELD row
            MATCH (from_user:User {user_id: row.from_user})
            MATCH (to_user:User {user_id: row.to_user})
            CREATE (from_user)-[r:FOLLOWS {created_at: row.created_at}]->(to_user)
            RETURN count(r) as follows_created
            """
        ))
        
        follows_created = results[0]["follows_created"] if results else 0
        return follows_created
        
    except Exception as e:
        print(f"Error creating FOLLOWS relationships: {e}")
        return 0

def create_created_relationships(memgraph):
    """Create CREATED relationships between users and posts using migrate.mongodb()."""
    try:
        results = list(memgraph.execute_and_fetch(
            """
            CALL migrate.mongodb("posts", 
                {}, 
                {
                    projection: {_id: 1, user_id: 1}
                }, 
                {
                    host: "mongo",
                    port: 27017,
                    username: "root",
                    password: "example",
                    database: "social_network",
                    authSource: "admin"
                }
            )
            YIELD row
            MATCH (user:User {user_id: row.user_id})
            MATCH (post:Post {post_id: row._id})
            CREATE (user)-[r:CREATED]->(post)
            RETURN count(r) as created_relationships
            """
        ))
        
        created_relationships = results[0]["created_relationships"] if results else 0
        return created_relationships
        
    except Exception as e:
        print(f"Error creating CREATED relationships: {e}")
        return 0

def create_commented_relationships(memgraph):
    """Create COMMENTED relationships between users, comments, and posts using migrate.mongodb()."""
    try:
        results = list(memgraph.execute_and_fetch(
            """
            CALL migrate.mongodb("comments", 
                {}, 
                {
                    projection: {_id: 1, user_id: 1, post_id: 1}
                }, 
                {
                    host: "mongo",
                    port: 27017,
                    username: "root",
                    password: "example",
                    database: "social_network",
                    authSource: "admin"
                }
            )
            YIELD row
            MATCH (user:User {user_id: row.user_id})
            MATCH (comment:Comment {comment_id: row._id})
            MATCH (post:Post {post_id: row.post_id})
            CREATE (user)-[r1:COMMENTED]->(comment)
            CREATE (comment)-[r2:COMMENTED]->(post)
            RETURN count(r1) + count(r2) as commented_relationships
            """
        ))
        
        commented_relationships = results[0]["commented_relationships"] if results else 0
        return commented_relationships
        
    except Exception as e:
        print(f"Error creating COMMENTED relationships: {e}")
        return 0

def main():
    """Main function to run the migration."""
    print("Starting MongoDB to Memgraph migration using migrate.mongodb()...")
    
    # Connect to Memgraph
    memgraph = connect_memgraph()
    if not memgraph:
        print("Failed to connect to Memgraph. Exiting.")
        sys.exit(1)
    
    try:
        # Clear existing data
        clear_memgraph(memgraph)
        
        # Migrate data using migrate.mongodb() procedure
        users_count = migrate_users(memgraph)
        posts_count = migrate_posts(memgraph)
        comments_count = migrate_comments(memgraph)
        relationships_count = create_relationships(memgraph)
        
        print(f"\nMigration completed successfully!")
        print(f"Summary:")
        print(f"- Users migrated: {users_count}")
        print(f"- Posts migrated: {posts_count}")
        print(f"- Comments migrated: {comments_count}")
        print(f"- Relationships created: {relationships_count}")
        
        print("\nYou can now query your graph data in Memgraph.")
        print("\nExample queries:")
        print("MATCH (u:User) RETURN u LIMIT 5;")
        print("MATCH (u:User)-[:FOLLOWS]->(f:User) RETURN u.name, f.name;")
        print("MATCH (u:User)-[:CREATED]->(p:Post) RETURN u.name, p.title;")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)
    finally:
        print("Migration process completed.")

if __name__ == "__main__":
    main()
