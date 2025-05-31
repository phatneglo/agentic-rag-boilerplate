"""
Document Agent - Specialized for generating document artifacts.
"""

import re
from typing import Dict, Any, List

from app.agents.base_agent import BaseAgent, AgentResponse, AgentCapability, ArtifactType
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class DocumentAgent(BaseAgent):
    """
    Agent specialized in generating document artifacts.
    Handles reports, guides, documentation, and structured content.
    """
    
    def __init__(self):
        capabilities = [
            AgentCapability(
                name="Technical Documentation",
                description="Create technical guides, API docs, and manuals",
                artifact_types=[ArtifactType.DOCUMENT, ArtifactType.HTML],
                keywords=[
                    "documentation", "guide", "manual", "tutorial", "api",
                    "readme", "technical", "instructions", "how-to"
                ],
                examples=[
                    "Create API documentation",
                    "Write a user manual",
                    "Generate technical guide"
                ]
            ),
            AgentCapability(
                name="Business Reports",
                description="Generate business reports and formal documents",
                artifact_types=[ArtifactType.DOCUMENT],
                keywords=[
                    "report", "proposal", "business", "executive", "summary",
                    "plan", "strategy", "presentation", "memo"
                ],
                examples=[
                    "Create business proposal",
                    "Write executive summary",
                    "Generate project report"
                ]
            ),
            AgentCapability(
                name="Content Writing",
                description="Create articles, blogs, and general content",
                artifact_types=[ArtifactType.DOCUMENT, ArtifactType.HTML],
                keywords=[
                    "article", "blog", "content", "write", "essay",
                    "story", "copy", "marketing", "description"
                ],
                examples=[
                    "Write a blog post",
                    "Create marketing content",
                    "Generate article outline"
                ]
            )
        ]
        
        super().__init__("Document", capabilities)
    
    def get_system_prompt(self) -> str:
        return """You are a Document Agent, an expert in creating structured, well-formatted documents.

Your capabilities include:
- Writing technical documentation and guides
- Creating business reports and proposals
- Generating articles and content
- Structuring information clearly and logically
- Using appropriate formatting and style

When creating documents:
1. Use clear, logical structure with headings and sections
2. Write in appropriate tone for the audience
3. Include relevant details and examples
4. Use proper formatting (markdown, HTML as needed)
5. Ensure content is comprehensive and useful

Document types you can create:
- Technical documentation (API docs, manuals, guides)
- Business documents (reports, proposals, plans)
- Content pieces (articles, blogs, marketing copy)
- Structured content (outlines, frameworks, templates)

Always structure your response as:
1. Brief introduction to the document
2. Well-organized content with clear sections
3. Conclusion or summary when appropriate

Focus on creating valuable, well-structured content that serves the user's specific needs."""
    
    def can_handle(self, user_input: str) -> bool:
        """Check if this agent can handle the user request."""
        keywords = self.extract_keywords(user_input)
        user_lower = user_input.lower()
        
        # Very specific document creation indicators (explicit document requests)
        explicit_document_requests = [
            "write a document", "create a document", "draft a document",
            "generate a document", "write a report", "create a report",
            "write a guide", "create a guide", "write documentation",
            "create documentation", "write an article", "create an article",
            "write a proposal", "create a proposal", "write a manual",
            "create a manual", "draft a report", "generate a report"
        ]
        
        # Check for explicit document requests first
        for request in explicit_document_requests:
            if request in user_lower:
                return True
        
        # Strong single-word indicators that suggest formal document creation
        strong_single_indicators = ["documentation", "proposal", "manual"]
        for indicator in strong_single_indicators:
            if indicator in user_lower:
                return True
        
        # More restrictive check for ambiguous words
        ambiguous_indicators = ["write", "create", "generate", "draft"]
        document_context_words = [
            "document", "report", "guide", "article", "blog post", 
            "documentation", "manual", "proposal", "plan", "summary"
        ]
        
        # Only trigger if we have both an action word AND a clear document type
        has_action = any(action in user_lower for action in ambiguous_indicators)
        has_document_type = any(doc_type in user_lower for doc_type in document_context_words)
        
        if has_action and has_document_type:
            # Additional check: avoid triggering for simple examples or explanations
            simple_request_patterns = [
                "example of", "show me", "what is", "how to", "can you",
                "please", "just", "simple", "basic", "quick"
            ]
            
            # If it looks like asking for a simple example rather than document creation
            is_simple_request = any(pattern in user_lower for pattern in simple_request_patterns)
            
            if is_simple_request:
                # Only create document if it's very explicitly requested
                explicit_phrases = [
                    "write a complete", "create a full", "generate a detailed",
                    "draft a formal", "create a comprehensive"
                ]
                return any(phrase in user_lower for phrase in explicit_phrases)
            
            return True
        
        # Don't handle conversational or example requests
        conversational_patterns = [
            "hi", "hello", "hey", "how are you", "what's up", "thanks", "thank you",
            "cool", "nice", "good", "great", "awesome", "ok", "okay", "yes", "no",
            "example", "show me", "tell me", "explain", "what is", "how does"
        ]
        
        for pattern in conversational_patterns:
            if pattern in user_lower:
                return False
        
        return False
    
    async def process_request(self, user_input: str, context: Dict[str, Any] = None, config: Dict[str, Any] = None) -> AgentResponse:
        """Process document generation request."""
        try:
            logger.info(f"Document Agent processing request: {user_input[:100]}...")
            
            # Detect document type
            doc_type = self._detect_document_type(user_input)
            
            # Generate document response with streaming support
            response_content = await self.generate_response(
                user_input,
                self._get_specialized_prompt(doc_type),
                config=config
            )
            
            # Create document artifact
            document_artifact = self._create_document_artifact(user_input, response_content, doc_type)
            
            artifacts = [document_artifact]
            
            response = AgentResponse(
                success=True,
                content=self._format_document_summary(response_content),
                artifacts=artifacts,
                metadata={
                    "agent": self.name,
                    "document_type": doc_type,
                    "sections": self._extract_sections(response_content)
                }
            )
            
            return await self.validate_output(response)
            
        except Exception as e:
            logger.error(f"Error in Document Agent: {e}")
            return AgentResponse(
                success=False,
                content="",
                artifacts=[],
                metadata={"agent": self.name},
                error=str(e)
            )
    
    def _detect_document_type(self, user_input: str) -> str:
        """Detect the type of document requested."""
        user_lower = user_input.lower()
        
        type_indicators = {
            "technical": ["api", "documentation", "technical", "manual", "guide", "tutorial"],
            "business": ["report", "proposal", "business", "executive", "plan", "strategy"],
            "content": ["article", "blog", "content", "copy", "marketing", "story"],
            "academic": ["essay", "research", "paper", "study", "analysis"],
            "procedural": ["instructions", "how-to", "steps", "procedure", "workflow"]
        }
        
        for doc_type, indicators in type_indicators.items():
            for indicator in indicators:
                if indicator in user_lower:
                    return doc_type
        
        return "general"
    
    def _get_specialized_prompt(self, doc_type: str) -> str:
        """Get specialized prompt based on document type."""
        base_prompt = self.get_system_prompt()
        
        type_specific_prompts = {
            "technical": "\n\nFocus on technical accuracy, clear explanations, and practical examples. Use appropriate technical terminology and include code examples where relevant.",
            "business": "\n\nMaintain professional tone, include executive summary, use business terminology, and focus on actionable insights and recommendations.",
            "content": "\n\nWrite engaging, reader-friendly content with clear structure. Include compelling headlines and maintain appropriate tone for the target audience.",
            "academic": "\n\nUse formal academic tone, include proper structure with introduction, body, and conclusion. Support statements with reasoning and examples.",
            "procedural": "\n\nProvide clear, step-by-step instructions. Use numbered lists, include prerequisites, and ensure steps are actionable and easy to follow."
        }
        
        return base_prompt + type_specific_prompts.get(doc_type, "")
    
    def _create_document_artifact(self, user_input: str, content: str, doc_type: str) -> Dict[str, Any]:
        """Create structured document artifact."""
        
        # Extract sections from content
        sections = self._parse_document_sections(content)
        
        # Determine output format
        output_format = "html" if self._should_use_html(doc_type, content) else "markdown"
        
        artifact = self.create_artifact(
            ArtifactType.HTML if output_format == "html" else ArtifactType.DOCUMENT,
            title=self._generate_title(user_input, doc_type),
            content=content,
            format=output_format,
            sections=sections,
            metadata={
                "document_type": doc_type,
                "word_count": len(content.split()),
                "section_count": len(sections)
            }
        )
        
        return artifact
    
    def _parse_document_sections(self, content: str) -> List[Dict[str, str]]:
        """Parse document content into sections."""
        sections = []
        lines = content.split('\n')
        current_section = None
        current_content = []
        
        for line in lines:
            # Check for markdown headers
            if line.startswith('#'):
                if current_section and current_content:
                    sections.append({
                        "title": current_section,
                        "content": '\n'.join(current_content).strip()
                    })
                
                # Extract header title
                current_section = line.lstrip('#').strip()
                current_content = []
            else:
                current_content.append(line)
        
        # Add last section
        if current_section and current_content:
            sections.append({
                "title": current_section,
                "content": '\n'.join(current_content).strip()
            })
        
        return sections
    
    def _should_use_html(self, doc_type: str, content: str) -> bool:
        """Determine if HTML format should be used."""
        # Use HTML for complex formatting or business documents
        html_indicators = ["<", ">", "table", "style", "class"]
        
        if doc_type in ["business", "technical"] and any(indicator in content for indicator in html_indicators):
            return True
        
        return False
    
    def _extract_sections(self, content: str) -> List[str]:
        """Extract section titles from content."""
        sections = []
        for line in content.split('\n'):
            if line.startswith('#'):
                title = line.lstrip('#').strip()
                if title:
                    sections.append(title)
        return sections
    
    def _generate_title(self, user_input: str, doc_type: str) -> str:
        """Generate title for document artifact."""
        type_titles = {
            "technical": "Technical Documentation",
            "business": "Business Document",
            "content": "Content Document",
            "academic": "Academic Document",
            "procedural": "Procedure Guide",
            "general": "Document"
        }
        
        base_title = type_titles.get(doc_type, "Document")
        
        # Try to extract subject from user input
        if any(word in user_input.lower() for word in ["for", "about", "on"]):
            # Extract topic
            patterns = [
                r'(?:for|about|on)\s+(.+?)(?:\.|$|,)',
                r'(?:write|create|generate)\s+(?:a|an)?\s*(.+?)(?:\s+for|\s+about|$)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, user_input, re.IGNORECASE)
                if match:
                    subject = match.group(1).strip()[:50]
                    return f"{base_title}: {subject}"
        
        return base_title
    
    def _format_document_summary(self, content: str) -> str:
        """Format a brief summary of the document."""
        lines = content.split('\n')
        
        # Extract first paragraph or meaningful content
        summary_lines = []
        for line in lines:
            if line.strip() and not line.strip().startswith('#'):
                summary_lines.append(line.strip())
                if len(' '.join(summary_lines)) > 200:
                    break
        
        summary = ' '.join(summary_lines)
        
        if len(summary) > 300:
            summary = summary[:297] + "..."
        
        word_count = len(content.split())
        section_count = len(self._extract_sections(content))
        
        return f"Document created with {word_count} words and {section_count} sections. {summary} [Full document available in artifact]" 