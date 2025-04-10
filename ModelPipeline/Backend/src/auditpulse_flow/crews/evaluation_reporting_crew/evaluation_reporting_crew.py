import os

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool, ScrapeWebsiteTool, WebsiteSearchTool, JSONSearchTool, TXTSearchTool

from crewai.llm import LLM
from ...tools.custom_tool import WrappedScrapeWebsiteTool

@CrewBase
class EvaluationReportingCrew():
    """EvaluationReportingCrew crew"""

    run_id = '000000000'
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    compliance_file_path = './auditpulse_flow/crews/evaluation_reporting_crew/data/compliance.json'
    auditpulse_file_path = './auditpulse_flow/crews/evaluation_reporting_crew/data/AuditPulseInfo.md'
    output_dir = f"./output/{run_id}/evaluation_reporting"
    log_path = "./logs/evaluation_reporting.txt"

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
        },
    }, file_path=auditpulse_file_path)

    llm = LLM(
        model="vertex_ai/gemini-2.0-flash-lite-001",
        max_tokens=3072,
        context_window_size=1000000,
    )

    @agent
    def researcher(self) -> Agent:
        return Agent(
            config=self.agents_config['researcher'],
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
            max_rpm=10,
            cache=True,
			max_iter=5,
            max_retry_limit=20
        )

    @agent
    def reporting_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['reporting_analyst'],
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
            max_rpm=10,
            cache=True,
			max_iter=5,
            max_retry_limit=20
        )

    @task
    def evidence_evaluation_task(self) -> Task:
        return Task(
            config=self.tasks_config['evidence_evaluation_task'],
            async_execution=False,
            agent=self.researcher(),
            output_file=os.path.join(self.output_dir, 'evidence_evaluation_task.md'),
        )

    @task
    def misstatement_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['misstatement_analysis_task'],
            async_execution=False,
            agent=self.researcher(),
            context=[self.evidence_evaluation_task()],
            output_file=os.path.join(self.output_dir, 'misstatement_analysis_task.md'),
        )

    @task
    def conclusion_formation_task(self) -> Task:
        return Task(
            config=self.tasks_config['conclusion_formation_task'],
            async_execution=False,
            agent=self.reporting_analyst(),
            context=[self.misstatement_analysis_task()],
            output_file=os.path.join(self.output_dir, 'conclusion_formation_task.md'),
        )

    @task
    def audit_report_drafting_task(self) -> Task:
        return Task(
            config=self.tasks_config['audit_report_drafting_task'],
            async_execution=False,
            agent=self.reporting_analyst(),
            context=[self.conclusion_formation_task()],
            output_file=os.path.join(self.output_dir, 'audit_report_drafting_task.md'),
        )

    @crew
    def crew(self) -> Crew:
        """Creates the EvaluationReportingCrew crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            verbose=True,
            output_log_file=self.log_path
        )
