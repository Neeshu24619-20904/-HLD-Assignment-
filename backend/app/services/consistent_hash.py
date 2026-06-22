import hashlib
import bisect
from typing import List, Dict, Any, Optional

class ConsistentHashRing:
    def __init__(self, nodes: Optional[List[str]] = None, replicas: int = 50):
        """
        Initializes the Consistent Hash Ring.
        :param nodes: List of physical node names (e.g. ['cache-node-1', 'cache-node-2', 'cache-node-3'])
        :param replicas: Number of virtual nodes per physical node
        """
        self.replicas = replicas
        self.ring: List[int] = []            # Sorted list of virtual node hashes
        self.ring_map: Dict[int, str] = {}   # Map of hash -> physical node name
        
        if nodes:
            for node in nodes:
                self.add_node(node)

    def _hash(self, key: str) -> int:
        """MD5-based hash returning a 32-bit integer for standard distribution."""
        hash_bytes = hashlib.md5(key.encode('utf-8')).digest()
        # Take the first 4 bytes and convert to a 32-bit unsigned integer
        return int.from_bytes(hash_bytes[:4], byteorder='big')

    def add_node(self, node: str):
        """Adds a physical node and its replicas to the ring."""
        for i in range(self.replicas):
            virtual_key = f"{node}#replica-{i}"
            val = self._hash(virtual_key)
            # Find insertion point to maintain sorted order
            idx = bisect.bisect_left(self.ring, val)
            # Insert if not already in ring
            if idx == len(self.ring) or self.ring[idx] != val:
                self.ring.insert(idx, val)
                self.ring_map[val] = node

    def remove_node(self, node: str):
        """Removes a physical node and its replicas from the ring."""
        for i in range(self.replicas):
            virtual_key = f"{node}#replica-{i}"
            val = self._hash(virtual_key)
            idx = bisect.bisect_left(self.ring, val)
            if idx < len(self.ring) and self.ring[idx] == val:
                del self.ring[idx]
                self.ring_map.pop(val, None)

    def get_node(self, key: str) -> Optional[str]:
        """
        Routes the key (e.g. prefix) to the nearest node on the ring.
        """
        if not self.ring:
            return None
        
        val = self._hash(key)
        # Binary search for the first virtual node hash >= key hash
        idx = bisect.bisect_left(self.ring, val)
        
        # If we reached the end of the ring, wrap around to the first node
        if idx == len(self.ring):
            idx = 0
            
        return self.ring_map[self.ring[idx]]

    def get_distribution(self) -> Dict[str, int]:
        """Debugging utility to get the size of key ranges owned by each node on the ring."""
        distribution = {}
        if not self.ring:
            return distribution
        
        # Count hashes owned by each physical node
        for h in self.ring:
            node = self.ring_map[h]
            distribution[node] = distribution.get(node, 0) + 1
        return distribution
