"""Semantic vector search and knowledge-graph tools."""
import json
from jarvis.core.tool_registry import BaseTool
from jarvis.memory import embeddings, knowledge_graph


class SemanticRecall(BaseTool):
    name = "semantic_recall"
    description = (
        "Recall memories by meaning, not just keywords. Uses vector embeddings to find "
        "semantically similar memories. Use this when you want to find memories that "
        "RELATE to a topic even if the exact words differ."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer", "default": 8},
        },
        "required": ["query"],
    }

    def run(self, query: str, max_results: int = 8) -> str:
        try:
            results = embeddings.vector_search(query, k=max_results)
            return json.dumps({"query": query, "memories": results, "count": len(results)})
        except Exception as e:
            return json.dumps({"error": str(e)})


class AddKnowledgeRelation(BaseTool):
    name = "add_knowledge_relation"
    description = (
        "Record a relationship between two entities in the knowledge graph. "
        "Example: source='Alice', source_type='person', target='Acme Corp', "
        "target_type='company', relation='works_at'."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "source": {"type": "string"},
            "source_type": {"type": "string", "description": "person|project|company|place|thing"},
            "target": {"type": "string"},
            "target_type": {"type": "string"},
            "relation": {"type": "string", "description": "e.g. works_at, knows, owns, located_in, part_of"},
        },
        "required": ["source", "source_type", "target", "target_type", "relation"],
    }

    def run(self, source: str, source_type: str, target: str, target_type: str, relation: str) -> str:
        try:
            rid = knowledge_graph.add_relation(source, source_type, target, target_type, relation)
            return json.dumps({"success": True, "relation_id": rid})
        except Exception as e:
            return json.dumps({"error": str(e)})


class QueryKnowledgeGraph(BaseTool):
    name = "query_knowledge_graph"
    description = "Look up an entity in the knowledge graph and get all its relationships."
    input_schema = {
        "type": "object",
        "properties": {
            "entity": {"type": "string", "description": "Entity name to look up"},
        },
        "required": ["entity"],
    }

    def run(self, entity: str) -> str:
        try:
            result = knowledge_graph.query_entity(entity)
            if not result:
                return json.dumps({"found": False, "entity": entity})
            return json.dumps(result)
        except Exception as e:
            return json.dumps({"error": str(e)})
