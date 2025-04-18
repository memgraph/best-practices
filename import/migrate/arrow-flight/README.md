# Arrow Flight

With the `arrow_flight()` procedure, users can access data sources which support
the [Arrow Flight RPC
protocol](https://arrow.apache.org/docs/format/Flight.html) for transfer of
large data records to achieve high performance.

To test the usage, first start the server:

```python
python server.py
```

Then, start the client:

```python
python client.py
```

The client script connects to local Memgraph instance and runs `arrow_flight()`
procedure which creates client, connects to the server and streams rows to
Memgraph. 