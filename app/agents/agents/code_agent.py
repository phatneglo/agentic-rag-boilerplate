"""
Code Agent - Specialized for generating code artifacts.
"""

import re
import json
from typing import Dict, Any, List

from app.agents.base_agent import BaseAgent, AgentResponse, AgentCapability, ArtifactType
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class CodeAgent(BaseAgent):
    """
    Agent specialized in generating code artifacts.
    Handles Python, JavaScript, SQL, and other programming languages.
    """
    
    def __init__(self):
        capabilities = [
            AgentCapability(
                name="Python Code Generation",
                description="Generate Python scripts, functions, classes, and utilities",
                artifact_types=[ArtifactType.CODE],
                keywords=[
                    "python", "code", "script", "function", "class", "algorithm",
                    "implementation", "program", "coding", "write code", "create function"
                ],
                examples=[
                    "Write a Python function to sort a list",
                    "Create a class for managing user data",
                    "Generate a script to analyze data"
                ]
            ),
            AgentCapability(
                name="JavaScript Code Generation", 
                description="Generate JavaScript code for web development",
                artifact_types=[ArtifactType.CODE],
                keywords=[
                    "javascript", "js", "web", "frontend", "backend", "node",
                    "react", "vue", "angular", "dom", "api"
                ],
                examples=[
                    "Create a JavaScript function for form validation",
                    "Write a React component",
                    "Generate Node.js API endpoint"
                ]
            ),
            AgentCapability(
                name="SQL Code Generation",
                description="Generate SQL queries and database operations",
                artifact_types=[ArtifactType.CODE],
                keywords=[
                    "sql", "query", "database", "select", "insert", "update",
                    "delete", "join", "table", "mysql", "postgresql"
                ],
                examples=[
                    "Write a SQL query to find top customers",
                    "Create table schema",
                    "Generate complex join query"
                ]
            ),
            AgentCapability(
                name="General Programming",
                description="Generate code in various programming languages",
                artifact_types=[ArtifactType.CODE],
                keywords=[
                    "java", "c++", "c#", "go", "rust", "php", "ruby",
                    "swift", "kotlin", "programming", "coding"
                ],
                examples=[
                    "Write a Java class for data processing",
                    "Create a Go function for concurrency",
                    "Generate C++ algorithm implementation"
                ]
            )
        ]
        
        super().__init__("Code", capabilities)
    
    def get_system_prompt(self) -> str:
        return """You are a Code Agent, an expert programming assistant specialized in generating high-quality code artifacts.

Your capabilities include:
- Writing clean, efficient, and well-documented code
- Supporting multiple programming languages (Python, JavaScript, SQL, Java, C++, etc.)
- Creating functions, classes, algorithms, and complete applications
- Following best practices and coding standards
- Providing explanations and comments in code

When generating code:
1. Write clean, readable code with proper formatting
2. Include helpful comments and docstrings
3. Follow language-specific best practices
4. Handle edge cases and errors appropriately
5. Provide example usage when relevant

Always structure your response as:
1. Brief explanation of what the code does
2. The actual code artifact
3. Usage examples or additional notes if helpful

Focus on creating practical, working code that solves the user's specific requirements."""
    
    def can_handle(self, user_input: str) -> bool:
        """Check if this agent can handle the user request."""
        keywords = self.extract_keywords(user_input)
        
        # Check for programming-related terms
        code_indicators = [
            "code", "function", "script", "program", "algorithm",
            "implementation", "python", "javascript", "sql", "java",
            "write", "create", "generate", "build", "develop"
        ]
        
        user_lower = user_input.lower()
        for indicator in code_indicators:
            if indicator in user_lower:
                return True
        
        return len(keywords) > 0
    
    async def process_request(self, user_input: str, context: Dict[str, Any] = None) -> AgentResponse:
        """Process code generation request."""
        try:
            logger.info(f"Code Agent processing request: {user_input[:100]}...")
            
            # Detect programming language
            language = self._detect_language(user_input)
            
            # Generate code response
            response_content = await self.generate_response(user_input)
            
            # Extract code blocks from response
            code_blocks = self._extract_code_blocks(response_content)
            
            artifacts = []
            for i, code_block in enumerate(code_blocks):
                artifact = self.create_artifact(
                    ArtifactType.CODE,
                    title=f"{language.title()} Code - {self._generate_title(user_input)}",
                    language=code_block.get("language", language),
                    content=code_block["content"],
                    description=self._generate_description(user_input, code_block["content"])
                )
                artifacts.append(artifact)
            
            # If no code blocks found, create one from the entire response
            if not artifacts:
                artifact = self.create_artifact(
                    ArtifactType.CODE,
                    title=f"{language.title()} Code - {self._generate_title(user_input)}",
                    language=language,
                    content=self._clean_code_content(response_content),
                    description=self._generate_description(user_input, response_content)
                )
                artifacts.append(artifact)
            
            response = AgentResponse(
                success=True,
                content=self._clean_response_content(response_content),
                artifacts=artifacts,
                metadata={
                    "agent": self.name,
                    "language": language,
                    "code_blocks_found": len(code_blocks)
                }
            )
            
            return await self.validate_output(response)
            
        except Exception as e:
            logger.error(f"Error in Code Agent: {e}")
            return AgentResponse(
                success=False,
                content="",
                artifacts=[],
                metadata={"agent": self.name},
                error=str(e)
            )
    
    def _detect_language(self, user_input: str) -> str:
        """Detect the programming language from user input."""
        user_lower = user_input.lower()
        
        language_indicators = {
            "python": ["python", "py", "django", "flask", "pandas", "numpy"],
            "javascript": ["javascript", "js", "react", "vue", "angular", "node", "npm"],
            "sql": ["sql", "mysql", "postgresql", "sqlite", "query", "database"],
            "java": ["java", "spring", "maven", "gradle"],
            "cpp": ["c++", "cpp", "cxx"],
            "csharp": ["c#", "csharp", ".net", "dotnet"],
            "go": ["go", "golang"],
            "rust": ["rust", "cargo"],
            "php": ["php", "laravel", "symfony"],
            "ruby": ["ruby", "rails"],
            "swift": ["swift", "ios"],
            "kotlin": ["kotlin", "android"]
        }
        
        for language, indicators in language_indicators.items():
            for indicator in indicators:
                if indicator in user_lower:
                    return language
        
        return "python"  # Default to Python
    
    def _extract_code_blocks(self, content: str) -> List[Dict[str, str]]:
        """Extract code blocks from markdown-formatted content."""
        code_blocks = []
        
        # Pattern for fenced code blocks
        pattern = r'```(\w+)?\n(.*?)\n```'
        matches = re.findall(pattern, content, re.DOTALL)
        
        for language, code in matches:
            code_blocks.append({
                "language": language if language else "text",
                "content": code.strip()
            })
        
        return code_blocks
    
    def _clean_code_content(self, content: str) -> str:
        """Clean and extract code from response content."""
        # Remove markdown formatting and explanatory text
        lines = content.split('\n')
        code_lines = []
        in_code_block = False
        
        for line in lines:
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue
            
            if in_code_block:
                code_lines.append(line)
            elif line.strip() and not line.startswith('#') and not line.startswith('//'):
                # Try to detect if this looks like code
                if any(char in line for char in ['=', '(', ')', '{', '}', ';', ':']):
                    code_lines.append(line)
        
        return '\n'.join(code_lines) if code_lines else content
    
    def _clean_response_content(self, content: str) -> str:
        """Clean response content for display."""
        # Remove code blocks but keep explanatory text
        cleaned = re.sub(r'```\w*\n.*?\n```', '[Code artifact generated]', content, flags=re.DOTALL)
        return cleaned.strip()
    
    def _generate_title(self, user_input: str) -> str:
        """Generate a descriptive title for the code artifact."""
        user_lower = user_input.lower()
        
        if "function" in user_lower:
            return "Function Implementation"
        elif "class" in user_lower:
            return "Class Definition" 
        elif "algorithm" in user_lower:
            return "Algorithm Implementation"
        elif "script" in user_lower:
            return "Script"
        elif "api" in user_lower:
            return "API Implementation"
        elif "query" in user_lower:
            return "Database Query"
        else:
            return "Code Solution"
    
    def _generate_description(self, user_input: str, code_content: str) -> str:
        """Generate a description for the code artifact."""
        lines = len(code_content.split('\n'))
        return f"Generated code solution for: {user_input[:100]}{'...' if len(user_input) > 100 else ''} ({lines} lines)" 