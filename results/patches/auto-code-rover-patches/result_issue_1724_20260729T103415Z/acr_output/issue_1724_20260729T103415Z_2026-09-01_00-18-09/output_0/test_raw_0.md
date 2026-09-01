```python
# reproducer.py

import asyncio
import sys

def print_stacktrace(e: Exception):
    import traceback
    tb = traceback.extract_tb(e.__traceback__)
    print("Traceback (most recent call last):", file=sys.stderr)
    for frame in tb:
        line_number = frame.lineno
        code_context = frame.line.strip() if frame.line else "Unknown"
        print(f'  File "{frame.filename}"', file=sys.stderr)
        print(f"    {line_number}: {code_context}", file=sys.stderr)
    print(f"{e.__class__.__name__}: {e}", file=sys.stderr)


async def main():
    # Delayed import to isolate errors
    from agentscope.tool import Toolkit, ToolGroup

    # Dummy minimal skill loader for testing
    # Will return skill info based on path
    async def dummy_skill_loader(path: str):
        # Identify group by path
        if "repair" in path:
            return {
                "realme-repair-progress": {
                    "name": "realme-repair-progress",
                    "description": "Query and display realme device repair order progress..."
                }
            }
        elif "order" in path:
            return {
                "order-status-query": {
                    "name": "order-status-query",
                    "description": "Provide full-process order and logistics status query service..."
                }
            }
        elif "basic" in path:
            return {
                "basic-skill": {
                    "name": "basic-skill",
                    "description": "Basic group skill example."
                }
            }
        else:
            return {}

    # We patch the Toolkit._load_skill_loader method to hook into dummy loader
    # because Toolkit uses "skills_or_loaders" which normally load from files
    # For this reproducer, we define skills_or_loaders as strings to denote groups,
    # and monkey-patch _load_skill_loader to supply dummy_skill_loader to them.

    # Save original
    original_load_skill_loader = Toolkit._load_skill_loader

    async def patched_load_skill_loader(self, loader_ref):
        # loader_ref is from skills_or_loaders list, a string that is group tag
        # Use dummy_skill_loader for known group tags
        if loader_ref in ("./skills/repair", "./skills/order", "./skills/basic"):
            return dummy_skill_loader(loader_ref)
        # fallback
        return await original_load_skill_loader(self, loader_ref)

    Toolkit._load_skill_loader = patched_load_skill_loader

    # Define tool groups as per reproduction steps
    tool_groups = [
        ToolGroup(
            name="repair",
            description="Repair query",
            tools=[],  # empty for reproducer
            skills_or_loaders=["./skills/repair"],
        ),
        ToolGroup(
            name="order",
            description="Order query",
            tools=[],
            skills_or_loaders=["./skills/order"],
        ),
        ToolGroup(
            name="basic",
            description="Basic skills",
            tools=[],
            skills_or_loaders=["./skills/basic"],
        ),
    ]

    toolkit = Toolkit(tool_groups=tool_groups)

    # Get skill instructions WITHOUT passing groups parameter (the buggy way)
    # The bug: only "basic" group's skills are collected by default (buggy)
    instructions = await toolkit.get_skill_instructions()
    # We expect instructions to include all groups' skill names, but only basic should be there if buggy
    # Check if string "realme-repair-progress" or "order-status-query" appear in instructions
    # If yes, issue is fixed; if no, issue present

    # If instructions is None or empty, treat as issue present
    if instructions is None or instructions.strip() == "":
        raise AssertionError("No skill instructions returned at all")

    skills_in_output = instructions.lower()
    repair_present = "realme-repair-progress" in skills_in_output
    order_present = "order-status-query" in skills_in_output
    basic_present = "basic-skill" in skills_in_output

    # According to issue description:
    # bug: only "basic" group skills appear → repair_present and order_present == False
    # fix: all of them appear → repair_present and order_present == True

    # So we raise if bug present:
    if not (repair_present and order_present):
        raise AssertionError(
            f"Skill instructions missing some groups: repair_present={repair_present}, order_present={order_present}, basic_present={basic_present}\n"
            f"Instructions:\n{instructions}"
        )

    # Also test _get_available_tools behavior
    # _get_available_tools expects groups param, test without groups to simulate the bug behavior
    tools = await toolkit._get_available_tools(groups=[])
    skill_viewer_name = toolkit.builtin_skill_viewer.tool.name

    # The bug: skill_viewer tool may be absent or not properly injected if skills from other groups missing
    # Valid fix means skill_viewer exists if skills exist in all groups

    if skill_viewer_name not in tools:
        raise AssertionError(
            f"SkillViewer tool {skill_viewer_name} missing from available_tools: {list(tools.keys())}"
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print_stacktrace(e)
        sys.exit(1)
    sys.exit(0)
```
