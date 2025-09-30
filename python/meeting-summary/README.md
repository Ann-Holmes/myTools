# Meeting Summary Tool

AI-powered meeting transcription summary tool that processes English meeting transcripts and generates Chinese translations and comprehensive summaries.

## Features

- **Input Support**: Process both .txt and .srt format transcription files
- **Translation**: Convert English transcripts to Chinese while preserving speaker labels
- **Smart Summarization**: Generate comprehensive meeting summaries in both Chinese and English
- **Role Recognition**: Automatically identify and label potential speaker roles
- **Structured Output**: Produce well-organized summary documents with key meeting insights

## Installation

```bash
# Install using uv tool
uv tool install .

# Or install dependencies manually
uv sync
```

## Usage

```bash
# Basic usage
meeting-summary --input meeting.txt --basename output

# With custom model
meeting-summary --input meeting.srt --basename meeting_output --model gpt-4o-mini
```

## Environment Variables

### Option 1: Using .env file (Recommended for development)

Create a `.env` file with your OpenAI API configuration:

```bash
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini  # Optional
```

### Option 2: Using export command (Recommended for uv tool)

When using `uv tool install`, it's recommended to set environment variables directly:

```bash
export OPENAI_API_KEY=your_openai_api_key_here
export OPENAI_BASE_URL=https://api.openai.com/v1
export OPENAI_MODEL=gpt-4o-mini  # Optional
```

### Supported Models

The tool supports any OpenAI-compatible API, including:
- OpenAI models (gpt-4o, gpt-4o-mini, etc.)
- DeepSeek models (deepseek-chat, deepseek-coder, etc.)
- Other OpenAI-compatible APIs

## Output Files

The tool generates three output files:

1. `{basename}_translated.txt` - Chinese translation of the original transcript
2. `{basename}_summary_zh.md` - Chinese meeting summary
3. `{basename}_summary_en.md` - English meeting summary

## Development

```bash
# Install development dependencies
uv sync --extra dev

# Run linting and formatting
uv run ruff check .
uv run ruff format .

```

## License

MIT License
