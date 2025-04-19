import os

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool, ScrapeWebsiteTool, WebsiteSearchTool, JSONSearchTool, TXTSearchTool

from crewai.llm import LLM
from ...tools.custom_tool import WrappedScrapeWebsiteTool

@CrewBase
class TestingEvidenceGatheringCrew():
    """TestingAndEvidenceCrew crew"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    compliance_file_path = './auditpulse_flow/data/compliance.json'
    auditpulse_file_path = './auditpulse_flow/data/AuditPulseInfo.md'
    output_dir = "./output/{run_id}/testing_evidence"
    log_path = "./logs/testing_evidence.txt"

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
    def testing_and_evidence_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['testing_and_evidence_agent'],
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
    def control_testing_task(self) -> Task:
        return Task(
            config=self.tasks_config['control_testing_assessment'],
            async_execution=False,
            agent=self.testing_and_evidence_agent(),
            output_file=os.path.join(self.output_dir,'control_testing_task.md'),
        )

    @task
    def financial_statement_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['financial_statement_analysis'],
            async_execution=False,
            agent=self.testing_and_evidence_agent(),
            context=[self.control_testing_task()],
            output_file=os.path.join(self.output_dir,'financial_statement_analysis_task.md'),
        )

    @task
    def significant_transaction_testing_task(self) -> Task:
        return Task(
            config=self.tasks_config['significant_transaction_testing'],
            async_execution=False,
            agent=self.testing_and_evidence_agent(),
            context=[self.financial_statement_analysis_task()],
            output_file=os.path.join(self.output_dir,'significant_transaction_testing_task.md'),
        )
        
    @task
    def fraud_risk_assessment_task(self) -> Task:
        return Task(
            config=self.tasks_config['fraud_risk_assessment'],
            async_execution=False,
            agent=self.testing_and_evidence_agent(),
            context=[self.significant_transaction_testing_task()],
            output_file=os.path.join(self.output_dir,'fraud_risk_assessment_task.md'),
        )

    @crew
    def crew(self) -> Crew:
        """Creates the TestingAndEvidenceCrew crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            verbose=True,
            output_log_file=self.log_path
        )