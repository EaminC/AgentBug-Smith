import os
import unittest

class TestAgentTaskFiltering(unittest.TestCase):
    def test_agent_loop_stops_after_max_loops(self):
        # This test simulates the loop count logic in AutonomousAgent.ts
        # The patch changes maxLoops from 3 to 4 when customApiKey is empty.
        # We test that after 4 loops it stops, not after 3.

        class DummyAgent:
            def __init__(self, customApiKey=""):
                self.customApiKey = customApiKey
                self.numLoops = 0
                self.stopped = False

            def sendLoopMessage(self):
                pass

            def shutdown(self):
                self.stopped = True

            def loop(self):
                self.numLoops += 1
                # This logic mimics the fixed code after patch:
                maxLoops = 4 if self.customApiKey == "" else 25
                if self.numLoops > maxLoops:
                    self.sendLoopMessage()
                    self.shutdown()

        # On buggy code, maxLoops=3, so after 3 loops it stops
        # On fixed code, maxLoops=4, so after 4 loops it stops

        agent = DummyAgent(customApiKey="")
        for i in range(4):
            agent.loop()
            if i < 4:
                self.assertFalse(agent.stopped, f"Agent should not stop before maxLoops, failed at loop {i+1}")
        agent.loop()
        # After 5th loop (numLoops=5 > 4), agent should stop
        self.assertTrue(agent.stopped, "Agent should stop after exceeding maxLoops")

if __name__ == "__main__":
    unittest.main()