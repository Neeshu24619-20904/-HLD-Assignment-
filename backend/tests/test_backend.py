import pytest
import time
from backend.app.services.consistent_hash import ConsistentHashRing
from backend.app.services.batch_writer import BatchSearchWriter

def test_consistent_hashing_ring_distribution():
    # Setup ring with 3 nodes
    nodes = ["node-1", "node-2", "node-3"]
    ring = ConsistentHashRing(nodes=nodes, replicas=50)
    
    # Test prefix routing consistency
    node_a = ring.get_node("iph")
    node_b = ring.get_node("iph")
    assert node_a == node_b, "Consistent hashing must return same node for same key"
    assert node_a in nodes, "Selected node must be on the ring"

    # Test key ranges are distributed across multiple nodes
    routes = {}
    prefixes = [f"pref-{i}" for i in range(100)]
    for p in prefixes:
        node = ring.get_node(p)
        routes[node] = routes.get(node, 0) + 1
        
    # We should have keys routed to multiple nodes
    assert len(routes.keys()) > 1, "Keys should distribute across multiple nodes"
    for n in nodes:
        assert routes.get(n, 0) > 0, f"Node {n} should receive some routed keys"

def test_batch_search_writer_buffering():
    writer = BatchSearchWriter()
    
    # Add searches
    writer.add_search("iphone 15")
    writer.add_search("iphone 15")
    writer.add_search("python")
    writer.add_search("iphone 15")
    
    # Assert metrics and buffer state
    metrics = writer.get_metrics()
    assert metrics["queue_size"] == 4, "Buffer size should match added items"
    assert metrics["total_searches_received"] == 4, "Total searches received tracker should increment"
    
    # Check aggregation processing structure
    buffer_content = writer.buffer
    assert len(buffer_content) == 4
    
    # Mock aggregates calculation
    aggregates = {}
    for query, _ in buffer_content:
        aggregates[query] = aggregates.get(query, 0) + 1
        
    assert aggregates["iphone 15"] == 3
    assert aggregates["python"] == 1
