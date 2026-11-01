"""保持既有评测导入路径；本地模型实现在基础设施层复用。"""
from app.infrastructure.embedding.local_model import (
    MODEL, ENCODING_VERSION, LocalMultilingualEmbedding, model_files, model_version,
)

__all__ = ["MODEL", "ENCODING_VERSION", "LocalMultilingualEmbedding", "model_files", "model_version"]
