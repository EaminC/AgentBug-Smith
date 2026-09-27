import unittest
from pydantic import BaseModel, Field

from agentscope.models import ModelResponse
from agentscope.parsers import MarkdownJsonDictParser


class ModelResponseParserTest(unittest.TestCase):
    """Test MarkdownJsonDictParser with Pydantic schema for type validation."""

    def setUp(self) -> None:
        """Set up example responses and expected results."""
        self.res_dict_bool = ModelResponse(
            text=(
                "```json\n"
                '{"speak": "Hello, world!", '
                '"thought": "xxx", '
                '"end_discussion": true}\n```'
            ),
        )
        self.res_dict_str_bool = ModelResponse(
            text=(
                "```json\n"
                '{\n'
                '  "speak": "Hello, world!",\n'
                '  "thought": "xxx",\n'
                '  "end_discussion": "true"\n'
                '}\n'
                "```"
            ),
        )
        self.gt_dict = {
            "speak": "Hello, world!",
            "thought": "xxx",
            "end_discussion": True,
        }

    def test_parse_with_pydantic_schema(self) -> None:
        """Test parsing with Pydantic schema validates and normalizes types."""

        class Schema(BaseModel):
            speak: str = Field(description="what you speak")
            thought: str = Field(description="what you thought")
            end_discussion: bool = Field(description="whether the discussion reached an agreement or not")

        parser = MarkdownJsonDictParser(
            content_hint=Schema,
            keys_to_memory=["speak", "thought"],
            keys_to_content="speak",
            keys_to_metadata=["end_discussion"],
        )

        # The format_instruction should include the schema JSON
        self.assertIn("The generated JSON dictionary MUST follow this schema", parser.format_instruction)
        self.assertIn("'type': 'boolean'", parser.format_instruction)

        # Parsing a response with boolean true should produce expected dict
        res = parser.parse(self.res_dict_bool)
        self.assertDictEqual(res.parsed, self.gt_dict)

        # Parsing a response with string "true" should also produce expected dict (bool True)
        res2 = parser.parse(self.res_dict_str_bool)
        self.assertDictEqual(res2.parsed, self.gt_dict)

        # The to_metadata method should return the boolean True for end_discussion
        metadata = parser.to_metadata(res2.parsed)
        self.assertIsInstance(metadata["end_discussion"], bool)
        self.assertTrue(metadata["end_discussion"])


if __name__ == "__main__":
    unittest.main()
