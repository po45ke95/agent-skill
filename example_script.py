"""
Example usage of the agent_skill module.
Run: python example_script.py
"""

from agent_skill import task, run_task


@task()
def add(x: int, y: int) -> int:
    return x + y


if __name__ == "__main__":
    print(run_task("add", {"x": 2, "y": 3}))
