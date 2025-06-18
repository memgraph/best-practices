# Family Tree Use Case with Memgraph

This example demonstrates how to use Memgraph for family tree analysis with advanced features including storage mode switching, indexing, Time-to-Live (TTL), and path traversal algorithms.

## 🌟 Features Demonstrated

- **Storage Mode Switching**: Switches to `IN_MEMORY_ANALYTICAL` mode for optimal performance
- **Indexing**: Creates label and label-property indexes for efficient querying
- **Time-to-Live (TTL)**: Automatically expires data after 30 seconds
- **Path Traversal**: Uses Memgraph's advanced path finding algorithms (BFS, wShortest)
- **Family Relationships**: Uses explicit `mother_id` and `father_id` from CSV files to create `MOTHER_OF` and `FATHER_OF` relationships
- **Multiple Data Sources**: Loads data from three separate CSV files

## 📁 File Structure

```
use_cases/family_tree/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── family_tree_example.py       # Main Python script
├── family_tree_1.csv           # First family dataset (Smith & Johnson families)
├── family_tree_2.csv           # Second family dataset (Brown & Wilson families)
└── family_tree_3.csv           # Third family dataset (Rodriguez & Garcia families)
```

## 📊 Data Structure

Each CSV file contains family data with the following columns:

- `id`: Unique identifier for each person
- `name`: Full name of the person
- `family_id`: Family group identifier
- `gender`: Gender (M/F)
- `dob`: Date of birth (YYYY-MM-DD format)
- `mother_id`: ID of the person's mother (empty for root nodes)
- `father_id`: ID of the person's father (empty for root nodes)

### Example Data:
```csv
id,name,family_id,gender,dob,mother_id,father_id
1,John Smith,1,M,1980-05-15,,
2,Sarah Smith,1,F,1982-08-22,,
3,Michael Smith,1,M,2005-03-10,2,1
4,Emma Smith,1,F,2007-11-05,2,1
5,David Smith,1,M,2010-06-18,2,1
```

## 🔧 Prerequisites

1. **Memgraph Database**: Running instance of Memgraph
2. **Python 3.8+**: Python environment with pip
3. **Dependencies**: Install required packages

## 🚀 Installation & Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start Memgraph** (if not already running):
   ```bash
   docker run -it -p 7687:7687 -p 7444:7444 memgraph/memgraph-platform
   ```

3. **Run the example**:
   ```bash
   python family_tree_example.py
   ```

## 🔍 What the Script Does

### 1. Storage Mode Configuration
- Switches Memgraph to `IN_MEMORY_ANALYTICAL` mode for optimal analytical query performance

### 2. Data Loading
- Loads family data from three CSV files
- Creates `Person` nodes with properties: `id`, `name`, `family_id`, `gender`, `dob`

### 3. Relationship Creation
- **Mother-Child Relationships**: Creates `MOTHER_OF` relationships based on explicit `mother_id` values from CSV
- **Father-Child Relationships**: Creates `FATHER_OF` relationships based on explicit `father_id` values from CSV
- **Sibling Relationships**: Deduced through Cypher queries by finding people who share the same parents

### 4. Indexing
- Creates label index on `:Person`
- Creates label-property indexes on:
  - `Person(id)`
  - `Person(name)`
  - `Person(family_id)`

### 5. Time-to-Live (TTL)
- Enables TTL to run every 5 seconds
- Sets all Person nodes to expire after 30 seconds
- Uses the `TTL` label and `ttl` property as required by Memgraph

### 6. Advanced Queries
The script demonstrates several types of queries:

#### Basic Family Queries
- **Family Overview**: Lists all families with member counts
- **Mother-Child Relationships**: Shows all mother-child connections
- **Father-Child Relationships**: Shows all father-child connections
- **Sibling Relationships**: Displays sibling connections (deduced from shared parents)
- **Full Sibling Relationships**: Shows siblings with the same mother AND father
- **Family Statistics**: Gender distribution and member lists

#### Path Traversal Queries
- **BFS Path Finding**: Finds all paths between family members using Breadth-First Search
- **Shortest Path**: Uses `wShortest` algorithm to find optimal paths
- **Reachable Members**: Discovers all family members reachable within 3 hops

#### Advanced Family Analysis
- **Grandparent Relationships**: Finds 2-hop parent relationships
- **Maternal/Paternal Grandparents**: Distinguishes between maternal and paternal grandparents
- **Family Tree Roots**: Identifies people with no parents
- **Family Tree Leaves**: Identifies people with no children

### 7. TTL Verification
- Waits 30 seconds for TTL to expire
- Verifies that all Person nodes and relationships are automatically deleted

## 🧮 Query Examples

### Path Traversal with BFS
```cypher
MATCH p=(start:Person {name: 'John Smith'})-[:MOTHER_OF|FATHER_OF *BFS 1..5]-(end:Person)
WHERE end.name <> 'John Smith'
RETURN start.name as start_person, 
       end.name as end_person, 
       size(p) as path_length,
       [node in nodes(p) | node.name] as path
ORDER BY path_length, end.name
LIMIT 10
```

### Shortest Path with wShortest
```cypher
MATCH p=(start:Person {name: 'John Smith'})-[:MOTHER_OF|FATHER_OF *wShortest (r, n | 1)]-(end:Person {name: 'Emma Smith'})
RETURN start.name as start_person,
       end.name as end_person,
       size(p) as path_length,
       [node in nodes(p) | node.name] as path
```

