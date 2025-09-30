"""Translation module for meeting transcripts."""

import logging
from openai import OpenAI
from .utils import get_openai_config

logger = logging.getLogger(__name__)


class Translator:
    """Translator for meeting transcripts."""

    def __init__(self):
        """Initialize translator with OpenAI client."""
        self.client = None
        self.model = None

    def _ensure_client_initialized(self):
        """Ensure OpenAI client is initialized."""
        if self.client is None:
            config = get_openai_config()
            self.client = OpenAI(api_key=config["api_key"], base_url=config["base_url"])
            self.model = config["model"]

    def translate_utterances(self, utterances: list) -> list:
        """Translate speaker utterances from English to Chinese.

        Args:
            utterances: List of dictionaries with 'speaker' and 'text' keys

        Returns:
            List of translated utterances with same structure
        """
        logger.info("Starting translation of %d utterances", len(utterances))

        translated_utterances = []

        for utterance in utterances:
            try:
                translated_text = self._translate_text(utterance["text"])
                translated_utterances.append(
                    {"speaker": utterance["speaker"], "text": translated_text}
                )
                logger.debug("Translated utterance from %s", utterance["speaker"])
            except Exception as e:
                logger.error(
                    "Failed to translate utterance from %s: %s",
                    utterance["speaker"],
                    str(e),
                )
                # Keep original text if translation fails
                translated_utterances.append(utterance)

        logger.info("Translation completed successfully")
        return translated_utterances

    def _translate_text(self, text: str) -> str:
        """Translate individual text using OpenAI.

        Args:
            text: English text to translate

        Returns:
            Chinese translation
        """
        self._ensure_client_initialized()

        prompt = f"""
请将以下英文文本准确翻译成中文。保持专业术语和会议内容的准确性：

{text}

中文翻译：
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的会议翻译助手，擅长将英文会议内容准确翻译成中文，保持专业术语和会议语境的准确性。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=2000,
        )

        return response.choices[0].message.content.strip()

    def save_translated_text(self, utterances: list, output_path: str) -> None:
        """Save translated utterances to file.

        Args:
            utterances: List of translated utterances
            output_path: Path to save the translated text
        """
        with open(output_path, "w", encoding="utf-8") as f:
            for utterance in utterances:
                f.write(f"{utterance['speaker']}: {utterance['text']}\n\n")

        logger.info("Translated text saved to: %s", output_path)
