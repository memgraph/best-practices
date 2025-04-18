# Arrow Flight

With the `migrate.arrow_flight()` procedure, users can access data sources which support
the [Arrow Flight RPC
protocol](https://arrow.apache.org/docs/format/Flight.html) for transfer of
large data records to achieve high performance.

## Prerequisites

Install the required libraries from the `arrow-flight` folder:

```
pip install -r requirements.txt
```

## Quick start

To test the usage, first start Memgraph MAGE:

```python
docker run -p 7687:7687 memgraph/memgraph-mage
```

Then, start the server:

```python
python server.py
```

In the end, start the client:

```python
python client.py
```

The client script connects to local Memgraph instance and runs `migrate.arrow_flight()`
procedure which creates client, connects to the server and streams rows to
Memgraph where it will create nodes.