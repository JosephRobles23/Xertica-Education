from abc import ABC, abstractmethod

class BaseAudioAdapter(ABC):
    @abstractmethod
    async def text_to_speech(self, text: str, output_path: str) -> float:
        """
        Synthesizes text to speech, saves it to output_path, and returns its duration in seconds.
        """
        pass
