"""Utility functions for the meeting summary tool."""

import os
from dotenv import load_dotenv


def load_environment() -> None:
    """Load environment variables from .env file.

    This function searches for .env files in multiple locations:
    1. Current working directory (./.env)
    2. User's home directory (~/.meeting-summary/.env)
    3. Project directory (if running from source)
    """
    # Try current working directory first
    current_env = "./.env"
    if os.path.exists(current_env) and load_dotenv(current_env):
        return

    # Try user's home directory
    home_env = os.path.expanduser("~/.meeting-summary/.env")
    if os.path.exists(home_env) and load_dotenv(home_env):
        return

    # Try to find project directory
    try:
        import meeting_summary

        project_dir = os.path.dirname(os.path.dirname(meeting_summary.__file__))
        project_env = os.path.join(project_dir, ".env")
        if os.path.exists(project_env) and load_dotenv(project_env):
            return
    except (ImportError, AttributeError):
        pass

    # If no .env file found, just load from current directory (default behavior)
    load_dotenv("./.env")


def get_openai_config() -> dict:
    """Get OpenAI configuration from environment variables.

    Returns:
        Dictionary with OpenAI configuration
    """
    # Try to load environment variables first
    load_environment()

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable is not set. "
            "Please set it in your .env file or environment variables."
        )

    return {"api_key": api_key, "base_url": base_url, "model": model}


def validate_file_path(file_path: str) -> None:
    """Validate that the file path exists and is readable.

    Args:
        file_path: Path to the file to validate

    Raises:
        FileNotFoundError: If file does not exist
        PermissionError: If file is not readable
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    if not os.access(file_path, os.R_OK):
        raise PermissionError(f"File is not readable: {file_path}")


def create_output_filename(basename: str, suffix: str) -> str:
    """Create output filename with proper suffix.

    Args:
        basename: Base name for the output file
        suffix: Suffix to add to the filename

    Returns:
        Complete output filename
    """
    return f"{basename}_{suffix}"


def format_speaker_utterances(utterances: list) -> str:
    """Format speaker utterances for LLM processing.

    Args:
        utterances: List of dictionaries with 'speaker' and 'text' keys

    Returns:
        Formatted string of speaker utterances
    """
    formatted = []
    for utterance in utterances:
        formatted.append(f"{utterance['speaker']}: {utterance['text']}")
    return "\n".join(formatted)
