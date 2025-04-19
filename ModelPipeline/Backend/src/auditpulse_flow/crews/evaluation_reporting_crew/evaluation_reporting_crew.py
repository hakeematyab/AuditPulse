import os

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool, ScrapeWebsiteTool, WebsiteSearchTool, JSONSearchTool, TXTSearchTool

from crewai.llm import LLM
from ...tools.custom_tool import WrappedScrapeWebsiteTool

@CrewBase
class EvaluationReportingCrew():
    """EvaluationReportingCrew crew"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    compliance_file_path = './auditpulse_flow/data/compliance.json'
    auditpulse_file_path = './auditpulse_flow/data/AuditPulseInfo.md'
    output_dir = "./output/{run_id}/evaluation_reporting"
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
    },json_path=compliance_file_path)

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
        },
        file_path=auditpulse_file_path)

    llm = LLM(
            model="vertex_ai/gemini-2.0-flash-lite-001",
            max_tokens=3072,
            context_window_size=1000000,
        )
    @agent
    def audit_evaluation_reporting_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['audit_evaluation_reporting_agent'],
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
            max_rpm=45,
            cache=True,
            max_iter=5,
            max_retry_limit=20
        )

    @task
    def evidence_evaluation_task(self) -> Task:
        return Task(
            config=self.tasks_config['evidence_evaluation_and_misstatement_assessment'],
            async_execution=False,
            agent=self.audit_evaluation_reporting_agent(),
            output_file=os.path.join(self.output_dir,'evidence_evaluation_task.md'),
        )

    @task
    def financial_statement_compliance_task(self) -> Task:
        return Task(
            config=self.tasks_config['financial_statement_compliance_evaluation'],
            async_execution=False,
            agent=self.audit_evaluation_reporting_agent(),
            context=[self.evidence_evaluation_task()],
            output_file=os.path.join(self.output_dir,'financial_statement_compliance_task.md'),
        )

    @task
    def going_concern_task(self) -> Task:
        return Task(
            config=self.tasks_config['going_concern_and_viability_assessment'],
            async_execution=False,
            agent=self.audit_evaluation_reporting_agent(),
            context=[self.financial_statement_compliance_task()],
            output_file=os.path.join(self.output_dir,'going_concern_task.md'),
        )

    @task
    def audit_opinion_task(self) -> Task:
        return Task(
            config=self.tasks_config['audit_opinion_formulation_and_reporting'],
            async_execution=False,
            agent=self.audit_evaluation_reporting_agent(),
            context=[self.going_concern_task()],
            output_file=os.path.join(self.output_dir,'audit_opinion_task.md'),
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