import time
from datetime import datetime
from random import randint

from typing import Any

from pydantic import BaseModel, Field

from crewai.flow import Flow, listen, start

from crewai.utilities.events import crewai_event_bus, LLMCallCompletedEvent

from auditpulse_flow.crews.client_acceptance_crew.client_acceptance_crew import ClientAcceptanceCrew
from auditpulse_flow.crews.audit_planning_crew.audit_planning_crew import AuditPlanningCrew
from auditpulse_flow.crews.testing_evidence_gathering_crew.testing_evidence_gathering_crew import TestingEvidenceGatheringCrew
from auditpulse_flow.crews.evaluation_reporting_crew.evaluation_reporting_crew import EvaluationReportingCrew

@crewai_event_bus.on(LLMCallCompletedEvent)
def on_llm_call_complete(source: Any, event):
    sleeptime = 5
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][🕒 LLM DELAY]: Sleeping for {sleeptime} seconds before next call...")
    time.sleep(sleeptime)

class AuditPulseState(BaseModel):
    """Validated and sanitized inputs."""
    audit_firm: str = "AuditPulse"
    run_id: str = Field("0000000", description="Identifier of the run.")
    company_name: str = Field(None, description="Name of the company to audit.")
    central_index_key: int = Field(None, description="A unique central index key to identify the company.") 
    company_ticker: str = Field(None, description="The ticker associated with the company.") 
    year: str = Field(None, description="Year in which to audit the company.")
    client_acceptance_result: str = Field(None,description="Result of the client acceptance phase.")
    audit_planning_result: str = Field(None,description="Result of the audit planning phase.")
    testing_evidence_gathering_result: str = Field(None,description="Result of the testing, evidence gathering phase.")
    evaluation_reporting_result: str = Field(None,description="Result of the evaluation reporting phase.")


class AuditPulseFlow(Flow[AuditPulseState]):
    @start()
    def client_acceptance_crew(self):
        client_acceptance = ClientAcceptanceCrew()
        client_acceptance.output_dir = client_acceptance.output_dir.format(run_id=self.state.run_id)
        self.state.client_acceptance_result = client_acceptance.crew().kickoff(
            inputs={
                'audit_firm': self.state.audit_firm,
                'company_name': self.state.company_name,
                'central_index_key': self.state.central_index_key,
                'company_ticker': self.state.company_ticker,
                'year': self.state.year
            }
        )

    @listen(client_acceptance_crew)
    def audit_planning_crew(self):
        audit_planning = AuditPlanningCrew()
        audit_planning.output_dir = audit_planning.output_dir.format(run_id=self.state.run_id)
        self.state.audit_planning_result = audit_planning.crew().kickoff(
            inputs={
                'audit_firm': self.state.audit_firm,
                'company_name': self.state.company_name,
                'central_index_key': self.state.central_index_key,
                'company_ticker': self.state.company_ticker,
                'year': self.state.year
            }
        )

    @listen(audit_planning_crew)
    def testing_evidence_gathering_crew(self):
        test_crew = TestingEvidenceGatheringCrew()
        test_crew.output_dir = test_crew.output_dir.format(run_id=self.state.run_id)
        self.state.testing_evidence_gathering_result = test_crew.crew().kickoff(
            inputs={
                'audit_firm': self.state.audit_firm,
                'company_name': self.state.company_name,
                'central_index_key': self.state.central_index_key,
                'company_ticker': self.state.company_ticker,
                'year': self.state.year
            }
        )

    @listen(testing_evidence_gathering_crew)
    def evaluation_reporting_crew(self):
        eval_crew = EvaluationReportingCrew()
        eval_crew.output_dir = eval_crew.output_dir.format(run_id=self.state.run_id)
        self.state.evaluation_reporting_result = eval_crew.crew().kickoff(
            inputs={
                'audit_firm': self.state.audit_firm,
                'company_name': self.state.company_name,
                'central_index_key': self.state.central_index_key,
                'company_ticker': self.state.company_ticker,
                'year': self.state.year
            }
        )


def kickoff(run_id, company_name, central_index_key, company_ticker, year):
    auditpulse_flow = AuditPulseFlow()
    auditpulse_flow.state.run_id = run_id
    auditpulse_flow.state.company_name = company_name
    auditpulse_flow.state.central_index_key = central_index_key
    auditpulse_flow.state.company_ticker = company_ticker
    auditpulse_flow.state.year = year
    auditpulse_flow.kickoff()


def plot():
    auditpulse_flow = AuditPulseFlow()
    auditpulse_flow.plot()


if __name__ == "__main__":
    kickoff()
