#!/usr/bin/env python
from random import randint

from pydantic import BaseModel, Field

from crewai.flow import Flow, listen, start

from auditpulse_flow.crews.client_acceptance_crew.client_acceptance_crew import ClientAcceptanceCrew
from auditpulse_flow.crews.audit_planning_crew.audit_planning_crew import AuditPlanningCrew
from auditpulse_flow.crews.testing_evidence_gathering_crew.testing_evidence_gathering_crew import TestingEvidenceGatheringCrew
from auditpulse_flow.crews.evaluation_reporting_crew.evaluation_reporting_crew import EvaluationReportingCrew

class AuditPulseState(BaseModel):
    """Validated and sanitized inputs."""
    audit_firm: str = "AuditPulse"
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
        print("Generating sentence count")
        self.state.client_acceptance_result = ClientAcceptanceCrew().crew().kickoff(
                                                inputs={
                                                'audit_firm':self.state.audit_firm,
                                                'company_name': self.state.company_name,
                                                'central_index_key': self.state.central_index_key,
                                                'company_ticker': self.state.company_ticker,
                                                'year': self.state.year
                                                }
                                                )
        
    @listen(client_acceptance_crew)
    def audit_planning_crew(self):
        self.state.client_acceptance_result = AuditPlanningCrew().crew().kickoff(
                                                inputs={
                                                'audit_firm':self.state.audit_firm,
                                                'company_name': self.state.company_name,
                                                'central_index_key': self.state.central_index_key,
                                                'company_ticker': self.state.company_ticker,
                                                'year': self.state.year
                                                }
                                                )

    @listen(audit_planning_crew)
    def testing_evidence_gathering_crew(self):
        print("Starting Testing and Evidence Gathering Crew...")
        self.state.testing_evidence_gathering_result = TestingEvidenceGatheringCrew().crew().kickoff(
            inputs={
                'audit_firm': self.state.audit_firm,
                'company_name': self.state.company_name,
                'central_index_key': self.state.central_index_key,
                'company_ticker': self.state.company_ticker,
                'year': self.state.year
            }
        )
        print(f"Testing Evidence Gathering Result: {self.state.testing_evidence_gathering_result}")

    @listen(testing_evidence_gathering_crew)
    def evaluation_reporting_crew(self):
        print("Starting Evaluation and Reporting Crew...")
        self.state.evaluation_reporting_result = EvaluationReportingCrew().crew().kickoff(
            inputs={
                'audit_firm': self.state.audit_firm,
                'company_name': self.state.company_name,
                'central_index_key': self.state.central_index_key,
                'company_ticker': self.state.company_ticker,
                'year': self.state.year
            }
        )
        print(f"Evaluation Reporting Result: {self.state.evaluation_reporting_result}")



def kickoff(company_name, central_index_key, company_ticker, year):
    auditpulse_flow = AuditPulseFlow()
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
