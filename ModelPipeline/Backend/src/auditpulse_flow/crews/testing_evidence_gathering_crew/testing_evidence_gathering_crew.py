import os

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool, ScrapeWebsiteTool, WebsiteSearchTool, JSONSearchTool, TXTSearchTool

from crewai.llm import LLM
from ...tools.custom_tool import WrappedScrapeWebsiteTool


@CrewBase
class TestingEvidenceGatheringCrew():
    """TestingEvidenceGatheringCrew crew"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    compliance_file_path = './auditpulse_flow/crews/testing_evidence_crew/data/compliance.json'
    auditpulse_file_path = './auditpulse_flow/crews/testing_evidence_crew/data/AuditPulseInfo.md'
    output_dir = "./output/testing_evidence"
    log_path = "./logs/testing_evidence.txt"

    pcaob_guidelines_tool = JSONSearchTool(config={
        "llm": {
            "provider": "vertexai",
            "config": {
                "model": "gemini-2.0-flash-lite-001",
            },
        },
        "embedder": {
            "provider": "vertexai",
            "config": {
                "model": "text-embedding-004",
            },
        },
    }, json_path=compliance_file_path)

    website_search_tool = WebsiteSearchTool(config={
        "llm": {
            "provider": "vertexai",
            "config": {
                "model": "gemini-2.0-flash-lite-001",
            },
        },
        "embedder": {
            "provider": "vertexai",
            "config": {
                "model": "text-embedding-004",
            },
        },
    })

    auditpulse_file_tool = TXTSearchTool(config={
        "llm": {
            "provider": "vertexai",
            "config": {
                "model": "gemini-2.0-flash-lite-001",
            },
        },
        "embedder": {
            "provider": "vertexai",
            "config": {
                "model": "text-embedding-004",
            },
        },
    }, file_path=auditpulse_file_path)

    llm = LLM(
        model="vertex_ai/gemini-2.0-flash-lite-001",
        max_tokens=3072,
        context_window_size=1000000,
    )

    def task_limit_context(self, task_output):
        context_len = 1_000_000
        n_tasks = 3
        max_chars = int((context_len*3.3)/n_tasks)
        task_output.raw = task_output.raw[:max_chars]
        return True, task_output
    
    @agent
    def substantive_testing_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['substantive_testing_agent'],
            verbose=True,
            tools=[
                SerperDevTool(n_results=5),
                WrappedScrapeWebsiteTool(),
                self.website_search_tool,
                self.pcaob_guidelines_tool,
                self.auditpulse_file_tool
            ],
            llm=self.llm,
            respect_context_window=True,
            max_rpm=10,
            cache=True,
			max_iter=5,
            max_retry_limit=20
        )

    @agent
    def control_testing_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['control_testing_agent'],
            verbose=True,
            tools=[
                SerperDevTool(n_results=5),
                WrappedScrapeWebsiteTool(),
                self.website_search_tool,
                self.pcaob_guidelines_tool,
                self.auditpulse_file_tool
            ],
            llm=self.llm,
            respect_context_window=True,
            max_rpm=10,
            cache=True,
			max_iter=5,
            max_retry_limit=20
        )

    @agent
    def analytical_procedures_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['analytical_procedures_agent'],
            verbose=True,
            tools=[
                SerperDevTool(n_results=5),
                WrappedScrapeWebsiteTool(),
                self.website_search_tool,
                self.pcaob_guidelines_tool,
                self.auditpulse_file_tool
            ],
            llm=self.llm,
            respect_context_window=True,
            max_rpm=10,
            cache=True,
			max_iter=5,
            max_retry_limit=20
        )

    @agent
    def evidence_documentation_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['evidence_documentation_agent'],
            verbose=True,
            tools=[
                SerperDevTool(n_results=5),
                WrappedScrapeWebsiteTool(),
                self.website_search_tool,
                self.pcaob_guidelines_tool,
                self.auditpulse_file_tool
            ],
            llm=self.llm,
            respect_context_window=True,
            max_rpm=10,
            cache=True,
			max_iter=5,
            max_retry_limit=20
        )

    @task
    def substantive_testing_task(self) -> Task:
        return Task(
            config=self.tasks_config['substantive_testing_task'],
            async_execution=False,
            agent=self.substantive_testing_agent(),
            guardrail=self.task_limit_context,
            output_file=os.path.join(self.output_dir, 'substantive_testing_task.md'),
        )

    @task
    def control_testing_task(self) -> Task:
        return Task(
            config=self.tasks_config['control_testing_task'],
            async_execution=False,
            agent=self.control_testing_agent(),
            guardrail=self.task_limit_context,
            output_file=os.path.join(self.output_dir, 'control_testing_task.md'),
        )

    @task
    def analytical_procedures_task(self) -> Task:
        return Task(
            config=self.tasks_config['analytical_procedures_task'],
            async_execution=False,
            agent=self.analytical_procedures_agent(),
            guardrail=self.task_limit_context,
            output_file=os.path.join(self.output_dir, 'analytical_procedures_task.md'),
        )

    @task
    def evidence_documentation_task(self) -> Task:
        return Task(
            config=self.tasks_config['evidence_documentation_task'],
            async_execution=False,
            agent=self.evidence_documentation_agent(),
            context=[self.substantive_testing_task(), self.control_testing_task(), self.analytical_procedures_task()],
            output_file=os.path.join(self.output_dir, 'evidence_documentation_task.md'),
        )

    @crew
    def crew(self) -> Crew:
        """Creates the TestingEvidenceGatheringCrew crew"""
        return Crew(
            agents=self.agents,  # Automatically created by the @agent decorator
            tasks=self.tasks,  # Automatically created by the @task decorator
            process=Process.sequential,  # Tasks will be executed sequentially in this phase.
			verbose=True,
			output_log_file=self.log_path  # Log all outputs for debugging and tracking.
		)
