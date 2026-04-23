# MongoDB to Memgraph Migration

This directory contains scripts and configuration for migrating data from MongoDB to Memgraph using the built-in `migrate.mongodb()` procedure from MAGE. The migration demonstrates how to transfer a social network dataset from MongoDB's document-based structure to Memgraph's graph structure using Memgraph's native migration capabilities.

## Overview

### Installation

1. **Clone and navigate to the directory:**
   ```bash
   cd import/migrate/mongodb/
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the services:**
   ```bash
   docker compose up -d
   ```

   This will start:
   - MongoDB on port 27017
   - Memgraph with MAGE on port 7687 (Bolt)

## Usage

### Step 1: Populate MongoDB

Run the script to populate MongoDB with sample data:

```bash
python populate_mongodb.py
```

### Step 2: Run Migration

Migrate data from MongoDB to Memgraph using the `migrate.mongodb()` procedure:

```bash
python migrate_to_memgraph.py
```
