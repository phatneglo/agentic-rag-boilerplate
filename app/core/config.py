"""
Application configuration settings.
"""
from typing import Dict, List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_debug: bool = Field(default=False, env="API_DEBUG")
    api_reload: bool = Field(default=False, env="API_RELOAD")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    api_version: str = Field(default="v1", env="API_VERSION")
    
    # Development Configuration (additional fields from env.example)
    debug: bool = Field(default=False, env="DEBUG")
    reload: bool = Field(default=False, env="RELOAD")
    
    # Database Configuration
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    
    # Redis Configuration
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    
    # Queue Configuration
    queue_prefix: str = Field(default="document_processing", env="QUEUE_PREFIX")
    max_retries: int = Field(default=3, env="MAX_RETRIES")
    job_timeout: int = Field(default=300, env="JOB_TIMEOUT")
    queue_concurrency: int = Field(default=5, env="QUEUE_CONCURRENCY")
    
    # Typesense Configuration
    typesense_host: str = Field(default="localhost", env="TYPESENSE_HOST")
    typesense_port: int = Field(default=8108, env="TYPESENSE_PORT")
    typesense_api_key: str = Field(default="", env="TYPESENSE_API_KEY")
    typesense_protocol: str = Field(default="http", env="TYPESENSE_PROTOCOL")
    
    # Qdrant Configuration
    qdrant_host: str = Field(default="localhost", env="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, env="QDRANT_PORT")
    qdrant_api_key: str = Field(default="", env="QDRANT_API_KEY")
    qdrant_protocol: str = Field(default="http", env="QDRANT_PROTOCOL")
    
    # Service URLs
    document_service_url: str = Field(default="http://localhost:8001", env="DOCUMENT_SERVICE_URL")
    typesense_service_url: str = Field(default="http://localhost:8002", env="TYPESENSE_SERVICE_URL")
    qdrant_service_url: str = Field(default="http://localhost:8003", env="QDRANT_SERVICE_URL")
    
    # External API Keys
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", env="ANTHROPIC_API_KEY")
    
    # Cache Configuration
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")
    cache_max_size: int = Field(default=1000, env="CACHE_MAX_SIZE")
    
    # Email Configuration
    smtp_host: str = Field(default="smtp.gmail.com", env="SMTP_HOST")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_username: str = Field(default="", env="SMTP_USERNAME")
    smtp_password: str = Field(default="", env="SMTP_PASSWORD")
    email_from: str = Field(default="", env="EMAIL_FROM")
    
    # Webhook Configuration
    webhook_secret: str = Field(default="", env="WEBHOOK_SECRET")
    
    # Feature Flags
    enable_document_conversion: bool = Field(default=True, env="ENABLE_DOCUMENT_CONVERSION")
    enable_vector_search: bool = Field(default=True, env="ENABLE_VECTOR_SEARCH")
    enable_typesense_indexing: bool = Field(default=True, env="ENABLE_TYPESENSE_INDEXING")
    enable_qdrant_indexing: bool = Field(default=True, env="ENABLE_QDRANT_INDEXING")
    
    # Document Processing
    upload_dir: str = Field(default="./uploads", env="UPLOAD_DIR")
    processed_dir: str = Field(default="./processed", env="PROCESSED_DIR")
    max_file_size: str = Field(default="50MB", env="MAX_FILE_SIZE")
    allowed_extensions: str = Field(default="pdf,docx,txt,md", env="ALLOWED_EXTENSIONS")
    
    # File Manager Configuration
    file_storage_path: str = Field(default="./file_storage", env="FILE_STORAGE_PATH")
    max_file_size_mb: int = Field(default=100, env="MAX_FILE_SIZE_MB")
    allowed_file_extensions: Optional[str] = Field(
        default=".pdf,.docx,.txt,.md,.html,.jpg,.jpeg,.png,.gif,.csv,.json,.xml,.zip,.rar,.mp3,.mp4,.avi,.mov",
        env="ALLOWED_FILE_EXTENSIONS"
    )
    enable_file_sharing: bool = Field(default=True, env="ENABLE_FILE_SHARING")
    shared_link_expiry_hours: int = Field(default=24, env="SHARED_LINK_EXPIRY_HOURS")
    
    # Security
    secret_key: str = Field(default="your-secret-key-here", env="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    cors_origins: str = Field(default="http://localhost:3000,http://localhost:8000", env="CORS_ORIGINS")
    
    # JWT Authentication Configuration
    jwt_secret_key: str = Field(default="your-super-secret-jwt-key-change-this-in-production", env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")
    
    # Background Tasks
    celery_broker_url: str = Field(default="redis://localhost:6379/1", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/1", env="CELERY_RESULT_BACKEND")
    
    # Monitoring and Logging
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    log_file: str = Field(default="./logs/app.log", env="LOG_FILE")
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")
    metrics_enabled: bool = Field(default=True, env="METRICS_ENABLED")
    
    # Worker Configuration
    worker_concurrency: int = Field(default=2, env="WORKER_CONCURRENCY")
    worker_timeout: int = Field(default=600, env="WORKER_TIMEOUT")
    worker_retry_delay: int = Field(default=5, env="WORKER_RETRY_DELAY")
    
    # Development
    workers: int = Field(default=1, env="WORKERS")
    
    # Testing
    test_database_url: Optional[str] = Field(default=None, env="TEST_DATABASE_URL")
    
    # File Upload Configuration
    max_files_per_request: int = Field(default=10, env="MAX_FILES_PER_REQUEST")
    allowed_file_types: str = Field(default="pdf,doc,docx,txt,md,jpg,jpeg,png,gif,csv,xlsx", env="ALLOWED_FILE_TYPES")
    
    # Object Storage Configuration
    object_storage_provider: str = Field(default="s3", env="OBJECT_STORAGE_PROVIDER")
    object_storage_bucket: str = Field(default="", env="OBJECT_STORAGE_BUCKET")
    object_storage_region: str = Field(default="us-east-1", env="OBJECT_STORAGE_REGION")
    object_storage_access_key: str = Field(default="", env="OBJECT_STORAGE_ACCESS_KEY")
    object_storage_secret_key: str = Field(default="", env="OBJECT_STORAGE_SECRET_KEY")
    object_storage_endpoint_url: Optional[str] = Field(default=None, env="OBJECT_STORAGE_ENDPOINT_URL")
    object_storage_public_url: Optional[str] = Field(default=None, env="OBJECT_STORAGE_PUBLIC_URL")
    
    # File Upload Configuration (legacy - keeping for backward compatibility)
    upload_folder_structure: str = Field(default="year-month-day", env="UPLOAD_FOLDER_STRUCTURE")
    file_manager_base_path: str = Field(default="./file_storage", env="FILE_MANAGER_BASE_PATH")

    @validator("redis_url", pre=True, always=True)
    def build_redis_url(cls, v, values):
        """Build Redis URL if not provided."""
        if v:
            return v
        
        password = values.get("redis_password")
        host = values.get("redis_host", "localhost")
        port = values.get("redis_port", 6379)
        db = values.get("redis_db", 0)
        
        if password:
            return f"redis://:{password}@{host}:{port}/{db}"
        return f"redis://{host}:{port}/{db}"
    
    @validator("allowed_extensions")
    def parse_allowed_extensions(cls, v):
        """Parse allowed extensions into a list."""
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",")]
        return v
    
    @validator("allowed_file_extensions", pre=True)
    def parse_allowed_file_extensions(cls, v):
        """Parse allowed file extensions into a list."""
        if isinstance(v, str):
            return v  # Keep as string, will be parsed in property
        return v
    
    @validator("cors_origins")
    def parse_cors_origins(cls, v):
        """Parse CORS origins into a list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("allowed_file_types")
    def parse_allowed_file_types(cls, v):
        """Parse allowed file types into a list."""
        if isinstance(v, str):
            return [file_type.strip() for file_type in v.split(",")]
        return v
    
    @property
    def typesense_url(self) -> str:
        """Get Typesense URL."""
        return f"{self.typesense_protocol}://{self.typesense_host}:{self.typesense_port}"
    
    @property
    def qdrant_url(self) -> str:
        """Get Qdrant URL."""
        return f"{self.qdrant_protocol}://{self.qdrant_host}:{self.qdrant_port}"
    
    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024
    
    @property
    def allowed_extensions_list(self) -> List[str]:
        """Get allowed file extensions as a list."""
        if isinstance(self.allowed_file_extensions, str):
            return [ext.strip().lower() for ext in self.allowed_file_extensions.split(",")]
        return self.allowed_file_extensions or []
    
    @property
    def queue_names(self) -> Dict[str, str]:
        """Get queue names with prefix."""
        return {
            "document_converter": f"{self.queue_prefix}:document_converter",
            "typesense_indexer": f"{self.queue_prefix}:typesense_indexer",
            "qdrant_indexer": f"{self.queue_prefix}:qdrant_indexer",
            "document_sync": f"{self.queue_prefix}:document_sync",
            "file_manager": f"{self.queue_prefix}:file_manager",
        }
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings 