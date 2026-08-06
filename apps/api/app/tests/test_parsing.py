import unittest

from app.utils.parsing import parse_file_bytes


class ParsingTests(unittest.TestCase):
    def test_parse_file_bytes_decodes_text_materials(self) -> None:
        parsed = parse_file_bytes(
            b"# Demo\n\nArchitecture notes",
            filename="demo.md",
            content_type="text/markdown",
        )

        self.assertIn("Architecture notes", parsed)


if __name__ == "__main__":
    unittest.main()
