from abc import ABC, abstractmethod

class BaseParserAdapter(ABC):
    @abstractmethod
    async def parse_document(self, file_bytes: bytes, file_name: str) -> str:
        """Parses a document (PDF, DOCX, PPTX) and returns structured Markdown text."""
        pass
