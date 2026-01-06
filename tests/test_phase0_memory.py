import os
import json
import unittest
import threading
from core.memory_utils import init_project_memory, load_memory, save_memory, log_project_action, update_memory

class TestPhase0Memory(unittest.TestCase):
    MEMORY_FILE = 'memory.json'

    def setUp(self):
        # Initialize memory for the test project
        self.project_name = "Test_New_Project"
        self.initial_memory = init_project_memory(self.project_name)

    def test_memory_initialization(self):
        # Verify that the memory is initialized correctly
        memory = load_memory(self.project_name)
        self.assertEqual(memory['active_project'], self.project_name)

    def test_log_project_action(self):
        # Log an action and verify it is recorded
        action_type = "create"
        message = "Project created"
        log_project_action(self.project_name, action_type, message)

        # Load memory and check if the action is logged
        memory = load_memory(self.project_name)
        self.assertIn(message, memory['logs'])

    def test_update_memory(self):
        # Update memory and verify the update
        new_description = "Updated project description"
        update_memory(self.project_name, "update", new_description)

        memory = load_memory(self.project_name)
        self.assertEqual(memory['description'], new_description)

    def test_memory_recovery(self):
        # Simulate a failure and recover memory
        original_memory = load_memory(self.project_name)
        save_memory(self.project_name, original_memory)  # Save current state

        # Modify memory and then recover
        new_memory = {"active_project": "Modified_Project"}
        save_memory(self.project_name, new_memory)

        # Recover original memory
        recover_memory = load_memory(self.project_name)
        self.assertEqual(recover_memory, original_memory)

    def test_thread_safety(self):
        # Function to log actions in a thread
        def log_actions():
            for i in range(5):
                log_project_action(self.project_name, "update", f"Action {i}")

        threads = []
        for _ in range(10):  # Create 10 threads
            thread = threading.Thread(target=log_actions)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Load memory and check if all actions are logged
        memory = load_memory(self.project_name)
        self.assertEqual(len(memory['logs']), 50)  # 10 threads * 5 actions each

    def tearDown(self):
        # Clean up after tests
        if os.path.exists(self.MEMORY_FILE):
            os.remove(self.MEMORY_FILE)

if __name__ == '__main__':
    unittest.main()
