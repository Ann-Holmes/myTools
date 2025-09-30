"""Main entry point for the meeting summary tool."""

import argparse
import logging
import sys

from dotenv import load_dotenv

from .parser import TranscriptionParser
from .translator import Translator
from .summarizer import MeetingSummarizer
from .utils import validate_file_path


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration.

    Args:
        verbose: Enable verbose logging if True
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="AI-powered meeting transcription summary tool"
    )

    parser.add_argument(
        "--input", "-i", required=True, help="Input file path (txt or srt format)"
    )

    parser.add_argument(
        "--basename", "-b", required=True, help="Base name for output files"
    )

    parser.add_argument(
        "--model", "-m", help="OpenAI model to use (default: from environment)"
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    parser.add_argument(
        "--skip-translation",
        action="store_true",
        help="Skip translation and only generate summaries",
    )

    return parser.parse_args()


def main() -> None:
    """Main function."""
    args = parse_arguments()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    try:
        # Load environment variables
        logger.info("Loading environment variables...")
        load_dotenv()

        # Validate input file
        validate_file_path(args.input)

        # Parse input file
        logger.info("Parsing input file: %s", args.input)
        parser = TranscriptionParser()
        utterances = parser.parse_file(args.input)
        logger.info(
            "Parsed %d utterances from %d speakers",
            len(utterances),
            len(parser.get_speakers(utterances)),
        )

        # Translate utterances
        if not args.skip_translation:
            logger.info("Starting translation...")
            translator = Translator()
            translated_utterances = translator.translate_utterances(utterances)

            # Save translated text
            translated_output = f"{args.basename}_translated.txt"
            translator.save_translated_text(translated_utterances, translated_output)
            logger.info("Translation saved to: %s", translated_output)
        else:
            logger.info("Skipping translation as requested")
            translated_utterances = utterances

        # Generate summaries
        logger.info("Generating meeting summaries...")
        summarizer = MeetingSummarizer()

        # Chinese summary
        chinese_summary = summarizer.generate_summary(utterances, "zh")
        chinese_output = f"{args.basename}_summary_zh.md"
        summarizer.save_summary(chinese_summary, chinese_output)
        logger.info("Chinese summary saved to: %s", chinese_output)

        # English summary
        english_summary = summarizer.generate_summary(utterances, "en")
        english_output = f"{args.basename}_summary_en.md"
        summarizer.save_summary(english_summary, english_output)
        logger.info("English summary saved to: %s", english_output)

        logger.info("Meeting summary processing completed successfully!")
        print("\nOutput files created:")
        if not args.skip_translation:
            print(f"  - {args.basename}_translated.txt")
        print(f"  - {args.basename}_summary_zh.md")
        print(f"  - {args.basename}_summary_en.md")

    except Exception as e:
        logger.error("Error processing meeting summary: %s", str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
