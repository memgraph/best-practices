#!/usr/bin/env python3
"""
Script to populate MongoDB with sample data for migration to Memgraph.
This creates a social network dataset with users, posts, and relationships.
"""

import pymongo
from datetime import datetime, timedelta
import random
import sys

def connect_to_mongodb():
    """Connect to MongoDB with authentication."""
    try:
        client = pymongo.MongoClient(
            "mongodb://root:example@localhost:27017/",
            authSource="admin"
        )
        # Test the connection
        client.admin.command('ping')
        print("Successfully connected to MongoDB!")
        return client
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        sys.exit(1)

def create_sample_data():
    """Create sample data for the social network."""
    
    # Sample users data
    users = [
        {
            "_id": "user_1",
            "name": "Alice Johnson",
            "email": "alice@example.com",
            "age": 28,
            "city": "New York",
            "profession": "Software Engineer",
            "created_at": datetime.now() - timedelta(days=365),
            "is_active": True
        },
        {
            "_id": "user_2", 
            "name": "Bob Smith",
            "email": "bob@example.com",
            "age": 32,
            "city": "San Francisco",
            "profession": "Data Scientist",
            "created_at": datetime.now() - timedelta(days=300),
            "is_active": True
        },
        {
            "_id": "user_3",
            "name": "Carol Davis",
            "email": "carol@example.com", 
            "age": 25,
            "city": "Seattle",
            "profession": "Product Manager",
            "created_at": datetime.now() - timedelta(days=200),
            "is_active": True
        },
        {
            "_id": "user_4",
            "name": "David Wilson",
            "email": "david@example.com",
            "age": 35,
            "city": "Boston",
            "profession": "DevOps Engineer",
            "created_at": datetime.now() - timedelta(days=150),
            "is_active": False
        },
        {
            "_id": "user_5",
            "name": "Eva Brown",
            "email": "eva@example.com",
            "age": 29,
            "city": "Austin",
            "profession": "UX Designer",
            "created_at": datetime.now() - timedelta(days=100),
            "is_active": True
        }
    ]
    
    # Sample posts data
    posts = [
        {
            "_id": "post_1",
            "user_id": "user_1",
            "title": "Learning Graph Databases",
            "content": "Just started exploring Memgraph and graph databases. The performance is amazing!",
            "tags": ["graph", "database", "memgraph"],
            "likes": 15,
            "created_at": datetime.now() - timedelta(days=5)
        },
        {
            "_id": "post_2",
            "user_id": "user_2", 
            "title": "Data Science Insights",
            "content": "Working on a new machine learning project using graph neural networks.",
            "tags": ["ml", "data-science", "gnn"],
            "likes": 23,
            "created_at": datetime.now() - timedelta(days=3)
        },
        {
            "_id": "post_3",
            "user_id": "user_3",
            "title": "Product Strategy",
            "content": "Planning the roadmap for our new graph analytics platform.",
            "tags": ["product", "strategy", "analytics"],
            "likes": 8,
            "created_at": datetime.now() - timedelta(days=1)
        },
        {
            "_id": "post_4",
            "user_id": "user_1",
            "title": "Cypher Query Tips",
            "content": "Here are some advanced Cypher patterns I've been using lately.",
            "tags": ["cypher", "queries", "tips"],
            "likes": 31,
            "created_at": datetime.now() - timedelta(hours=12)
        },
        {
            "_id": "post_5",
            "user_id": "user_5",
            "title": "Design Systems",
            "content": "Building a comprehensive design system for our graph visualization tools.",
            "tags": ["design", "ui", "visualization"],
            "likes": 12,
            "created_at": datetime.now() - timedelta(hours=6)
        }
    ]
    
    # Sample relationships data
    relationships = [
        {
            "_id": "rel_1",
            "from_user": "user_1",
            "to_user": "user_2", 
            "type": "follows",
            "created_at": datetime.now() - timedelta(days=200)
        },
        {
            "_id": "rel_2",
            "from_user": "user_1",
            "to_user": "user_3",
            "type": "follows", 
            "created_at": datetime.now() - timedelta(days=150)
        },
        {
            "_id": "rel_3",
            "from_user": "user_2",
            "to_user": "user_1",
            "type": "follows",
            "created_at": datetime.now() - timedelta(days=180)
        },
        {
            "_id": "rel_4",
            "from_user": "user_3",
            "to_user": "user_5",
            "type": "follows",
            "created_at": datetime.now() - timedelta(days=50)
        },
        {
            "_id": "rel_5",
            "from_user": "user_4",
            "to_user": "user_1",
            "type": "follows",
            "created_at": datetime.now() - timedelta(days=100)
        },
        {
            "_id": "rel_6",
            "from_user": "user_5",
            "to_user": "user_2",
            "type": "follows",
            "created_at": datetime.now() - timedelta(days=30)
        }
    ]
    
    # Sample comments data
    comments = [
        {
            "_id": "comment_1",
            "post_id": "post_1",
            "user_id": "user_2",
            "content": "Great post! I've been using Memgraph for similar projects.",
            "created_at": datetime.now() - timedelta(days=4)
        },
        {
            "_id": "comment_2", 
            "post_id": "post_1",
            "user_id": "user_3",
            "content": "Thanks for sharing these insights!",
            "created_at": datetime.now() - timedelta(days=3)
        },
        {
            "_id": "comment_3",
            "post_id": "post_2",
            "user_id": "user_1", 
            "content": "Very interesting approach to GNNs!",
            "created_at": datetime.now() - timedelta(days=2)
        },
        {
            "_id": "comment_4",
            "post_id": "post_4",
            "user_id": "user_5",
            "content": "These Cypher patterns are really helpful!",
            "created_at": datetime.now() - timedelta(hours=8)
        }
    ]
    
    return users, posts, relationships, comments

def populate_database(client):
    """Populate the MongoDB database with sample data."""
    db = client.social_network
    
    # Clear existing data
    print("Clearing existing data...")
    db.users.drop()
    db.posts.drop()
    db.relationships.drop()
    db.comments.drop()
    
    # Get sample data
    users, posts, relationships, comments = create_sample_data()
    
    # Insert data
    print("Inserting users...")
    db.users.insert_many(users)
    
    print("Inserting posts...")
    db.posts.insert_many(posts)
    
    print("Inserting relationships...")
    db.relationships.insert_many(relationships)
    
    print("Inserting comments...")
    db.comments.insert_many(comments)
    
    # Create indexes for better performance
    print("Creating indexes...")
    db.users.create_index("email", unique=True)
    db.users.create_index("city")
    db.posts.create_index("user_id")
    db.posts.create_index("created_at")
    db.relationships.create_index([("from_user", 1), ("to_user", 1)])
    db.comments.create_index("post_id")
    
    print("Database populated successfully!")
    
    # Print summary
    print(f"\nSummary:")
    print(f"- Users: {db.users.count_documents({})}")
    print(f"- Posts: {db.posts.count_documents({})}")
    print(f"- Relationships: {db.relationships.count_documents({})}")
    print(f"- Comments: {db.comments.count_documents({})}")

def main():
    """Main function to populate MongoDB."""
    print("Starting MongoDB population...")
    
    # Connect to MongoDB
    client = connect_to_mongodb()
    
    try:
        # Populate the database
        populate_database(client)
    except Exception as e:
        print(f"Error populating database: {e}")
        sys.exit(1)
    finally:
        # Close the connection
        client.close()
        print("MongoDB connection closed.")

if __name__ == "__main__":
    main()
