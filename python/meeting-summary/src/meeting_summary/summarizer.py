"""Meeting summarization module."""

import logging
from openai import OpenAI
from .utils import get_openai_config, format_speaker_utterances

logger = logging.getLogger(__name__)


class MeetingSummarizer:
    """Summarizer for meeting transcripts."""

    def __init__(self):
        """Initialize summarizer with OpenAI client."""
        self.client = None
        self.model = None

    def _ensure_client_initialized(self):
        """Ensure OpenAI client is initialized."""
        if self.client is None:
            config = get_openai_config()
            self.client = OpenAI(api_key=config["api_key"], base_url=config["base_url"])
            self.model = config["model"]

    def generate_summary(self, utterances: list, language: str = "zh") -> str:
        """Generate meeting summary in specified language.

        Args:
            utterances: List of speaker utterances
            language: Language for summary ('zh' for Chinese, 'en' for English)

        Returns:
            Formatted meeting summary
        """
        logger.info("Generating %s meeting summary", language)

        formatted_utterances = format_speaker_utterances(utterances)

        if language == "zh":
            return self._generate_chinese_summary(formatted_utterances)
        else:
            return self._generate_english_summary(formatted_utterances)

    def _generate_chinese_summary(self, formatted_utterances: str) -> str:
        """Generate Chinese meeting summary."""
        self._ensure_client_initialized()

        prompt = f"""
请根据以下会议对话内容，生成一份结构化的中文会议纪要。请包括以下部分：

1. 总体概括：会议主题和主要讨论点
2. 参会人数：基于说话人数量统计
3. 工作进展：已完成的工作和当前状态
4. 下一步计划：具体的行动项和负责人（如果可能）
5. 优先级评估：各项任务的紧急程度
6. 角色分析：基于对话内容分析可能的角色分工

会议对话内容：
{formatted_utterances}

请生成结构清晰、内容完整的中文会议纪要：
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是一个专业的会议纪要撰写助手，擅长从会议对话中提取关键信息，"
                        "生成结构清晰、内容完整的会议纪要。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=3000,
        )

        return response.choices[0].message.content.strip()

    def _generate_english_summary(self, formatted_utterances: str) -> str:
        """Generate English meeting summary."""
        self._ensure_client_initialized()

        prompt = f"""
Please generate a structured meeting summary in English based on the following conversation. Include the following sections:

1. Overall Summary: Meeting theme and main discussion points
2. Participants: Number of speakers based on the conversation
3. Work Progress: Completed work and current status
4. Next Steps: Specific action items and responsible parties (if identifiable)
5. Priority Assessment: Urgency level of each task
6. Role Analysis: Potential role assignments based on conversation content

Meeting conversation:
{formatted_utterances}

Please generate a well-structured, comprehensive meeting summary in English:
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional meeting summary assistant, skilled at "
                        "extracting key information from meeting conversations and "
                        "generating well-structured, comprehensive meeting summaries."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=3000,
        )

        return response.choices[0].message.content.strip()

    def save_summary(self, summary: str, output_path: str) -> None:
        """Save meeting summary to file.

        Args:
            summary: Meeting summary text
            output_path: Path to save the summary
        """
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(summary)

        logger.info("Meeting summary saved to: %s", output_path)
