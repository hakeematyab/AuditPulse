import os

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool, ScrapeWebsiteTool, WebsiteSearchTool, JSONSearchTool, TXTSearchTool

from crewai.llm import LLM
from ...tools.custom_tool import WrappedScrapeWebsiteTool

@CrewBase
class ClientAcceptanceCrew():
	"""ClientAcceptanceCrew crew"""

	agents_config = 'config/agents.yaml'
	tasks_config = 'config/tasks.yaml'
	compliance_file_path = './auditpulse_flow/crews/client_acceptance_crew/data/compliance.json'
	auditpulse_file_path = './auditpulse_flow/crews/client_acceptance_crew/data/AuditPulseInfo.md'
	output_dir = "./output/client_acceptance"
	log_path = "./logs/client_acceptance.txt"

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
	def client_acceptance_agent(self) -> Agent:
		return Agent(
			config=self.agents_config['client_acceptance_agent'],
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
	def client_background_task(self) -> Task:
		return Task(
			config=self.tasks_config['client_background_and_integrity_assessment'],
			async_execution=False,
			agent=self.client_acceptance_agent(),
			output_file=os.path.join(self.output_dir,'client_background_task.md'),
		)

	@task
	def financial_risk_task(self) -> Task:
		return Task(
			config=self.tasks_config['financial_risk_and_independence_assessment'],
			async_execution=False,
			agent=self.client_acceptance_agent(),
			context=[self.client_background_task()],
			output_file=os.path.join(self.output_dir,'financial_risk_task.md'),
		)

	@task
	def engagement_scope_task(self) -> Task:
		return Task(
			config=self.tasks_config['engagement_scope_and_strategy'],
			async_execution=False,
			agent=self.client_acceptance_agent(),
			context=[self.financial_risk_task()],
			output_file=os.path.join(self.output_dir,'engagement_scope_task.md'),
		)

	@crew
	def crew(self) -> Crew:
		"""Creates the ClientAcceptanceCrew crew"""
		return Crew(
			agents=self.agents,
			tasks=self.tasks,
			verbose=True,
			output_log_file=self.log_path
		)