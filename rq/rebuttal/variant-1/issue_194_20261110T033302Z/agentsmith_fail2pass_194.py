import unittest
import os
from agentscope.message import Msg, Tht
from agentscope.memory import TemporaryMemory


class TemporaryMemoryTest(unittest.TestCase):
    """
    Test cases for TemporaryMemory focusing on loading JSON/dict memory
    and ensuring memory objects are Msg or subclasses, not plain dicts.
    """

    def setUp(self) -> None:
        self.memory = TemporaryMemory()
        self.file_name_1 = "tmp_mem_file1.txt"
        self.file_name_2 = "tmp_mem_file2.txt"
        self.msg_1 = Msg("user", "Hello", role="user")
        self.msg_2 = Msg(
            "agent",
            "Hello! How can I help you?",
            role="assistant",
        )
        self.msg_3 = Msg(
            "user",
            "Translate the following sentence",
            role="assistant",
        )
        self.invalid = {"invalid_key": "invalid_value"}

    def tearDown(self) -> None:
        """Clean up files after tests."""
        if os.path.exists(self.file_name_1):
            os.remove(self.file_name_1)
        if os.path.exists(self.file_name_2):
            os.remove(self.file_name_2)

    def test_add_and_type_conversion(self) -> None:
        """Test that dicts are converted to Msg and added properly."""
        self.memory.add(self.msg_1)
        self.assertEqual(
            self.memory.get_memory(),
            [self.msg_1],
        )

        # Add list of Msg objects
        self.memory.add([self.msg_2, self.msg_3])
        self.assertEqual(
            self.memory.get_memory(),
            [self.msg_1, self.msg_2, self.msg_3],
        )

        # Add dict with 'name' and 'content' keys, should convert to Msg
        dict_msg = {"name": "user", "content": "Hello from dict"}
        self.memory.add(dict_msg)
        mem = self.memory.get_memory()
        self.assertEqual(len(mem), 4)
        self.assertIsInstance(mem[-1], Msg)
        self.assertEqual(mem[-1].name, "user")
        self.assertEqual(mem[-1].content, "Hello from dict")

    def test_add_invalid_dict_raises(self) -> None:
        """Adding dict without required keys should raise ValueError."""
        with self.assertRaises(ValueError) as context:
            self.memory.add(self.invalid)
        self.assertIn("Cannot add", str(context.exception))

    def test_load_and_export_memory_objects(self) -> None:
        """
        Test loading memory from list of Msg objects and exporting returns Msg objects,
        not plain dicts.
        """
        memory = TemporaryMemory()
        user_input = Msg(name="user", content="Hello")
        agent_input = Msg(
            name="agent",
            content="Hello! How can I help you?",
        )
        memory.load([user_input, agent_input])
        retrieved_mem = memory.export(to_mem=True)
        self.assertEqual(len(retrieved_mem), 2)
        self.assertIsInstance(retrieved_mem[0], Msg)
        self.assertIsInstance(retrieved_mem[1], Msg)
        self.assertEqual(retrieved_mem[0].name, "user")
        self.assertEqual(retrieved_mem[1].name, "agent")

        # Export to file and reload, memory objects remain Msg instances
        memory.export(file_path=self.file_name_1)
        memory.clear()
        self.assertEqual(memory.get_memory(), [])
        memory.load(self.file_name_1)
        mem_after_load = memory.get_memory()
        self.assertEqual(len(mem_after_load), 2)
        self.assertIsInstance(mem_after_load[0], Msg)
        self.assertIsInstance(mem_after_load[1], Msg)
        self.assertEqual(mem_after_load[0].name, "user")
        self.assertEqual(mem_after_load[1].name, "agent")

    def test_tht_memory_add_export_load(self) -> None:
        """
        Test TemporaryMemory with Tht message type:
        add, export, clear, and load.
        """
        memory = TemporaryMemory()
        thought = Tht("testing")
        memory.add(thought)

        self.assertEqual(
            memory.get_memory(),
            [thought],
        )

        memory.export(file_path=self.file_name_2)
        memory.clear()
        self.assertEqual(
            memory.get_memory(),
            [],
        )
        memory.load(self.file_name_2)
        mem_after_load = memory.get_memory()
        self.assertEqual(len(mem_after_load), 1)
        self.assertIsInstance(mem_after_load[0], Tht)
        self.assertEqual(mem_after_load[0].content, "testing")


if __name__ == "__main__":
    unittest.main()