### Full Sibling Relationships
```cypher
MATCH (mother:Person)-[:MOTHER_OF]->(child1:Person)
MATCH (mother:Person)-[:MOTHER_OF]->(child2:Person)
MATCH (father:Person)-[:FATHER_OF]->(child1:Person)
MATCH (father:Person)-[:FATHER_OF]->(child2:Person)
WHERE child1.id < child2.id
RETURN child1.name as sibling1, child2.name as sibling2, 
       mother.name as mother, father.name as father
ORDER BY mother.name, father.name, child1.name
```

### Maternal and Paternal Grandparents
```cypher
MATCH (maternal_grandmother:Person)-[:MOTHER_OF]->(mother:Person)-[:MOTHER_OF]->(child:Person)
RETURN 'Maternal Grandmother' as relationship_type, 
       maternal_grandmother.name as grandparent, 
       mother.name as parent, 
       child.name as child
UNION
MATCH (paternal_grandfather:Person)-[:FATHER_OF]->(father:Person)-[:FATHER_OF]->(child:Person)
RETURN 'Paternal Grandfather' as relationship_type,
       paternal_grandfather.name as grandparent, 
       father.name as parent, 
       child.name as child
ORDER BY relationship_type, grandparent.name
```

### Family Tree Roots (No Parents)
```cypher
MATCH (p:Person)
WHERE NOT EXISTS((:Person)-[:MOTHER_OF|FATHER_OF]->(p))
RETURN p.name as root_person, p.family_id as family_id
ORDER BY p.family_id, p.name
```

### Family Tree Leaves (No Children)
```cypher
MATCH (p:Person)
WHERE NOT EXISTS((p)-[:MOTHER_OF|FATHER_OF]->(:Person))
RETURN p.name as leaf_person, p.family_id as family_id
ORDER BY p.family_id, p.name
```

## 📈 Expected Output

The script will output:
1. Data loading progress
2. Index creation confirmation
3. TTL setup information
4. Family tree analysis results
5. Path traversal examples
6. Advanced family analysis (grandparents, roots, leaves)
7. Maternal and paternal relationship distinctions
8. TTL deletion verification

## 🔗 Key Memgraph Features Used

- **[Storage Modes](https://memgraph.com/docs/fundamentals/storage-access)**: Switching to analytical mode
- **[Indexes](https://memgraph.com/docs/fundamentals/indexes)**: Creating label and label-property indexes
- **[Time-to-Live](https://memgraph.com/docs/querying/time-to-live)**: Automatic data expiration
- **[Deep Path Traversal](https://memgraph.com/docs/advanced-algorithms/deep-path-traversal)**: BFS and wShortest algorithms
- **[GQLAlchemy](https://memgraph.com/docs/client-libraries/python)**: Python client library

## 🎯 Use Cases

This example is useful for:
- **Genealogy Research**: Family tree analysis and relationship discovery
- **Social Network Analysis**: Understanding family connections and influence
- **Data Lifecycle Management**: Demonstrating automatic data cleanup with TTL
- **Performance Optimization**: Showing the impact of proper indexing
- **Path Analysis**: Finding connections between family members
- **Relationship Inference**: Demonstrating how complex relationships can be deduced from simple ones
- **Data Import**: Showing how to import structured family data with explicit relationships
- **Maternal/Paternal Analysis**: Distinguishing between maternal and paternal family lines

## 🏗️ Data Model Design

This example demonstrates a **gender-aware approach** to family tree modeling:

- **Explicit Gender Relationships**: Separate `MOTHER_OF` and `FATHER_OF` relationships
- **Flexible Data Import**: Relationships are created based on `mother_id` and `father_id` references
- **Derived Relationships**: Sibling relationships are computed on-demand through Cypher
- **Accurate Modeling**: Distinguishes between maternal and paternal family lines
- **Comprehensive Analysis**: Enables maternal/paternal grandparent analysis

## 📊 Family Structure Examples

### Family 1 (Smith & Johnson):
- **Roots**: John Smith, Sarah Smith, Lisa Johnson, Robert Johnson
- **Children**: Michael, Emma, David (children of John & Sarah)
- **Children**: Jessica, Christopher, Amanda (children of Lisa & Robert)

### Family 2 (Brown & Wilson):
- **Roots**: William Brown, Mary Brown, Daniel Wilson, Jennifer Wilson
- **Children**: James, Patricia, Thomas, Elizabeth (children of William & Mary)
- **Children**: Matthew, Ashley, Andrew (children of Daniel & Jennifer)

### Family 3 (Rodriguez & Garcia):
- **Roots**: Carlos Rodriguez, Ana Rodriguez, Maria Garcia, Jose Garcia
- **Children**: Sofia, Lucas (children of Carlos & Ana)
- **Children**: Isabella, Diego, Carmen, Antonio (children of Maria & Jose)

## 🐛 Troubleshooting

### Common Issues

1. **Connection Error**: Ensure Memgraph is running on `localhost:7687`
2. **Import Error**: Check that CSV files are in the same directory as the script
3. **TTL Not Working**: Verify Memgraph Enterprise features are enabled
4. **Index Creation Error**: Ensure no conflicting indexes exist
5. **Parent ID Error**: Ensure all `mother_id` and `father_id` values reference existing person IDs

### Debug Mode

To run with more verbose output, modify the script to include debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📚 Additional Resources

- [Memgraph Documentation](https://memgraph.com/docs)
- [GQLAlchemy Python Client](https://memgraph.com/docs/client-libraries/python)
- [Cypher Query Language](https://memgraph.com/docs/querying)
- [Advanced Algorithms](https://memgraph.com/docs/advanced-algorithms) 