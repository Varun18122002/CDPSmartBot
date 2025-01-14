from typing import List, Optional
from app.services.search_service import SearchService
from app.services.cache_service import CacheService
from app.schemas.search import SearchResult

class ChatService:
    def __init__(
        self,
        search_service: SearchService,
        cache_service: CacheService
    ):
        self.search_service = search_service
        self.cache_service = cache_service
        
        # Define response templates
        self.templates = {
            "how_to": "Here's how to {action} in {platform}:\n\n{steps}",
            "not_found": "I couldn't find specific information about how to {action} in {platform}. Could you please rephrase your question or ask about a different topic?",
            "non_cdp": "I specialize in answering questions about CDP platforms (Segment, mParticle, Lytics, and Zeotap). Your question seems to be about something else. Could you please ask a CDP-related question?",
            "error": "I apologize, but I encountered an error while processing your request. Please try asking your question again."
        }

    async def get_response(self, query: str, platform: str) -> str:
        """Generate a response for the user's query"""
        # Check cache first
        cached_response = await self.cache_service.get_response(query, platform)
        if cached_response:
            return cached_response

        # Validate and process the query
        if not self._is_cdp_related(query, platform):
            return self.templates["non_cdp"]

        # Extract the main action from the query
        action = self._extract_action(query)
        
        # Search for relevant documentation
        try:
            search_results = await self.search_service.search(query, platform, top_k=3)
            if not search_results:
                return self.templates["not_found"].format(
                    action=action,
                    platform=platform
                )
            
            # Format response from search results
            response = self._format_response(search_results, action, platform)
            
            # Cache the response
            await self.cache_service.store_response(query, platform, response)
            
            return response
            
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            return self.templates["error"]

    def _is_cdp_related(self, query: str, platform: str) -> bool:
        """Check if the query is related to CDP platforms"""
        cdp_keywords = [
            "segment", "mparticle", "lytics", "zeotap",
            "source", "destination", "integration", "track",
            "identify", "audience", "profile", "data", "sdk",
            "api", "webhook", "event"
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in cdp_keywords)

    def _extract_action(self, query: str) -> str:
        """Extract the main action from the query"""
        # Remove common question starters
        query = query.lower().replace("how do i ", "").replace("how to ", "")
        query = query.replace("how can i ", "").replace("what is the way to ", "")
        
        # Return the cleaned action
        return query.strip()

    def _format_response(
        self,
        search_results: List[SearchResult],
        action: str,
        platform: str
    ) -> str:
        """Format the response using search results"""
        # Combine relevant information from search results
        if not search_results:
            return self.templates["not_found"].format(
                action=action,
                platform=platform
            )

        # Extract steps from the most relevant result
        main_content = search_results[0].content
        
        # Format supplementxary information from other results
        supplementary_info = ""
        if len(search_results) > 1:
            relevant_points = self._extract_relevant_points(search_results[1:])
            if relevant_points:
                supplementary_info = "\n\nAdditional tips:\n" + relevant_points

        # Format the final response
        response = self.templates["how_to"].format(
            action=action,
            platform=platform,
            steps=main_content
        )
        
        if supplementary_info:
            response += supplementary_info

        return response

    def _extract_relevant_points(self, results: List[SearchResult]) -> str:
        """Extract relevant points from secondary search results"""
        points = []
        for result in results:
            # Extract key sentences that add value
            sentences = result.content.split('. ')
            for sentence in sentences:
                if self._is_relevant_point(sentence):
                    points.append(f"• {sentence.strip()}")
                    
        return "\n".join(points[:3])  # Limit to top 3 points

    def _is_relevant_point(self, sentence: str) -> bool:
        """Check if a sentence contains relevant information"""
        important_keywords = ["note", "important", "ensure", "remember", "tip", "best practice"]
        return any(keyword in sentence.lower() for keyword in important_keywords)