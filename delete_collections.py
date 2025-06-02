#!/usr/bin/env python3
"""Delete both Typesense and Qdrant collections for fresh start."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import typesense
from qdrant_client import QdrantClient
from app.core.config import settings

# Delete Typesense collection
try:
    typesense_client = typesense.Client({
        'nodes': [{'host': settings.typesense_host, 'port': settings.typesense_port, 'protocol': settings.typesense_protocol}],
        'api_key': settings.typesense_api_key
    })
    typesense_client.collections[settings.typesense_collection_name].delete()
    print(f'✅ Deleted Typesense collection: {settings.typesense_collection_name}')
except Exception as e:
    print(f'⚠️ Typesense collection not found or already deleted: {e}')

# Delete Qdrant collection
try:
    qdrant_client = QdrantClient(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        api_key=settings.qdrant_api_key,
        https=False,
        prefer_grpc=False,
    )
    qdrant_client.delete_collection(settings.qdrant_collection_name)
    print(f'✅ Deleted Qdrant collection: {settings.qdrant_collection_name}')
except Exception as e:
    print(f'⚠️ Qdrant collection not found or already deleted: {e}')

print("🧹 Collections deleted. Ready for fresh start!") 