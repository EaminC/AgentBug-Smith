The issue describes that the knowledge of the crew is not passed to the planning process handler. The planning agent should have access to this knowledge during the planning phase to influence planning decisions.

The key parts to fix are:

1. Modify the `Crew._handle_crew_planning` method to pass the crew's knowledge or the crew itself to the `CrewPlanner` so that the planner has access to it.

2. Modify the `CrewPlanner` to accept this new parameter (knowledge or crew) and store it.

3. When creating the planning agent inside `CrewPlanner._create_planning_agent`, assign the knowledge object or knowledge_sources from the crew to the planning agent. This will inject the knowledge context into the planning agent.

From the provided context, the practical way is to pass the entire crew to `CrewPlanner` because it contains knowledge as an internal private attribute (`_knowledge`) and the knowledge sources. Passing the crew object is simple and gives flexibility.

Then, in `CrewPlanner`, store it, and when creating the planning agent, if the crew's knowledge is present, assign it to the agent's knowledge.

With these changes, the knowledge will be included when the planning agent is created, thus included in the planning process.

---

Patch:

# modification 1: modify Crew._handle_crew_planning to pass `crew=self` to CrewPlanner

# modification 2: modify CrewPlanner.__init__ to accept crew param and store it

# modification 3: modify CrewPlanner._create_planning_agent to assign knowledge if available from crew to the created Agent

---

```
<file>src/crewai/crew.py</file>
<original>    def _handle_crew_planning(self):
        """Handles the Crew planning."""
        self._logger.log("info", "Planning the crew execution")
        result = CrewPlanner(
            tasks=self.tasks, planning_agent_llm=self.planning_llm
        )._handle_crew_planning()

        for task, step_plan in zip(self.tasks, result.list_of_plans_per_task):
            task.description += step_plan.plan
</original>
<patched>    def _handle_crew_planning(self):
        """Handles the Crew planning."""
        self._logger.log("info", "Planning the crew execution")
        result = CrewPlanner(
            tasks=self.tasks, planning_agent_llm=self.planning_llm, crew=self
        )._handle_crew_planning()

        for task, step_plan in zip(self.tasks, result.list_of_plans_per_task):
            task.description += step_plan.plan
</patched>
</file>

<file>src/crewai/utilities/planning_handler.py</file>
<original>24 class CrewPlanner:
25     def __init__(self, tasks: List[Task], planning_agent_llm: Optional[Any] = None):
26         self.tasks = tasks
27 
28         if planning_agent_llm is None:
29             self.planning_agent_llm = "gpt-4o-mini"
30         else:
31             self.planning_agent_llm = planning_agent_llm
</original>
<patched>24 class CrewPlanner:
25     def __init__(
26         self,
27         tasks: List[Task],
28         planning_agent_llm: Optional[Any] = None,
29         crew: Optional["Crew"] = None,
30     ):
31         self.tasks = tasks
32         self.crew = crew
33
34         if planning_agent_llm is None:
35             self.planning_agent_llm = "gpt-4o-mini"
36         else:
37             self.planning_agent_llm = planning_agent_llm
</patched>
</file>

<file>src/crewai/utilities/planning_handler.py</file>
<original>47     def _create_planning_agent(self) -> Agent:
48         """Creates the planning agent for the crew planning."""
49         return Agent(
50             role="Task Execution Planner",
51             goal=(
52                 "Your goal is to create an extremely detailed, step-by-step plan based on the tasks and tools "
53                 "available to each agent so that they can perform the tasks in an exemplary manner"
54             ),
55             backstory="Planner agent for crew planning",
56             llm=self.planning_agent_llm,
57         )
</original>
<patched>47     def _create_planning_agent(self) -> Agent:
48         """Creates the planning agent for the crew planning."""
49         planning_agent = Agent(
50             role="Task Execution Planner",
51             goal=(
52                 "Your goal is to create an extremely detailed, step-by-step plan based on the tasks and tools "
53                 "available to each agent so that they can perform the tasks in an exemplary manner"
54             ),
55             backstory="Planner agent for crew planning",
56             llm=self.planning_agent_llm,
57         )
58
59         # Assign knowledge sources if knowledge present on crew
60         if self.crew and hasattr(self.crew, "_knowledge") and self.crew._knowledge:
61             planning_agent.knowledge = self.crew._knowledge
62
63         return planning_agent
</patched>
</file>
