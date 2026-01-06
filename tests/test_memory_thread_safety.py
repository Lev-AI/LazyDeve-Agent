import threading
import time
import random
from core.project_manager import commit_project

# Number of concurrent threads
NUM_THREADS = 10
# Number of commits each thread will make
COMMITS_PER_THREAD = 5

def simulate_commit(thread_id):
    for _ in range(COMMITS_PER_THREAD):
        message = f"Commit from thread {thread_id}"
        commit_project(message)
        time.sleep(random.uniform(0.1, 0.5))  # Simulate some delay

def run_concurrent_commits():
    threads = []
    for i in range(NUM_THREADS):
        thread = threading.Thread(target=simulate_commit, args=(i,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

if __name__ == "__main__":
    run_concurrent_commits()
