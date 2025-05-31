"""
MinIO Agent - Handles file storage and management using MinIO/S3-compatible storage
"""

import asyncio
from typing import Dict, List, Any, Optional
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.agents.base_agent import BaseAgent, AgentResponse, ArtifactType, AgentCapability
from app.core.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


class MinIOAgent(BaseAgent):
    """
    MinIO Agent for file storage and management operations.
    Handles file uploads, downloads, organization, and metadata management.
    """
    
    def __init__(self):
        # Define capabilities for this agent
        capabilities = [
            AgentCapability(
                name="File Storage Operations",
                description="File storage and management using MinIO/S3-compatible storage",
                artifact_types=[ArtifactType.CODE, ArtifactType.DOCUMENT],
                keywords=["upload", "download", "store", "save", "file", "storage", "manage", "organize", "minio", "s3"],
                examples=["Upload files to storage", "Manage file storage", "Organize files", "S3 operations"]
            )
        ]
        
        super().__init__("MinIO", capabilities)
    
    def get_system_prompt(self) -> str:
        """Return the system prompt for MinIO agent."""
        return """You are a MinIO File Management Agent. You help users with file storage, organization, and management tasks.

Your capabilities include:
- File upload and download operations
- File organization and metadata management
- Storage space optimization
- File permissions and security
- Backup and sync operations
- Object storage best practices

Provide helpful responses about file management operations. If users need to perform actual file operations, guide them through the process and explain what's happening.

Always be practical and provide clear instructions for file management tasks."""
        
    def can_handle(self, user_input: str) -> bool:
        """Check if this agent can handle the user's request."""
        
        # Keywords that indicate file storage/management tasks
        file_keywords = [
            "upload file", "download file", "store file", "save file",
            "file storage", "manage files", "organize files", "file system",
            "bucket", "object storage", "file metadata", "list files",
            "delete file", "move file", "copy file", "file permissions",
            "storage space", "file backup", "file sync", "minio", "s3"
        ]
        
        user_input_lower = user_input.lower()
        
        # Check for direct file management keywords
        if any(keyword in user_input_lower for keyword in file_keywords):
            return True
            
        # Check for file-related actions
        file_actions = ["upload", "download", "store", "save", "organize", "manage"]
        file_objects = ["file", "document", "image", "video", "data", "backup"]
        
        has_action = any(action in user_input_lower for action in file_actions)
        has_object = any(obj in user_input_lower for obj in file_objects)
        
        return has_action and has_object

    async def process_request(self, user_input: str, context: Dict[str, Any] = None, config: Dict[str, Any] = None) -> AgentResponse:
        """Process file storage and management requests."""
        
        try:
            logger.info(f"MinIO Agent processing: {user_input}")
            
            # Generate response using the base class method with streaming support
            response_content = await self.generate_response(user_input, config=config)
            
            # Determine if we need to create file management artifacts
            artifacts = []
            
            # Check if response involves file operations that need artifacts
            response_lower = response_content.lower()
            if any(keyword in response_lower for keyword in ["upload", "organize", "structure", "config", "script"]):
                artifacts.append({
                    "type": ArtifactType.CODE,
                    "title": "File Management Script",
                    "content": self._generate_file_management_script(user_input, response_content),
                    "language": "python"
                })
            
            return AgentResponse(
                success=True,
                content=response_content,
                artifacts=artifacts,
                metadata={
                    "agent": "minio",
                    "capabilities": ["file_storage", "file_management", "object_storage"],
                    "storage_backend": "minio"
                }
            )
            
        except Exception as e:
            logger.error(f"Error in MinIO Agent: {e}")
            return AgentResponse(
                success=False,
                content="",
                artifacts=[],
                metadata={"agent": "minio"},
                error=str(e)
            )
    
    def _generate_file_management_script(self, user_input: str, response_content: str) -> str:
        """Generate a file management script based on the request."""
        
        # Basic MinIO/S3 operations template
        script_template = '''"""
File Management Script for MinIO/S3 Operations
Generated based on: {user_input}
"""

import boto3
from botocore.exceptions import ClientError
import os
from datetime import datetime

# MinIO/S3 Configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
BUCKET_NAME = os.getenv("MINIO_BUCKET", "file-storage")

class FileManager:
    def __init__(self):
        self.client = boto3.client(
            's3',
            endpoint_url=f'http://{MINIO_ENDPOINT}',
            aws_access_key_id=ACCESS_KEY,
            aws_secret_access_key=SECRET_KEY,
            region_name='us-east-1'
        )
    
    def upload_file(self, local_path: str, object_name: str = None):
        """Upload a file to MinIO bucket."""
        if object_name is None:
            object_name = os.path.basename(local_path)
        
        try:
            self.client.upload_file(local_path, BUCKET_NAME, object_name)
            print(f"Successfully uploaded {local_path} to {object_name}")
            return True
        except ClientError as e:
            print(f"Error uploading file: {e}")
            return False
    
    def download_file(self, object_name: str, local_path: str):
        """Download a file from MinIO bucket."""
        try:
            self.client.download_file(BUCKET_NAME, object_name, local_path)
            print(f"Successfully downloaded {object_name} to {local_path}")
            return True
        except ClientError as e:
            print(f"Error downloading file: {e}")
            return False
    
    def list_files(self, prefix: str = ""):
        """List files in the bucket."""
        try:
            response = self.client.list_objects_v2(
                Bucket=BUCKET_NAME,
                Prefix=prefix
            )
            
            if 'Contents' in response:
                files = []
                for obj in response['Contents']:
                    files.append({
                        'name': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified']
                    })
                return files
            return []
        except ClientError as e:
            print(f"Error listing files: {e}")
            return []

# Example usage
if __name__ == "__main__":
    manager = FileManager()
    
    # Example operations based on user request
    # Uncomment the operations you need:
    
    # Upload a file
    # manager.upload_file("path/to/local/file.txt", "remote/path/file.txt")
    
    # Download a file
    # manager.download_file("remote/path/file.txt", "path/to/local/file.txt")
    
    # List files
    # files = manager.list_files()
    # for file in files:
    #     print(f"{file['name']} - {file['size']} bytes")
'''
        
        return script_template.format(user_input=user_input)

    async def get_capabilities(self) -> List[str]:
        """Return list of agent capabilities."""
        return [
            "file_upload",
            "file_download", 
            "file_organization",
            "storage_management",
            "object_storage",
            "file_metadata",
            "file_permissions",
            "backup_operations"
        ] 