# app/services/search_service.py
from typing import List, Dict, Optional
import numpy as np
import faiss
from elasticsearch import AsyncElasticsearch
from app.core.config import settings
from app.schemas.search import SearchResult, DocumentChunk
from sentence_transformers import SentenceTransformer

class SearchService:
    def __init__(self):
        # Initialize Elasticsearch client
        self.es = AsyncElasticsearch(
            hosts=[f"{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}"]
        )
        
        # Initialize FAISS index
        self.dimension = settings.VECTOR_DIMENSION
        self.index = faiss.IndexFlatL2(self.dimension)
        
        # Initialize sentence transformer for embeddings
        self.encoder = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')

    async def search(self, query: str, platform: str, top_k: int = 3) -> List[SearchResult]:
        """
        Hybrid search combining Elasticsearch and FAISS
        """
        # Get query embedding
        query_embedding = self.encoder.encode(query)

        # Parallel execution of both searches
        semantic_results = await self._semantic_search(query_embedding, platform, top_k)
        keyword_results = await self._keyword_search(query, platform, top_k)

        # Combine and rank results
        combined_results = self._combine_search_results(
            semantic_results,
            keyword_results
        )

        return combined_results

    async def _semantic_search(
        self,
        query_embedding: np.ndarray,
        platform: str,
        top_k: int
    ) -> List[SearchResult]:
        """
        Perform semantic search using FAISS
        """
        # Search in FAISS
        D, I = self.index.search(
            np.array([query_embedding]).astype('float32'),
            top_k
        )

        # Fetch document details from Elasticsearch using document IDs
        results = []
        for idx, distance in zip(I[0], D[0]):
            if idx != -1:  # Valid index
                doc = await self.es.get(
                    index=f"{platform.lower()}_docs",
                    id=str(idx)
                )
                results.append(
                    SearchResult(
                        content=doc['_source']['content'],
                        platform=platform,
                        score=1 / (1 + distance),  # Convert distance to similarity score
                        doc_type=doc['_source'].get('doc_type', 'general'),
                        section=doc['_source'].get('section', '')
                    )
                )
        return results

    async def _keyword_search(
        self,
        query: str,
        platform: str,
        top_k: int
    ) -> List[SearchResult]:
        """
        Perform keyword-based search using Elasticsearch
        """
        # Build search query
        search_query = {
            "bool": {
                "must": [
                    {
                        "match": {
                            "content": {
                                "query": query,
                                "operator": "and"
                            }
                        }
                    },
                    {
                        "term": {
                            "platform.keyword": platform.lower()
                        }
                    }
                ]
            }
        }

        # Add boost for title and section matches
        should_clauses = [
            {
                "match_phrase": {
                    "title": {
                        "query": query,
                        "boost": 2
                    }
                }
            },
            {
                "match_phrase": {
                    "section": {
                        "query": query,
                        "boost": 1.5
                    }
                }
            }
        ]
        search_query["bool"]["should"] = should_clauses

        # Execute search
        response = await self.es.search(
            index=f"{platform.lower()}_docs",
            query=search_query,
            size=top_k
        )

        # Process results
        results = []
        for hit in response['hits']['hits']:
            results.append(
                SearchResult(
                    content=hit['_source']['content'],
                    platform=platform,
                    score=hit['_score'],
                    doc_type=hit['_source'].get('doc_type', 'general'),
                    section=hit['_source'].get('section', '')
                )
            )
        return results

    def _combine_search_results(
        self,
        semantic_results: List[SearchResult],
        keyword_results: List[SearchResult],
        semantic_weight: float = 0.5
    ) -> List[SearchResult]:
        """
        Combine and rank results from both search methods
        """
        # Create a dictionary to store combined scores
        combined_scores = {}

        # Process semantic search results
        for result in semantic_results:
            combined_scores[result.content] = {
                'result': result,
                'score': result.score * semantic_weight
            }

        # Process keyword search results
        keyword_weight = 1 - semantic_weight
        for result in keyword_results:
            if result.content in combined_scores:
                combined_scores[result.content]['score'] += result.score * keyword_weight
            else:
                combined_scores[result.content] = {
                    'result': result,
                    'score': result.score * keyword_weight
                }

        # Sort and return combined results
        sorted_results = sorted(
            combined_scores.values(),
            key=lambda x: x['score'],
            reverse=True
        )
        return [item['result'] for item in sorted_results]

    async def index_document(self, doc: DocumentChunk) -> None:
        """
        Index a document chunk in both Elasticsearch and FAISS
        """
        # Generate embedding
        embedding = self.encoder.encode(doc.content)

        # Add to FAISS
        self.index.add(np.array([embedding]).astype('float32'))
        doc_id = str(self.index.ntotal - 1)  # Use FAISS index as document ID

        # Add to Elasticsearch
        await self.es.index(
            index=f"{doc.platform.lower()}_docs",
            id=doc_id,
            document={
                'content': doc.content,
                'platform': doc.platform.lower(),
                'doc_type': doc.doc_type,
                'section': doc.section,
                'title': doc.title,
                'url': doc.url
            }
        )

    async def close(self):
        """
        Cleanup resources
        """
        await self.es.close()

# app/schemas/search.py
from pydantic import BaseModel, Field
from typing import Optional

class SearchResult(BaseModel):
    content: str
    platform: str
    score: float
    doc_type: str
    section: Optional[str] = None

class DocumentChunk(BaseModel):
    content: str
    platform: str
    doc_type: str = "general"
    section: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None