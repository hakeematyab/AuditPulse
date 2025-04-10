import os

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool, ScrapeWebsiteTool, WebsiteSearchTool, JSONSearchTool, TXTSearchTool

from crewai.llm import LLM
from ...tools.custom_tool import WrappedScrapeWebsiteTool

@CrewBase
class AuditPlanningCrew():
    """AuditPlanningCrew crew"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    compliance_file_path = './auditpulse_flow/crews/audit_planning_crew/data/compliance.json'
    auditpulse_file_path = './auditpulse_flow/crews/audit_planning_crew/data/AuditPulseInfo.md'
    output_dir = "./output/{run_id}/audit_planning"
    log_path = './logs/audit_planning.txt'

    pcaob_guidlines_tool = JSONSearchTool(config={
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
		}},
        file_path=auditpulse_file_path)

    llm = LLM(
        model="vertex_ai/gemini-2.0-flash-lite-001",
        max_tokens=3072,
        context_window_size=1000000,
    )
    def task_limit_context(self, task_output):
        context_len = 1_000_000
        n_tasks = 2
        max_chars = int((context_len*3.3)/n_tasks)
        task_output.raw = task_output.raw[:max_chars]
        return True, task_output

    @agent
    def audit_planning_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['audit_planning_agent'],
            verbose=True,
            tools=[
                SerperDevTool(n_results=5),
                WrappedScrapeWebsiteTool(),
                self.website_search_tool,
                self.pcaob_guidlines_tool,
                self.auditpulse_file_tool
            ],
            llm=self.llm,
            respect_context_window=True,
            max_rpm=30,
            cache=True,
			max_iter=5,
            max_retry_limit=20
        )

    @task
    def preliminary_engagement_task(self) -> Task:
        return Task(
            config=self.tasks_config['preliminary_engagement_review'],
            async_execution=False,
            agent=self.audit_planning_agent(),
            guardrail=self.task_limit_context,
            output_file=os.path.join(self.output_dir, 'preliminary_engagement_task.md'),
        )

    @task
    def business_risk_task(self) -> Task:
        return Task(
            config=self.tasks_config['business_risk_and_fraud_assessment'],
            async_execution=False,
            agent=self.audit_planning_agent(),
            guardrail=self.task_limit_context,
            output_file=os.path.join(self.output_dir, 'business_risk_task.md'),
        )

    @task
    def internal_control_task(self) -> Task:
        return Task(
            config=self.tasks_config['internal_control_system_evaluation'],
            async_execution=False,
            agent=self.audit_planning_agent(),
            context=[self.preliminary_engagement_task(), self.business_risk_task()],
            output_file=os.path.join(self.output_dir, 'internal_control_task.md'),
        )

    @task
    def audit_strategy_task(self) -> Task:
        return Task(
            config=self.tasks_config['audit_strategy_and_team_allocation'],
            async_execution=False,
            agent=self.audit_planning_agent(),
            context=[self.internal_control_task()],
            output_file=os.path.join(self.output_dir, 'audit_strategy_task.md'),
        )

    @crew
    def crew(self) -> Crew:
        """Creates the AuditPlanningCrew crew"""

        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            verbose=True,
            output_log_file=self.log_path
        )
