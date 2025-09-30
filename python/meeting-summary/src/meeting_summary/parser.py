"""Input file parser for meeting transcription files."""

import re
from typing import List, Dict
from pathlib import Path


class TranscriptionParser:
    """Parser for transcription files in txt and srt formats."""

    def __init__(self):
        self.speaker_pattern = re.compile(
            r"^(?:Speaker\s*)?(\d+)[:\s]*(.*)", re.IGNORECASE
        )
        self.srt_timestamp_pattern = re.compile(r"^\d+$")
        self.srt_time_pattern = re.compile(
            r"^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}$"
        )

    def parse_file(self, file_path: str) -> List[Dict[str, str]]:
        """Parse transcription file and return list of speaker utterances.

        Args:
            file_path: Path to the input file

        Returns:
            List of dictionaries with 'speaker' and 'text' keys
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if file_path.suffix.lower() == ".txt":
            return self._parse_txt(file_path)
        elif file_path.suffix.lower() == ".srt":
            return self._parse_srt(file_path)
        else:
            raise ValueError(
                f"Unsupported file format: {file_path.suffix}. Supported formats: .txt, .srt"
            )

    def _parse_txt(self, file_path: Path) -> List[Dict[str, str]]:
        """Parse txt format transcription file."""
        utterances = []
        current_speaker = None
        current_text = []

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if line starts with speaker identifier
            match = self.speaker_pattern.match(line)
            if match:
                # Save previous utterance if exists
                if current_speaker and current_text:
                    utterances.append(
                        {
                            "speaker": current_speaker,
                            "text": " ".join(current_text).strip(),
                        }
                    )

                # Start new utterance
                current_speaker = f"Speaker {match.group(1)}"
                current_text = [match.group(2).strip()]
            else:
                # Continue current utterance
                if current_speaker:
                    current_text.append(line)

        # Add the last utterance
        if current_speaker and current_text:
            utterances.append(
                {"speaker": current_speaker, "text": " ".join(current_text).strip()}
            )

        return utterances

    def _parse_srt(self, file_path: Path) -> List[Dict[str, str]]:
        """Parse srt format transcription file."""
        utterances = []

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Split by double newlines to get subtitle blocks
        blocks = content.strip().split("\n\n")

        for block in blocks:
            lines = block.split("\n")
            if len(lines) < 3:
                continue

            # Skip index line and timestamp line
            text_lines = lines[2:]
            text = " ".join(text_lines).strip()

            if not text:
                continue

            # Extract speaker from text if present
            speaker = "Unknown Speaker"
            match = self.speaker_pattern.match(text)
            if match:
                speaker = f"Speaker {match.group(1)}"
                text = match.group(2).strip()

            utterances.append({"speaker": speaker, "text": text})

        return utterances

    def get_speakers(self, utterances: List[Dict[str, str]]) -> List[str]:
        """Get unique list of speakers from utterances."""
        speakers = set()
        for utterance in utterances:
            speakers.add(utterance["speaker"])
        return sorted(list(speakers))


def test_parser():
    """Test function for the parser."""
    parser = TranscriptionParser()

    # Test with sample data
    sample_txt = """Speaker 1: Hello everyone, let's start the meeting.
Speaker 2: Good morning. I have some updates on the project.
Speaker 1: Great, please share.
Speaker 2: We've completed the first phase and are ready for testing."""

    # Write sample to file and test
    test_file = "test_meeting.txt"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(sample_txt)

    try:
        result = parser.parse_file(test_file)
        print("Parser test successful:")
        for i, utterance in enumerate(result):
            print(f"{i + 1}. {utterance['speaker']}: {utterance['text']}")
    finally:
        # Clean up
        Path(test_file).unlink(missing_ok=True)


if __name__ == "__main__":
    test_parser()
