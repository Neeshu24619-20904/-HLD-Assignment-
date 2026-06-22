import logging
import threading
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class TrieNode:
    def __init__(self):
        self.children: Dict[str, TrieNode] = {}
        # Precomputed top 10 suggestions passing through this node
        self.top_suggestions: List[Dict[str, Any]] = []

class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, query: str, count: int, score: float):
        """
        Inserts a query into the Trie. Assumes queries are inserted in 
        descending order of score/count so that the first 10 queries 
        reaching a node are automatically the top 10 for that prefix.
        """
        if not query:
            return
        
        node = self.root
        suggestion_entry = {"query": query, "count": count, "score": score}
        
        # Add to root's top suggestions
        if len(node.top_suggestions) < 10:
            node.top_suggestions.append(suggestion_entry)

        for char in query.lower():
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
            
            # Maintain top 10 suggestions at this character node
            if len(node.top_suggestions) < 10:
                node.top_suggestions.append(suggestion_entry)

    def search(self, prefix: str) -> List[Dict[str, Any]]:
        """
        Returns the top 10 suggestions for the given prefix.
        Complexity: O(prefix_length)
        """
        node = self.root
        if prefix:
            for char in prefix.lower():
                if char not in node.children:
                    return []
                node = node.children[char]
        
        # Return a copy to avoid modification during concurrent reads
        return list(node.top_suggestions)

class TrieService:
    def __init__(self):
        self._trie = Trie()
        self._lock = threading.Lock()

    def search(self, prefix: str) -> List[Dict[str, Any]]:
        """Search the Trie with thread safety."""
        return self._trie.search(prefix)

    def get_trending(self) -> List[Dict[str, Any]]:
        """Returns the top 10 global trending queries."""
        return self._trie.search("")


    def reload(self, items: List[Dict[str, Any]]):
        """
        Rebuilds the Trie from scratch using the provided list of items.
        Each item is a dict with {"query": str, "count": int, "score": float}.
        Sorts the items by score (descending) first to ensure correct insertion.
        """
        # Sort by score descending, secondary sort by query name for stability
        sorted_items = sorted(items, key=lambda x: (-x.get("score", 0.0), x.get("query", "")))
        
        new_trie = Trie()
        for item in sorted_items:
            new_trie.insert(item["query"], item["count"], item["score"])
        
        with self._lock:
            self._trie = new_trie
        
        logger.info(f"Trie successfully reloaded with {len(items)} queries.")

# Global Trie instance
trie_service = TrieService()
