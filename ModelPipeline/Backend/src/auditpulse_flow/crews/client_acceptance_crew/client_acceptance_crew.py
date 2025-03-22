import os

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool, ScrapeWebsiteTool, WebsiteSearchTool, JSONSearchTool, TXTSearchTool

from crewai.llm import LLM

# If you want to run a snippet of code before or after the crew starts, 
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

@CrewBase
class ClientAcceptanceCrew():
	"""ClientAcceptanceCrew crew"""

	# Learn more about YAML configuration files here:
	# Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
	# Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
	agents_config = 'config/agents.yaml'
	tasks_config = 'config/tasks.yaml'
	compliance_file_path = './auditpulse_flow/crews/client_acceptance_crew/data/compliance.json'
	auditpulse_file_path = './auditpulse_flow/crews/client_acceptance_crew/data/AuditPulseInfo.md'
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
			max_tokens=	64,
			context_window_size=950000,
		)
	output_dir = "./output/client_acceptance"
	log_path = "./logs/client_acceptance.txt"
	os.makedirs(output_dir,exist_ok=True)
	os.makedirs(os.path.dirname(log_path),exist_ok=True)

	# If you would like to add tools to your agents, you can learn more about it here:
	# https://docs.crewai.com/concepts/agents#agent-tools
	@agent
	def client_acceptance_agent(self) -> Agent:
		return Agent(
			config=self.agents_config['client_acceptance_agent'],
			verbose=True,
			    tools=[
					SerperDevTool(),
					ScrapeWebsiteTool(),
					self.website_search_tool,
					self.pcaob_guidlines_tool,
					self.auditpulse_file_tool
				],
				llm=self.llm,
				respect_context_window=True,
				max_rpm=10,
				cache=True,
				max_retry_limit=10
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
		# To learn how to add knowledge sources to your crew, check out the documentation:
		# https://docs.crewai.com/concepts/knowledge#what-is-knowledge

		return Crew(
			agents=self.agents, # Automatically created by the @agent decorator
			tasks=self.tasks, # Automatically created by the @task decorator
			verbose=True,
			output_log_file=self.log_path
		)