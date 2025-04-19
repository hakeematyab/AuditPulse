import time
from datetime import datetime
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
    sleeptime = 3
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}][🕒 LLM DELAY]: Sleeping for {sleeptime} seconds before next call...")
    time.sleep(sleeptime)

class AuditPulseState(BaseModel):
    """Validated and sanitized inputs."""
    audit_firm: str = "AuditPulse"
    current_date: str = Field(datetime.now().date().isoformat(), description="Todays date.")
    run_id: str = Field("debug_run", description="Identifier of the run.")
    company_name: str = Field(None, description="Name of the company to audit.")
    central_index_key: int = Field(None, description="A unique central index key to identify the company.") 
    company_ticker: str = Field(None, description="The ticker associated with the company.") 
    year: str = Field(None, description="Year in which to audit the company.")
    
    # Client Acceptance Phase Task Results
    client_background_and_integrity_assessment: str = Field("", description="Output from client background and integrity assessment task.")
    financial_risk_and_independence_assessment: str = Field("", description="Output from financial risk and independence assessment task.")
    engagement_scope_and_strategy: str = Field("", description="Output from engagement scope and strategy task.")
    client_acceptance_result: str = Field("", description="Result of the client acceptance phase.")
    
    # Audit Planning Phase Task Results
    preliminary_engagement_review: str = Field("", description="Output from preliminary engagement review task.")
    business_risk_and_fraud_assessment: str = Field("", description="Output from business risk and fraud assessment task.")
    internal_control_system_evaluation: str = Field("", description="Output from internal control system evaluation task.")
    audit_strategy_and_team_allocation: str = Field("", description="Output from audit strategy and team allocation task.")
    audit_planning_result: str = Field("", description="Result of the audit planning phase.")
    
    # Testing and Evidence Gathering Phase Task Results
    control_testing_assessment: str = Field("", description="Output from control testing assessment task.")
    financial_statement_analysis: str = Field("", description="Output from financial statement analysis task.")
    significant_transaction_testing: str = Field("", description="Output from significant transaction testing task.")
    fraud_risk_assessment: str = Field("", description="Output from fraud risk assessment task.")
    testing_evidence_gathering_result: str = Field("", description="Result of the testing, evidence gathering phase.")
    
    # Evaluation and Reporting Phase Task Results
    evidence_evaluation_and_misstatement_assessment: str = Field("", description="Output from evidence evaluation and misstatement assessment task.")
    financial_statement_compliance_evaluation: str = Field("", description="Output from financial statement compliance evaluation task.")
    going_concern_and_viability_assessment: str = Field("", description="Output from going concern and viability assessment task.")
    audit_opinion_formulation_and_reporting: str = Field("", description="Output from audit opinion formulation and reporting task.")
    evaluation_reporting_result: str = Field("", description="Result of the evaluation reporting phase.")


class AuditPulseFlow(Flow[AuditPulseState]):
    # Phase task mapping defines the order of tasks in each phase
    phase_task_mapping = {
        'client_acceptance': [
            'client_background_and_integrity_assessment',
            'financial_risk_and_independence_assessment',
            'engagement_scope_and_strategy'
        ],
        'audit_planning': [
            'preliminary_engagement_review',
            'business_risk_and_fraud_assessment',
            'internal_control_system_evaluation',
            'audit_strategy_and_team_allocation'
        ],
        'testing_evidence': [
            'control_testing_assessment',
            'financial_statement_analysis',
            'significant_transaction_testing',
            'fraud_risk_assessment'
        ],
        'evaluation_reporting': [
            'evidence_evaluation_and_misstatement_assessment',
            'financial_statement_compliance_evaluation',
            'going_concern_and_viability_assessment',
            'audit_opinion_formulation_and_reporting'
        ]
    }

    @start()
    def client_acceptance_crew(self):
        client_acceptance = ClientAcceptanceCrew()
        client_acceptance.output_dir = client_acceptance.output_dir.format(run_id=self.state.run_id)
        crew_output = client_acceptance.crew().kickoff(
            inputs={
                'audit_firm': self.state.audit_firm,
                'company_name': self.state.company_name,
                'central_index_key': self.state.central_index_key,
                'company_ticker': self.state.company_ticker,
                'year': self.state.year,
                'current_date': self.state.current_date
            }
        )
        
        # Store individual task outputs based on their order of execution
        for i, task_name in enumerate(self.phase_task_mapping['client_acceptance']):
            if i < len(crew_output.tasks_output):
                setattr(self.state, task_name, crew_output.tasks_output[i].raw)
        
        # Store overall crew output
        self.state.client_acceptance_result = crew_output.raw

    @listen(client_acceptance_crew)
    def audit_planning_crew(self):
        audit_planning = AuditPlanningCrew()
        audit_planning.output_dir = audit_planning.output_dir.format(run_id=self.state.run_id)
        crew_output = audit_planning.crew().kickoff(
            inputs={
                'audit_firm': self.state.audit_firm,
                'company_name': self.state.company_name,
                'central_index_key': self.state.central_index_key,
                'company_ticker': self.state.company_ticker,
                'year': self.state.year,
                'current_date': self.state.current_date,
                # Pass relevant outputs from previous phase
                'engagement_scope_and_strategy': self.state.engagement_scope_and_strategy,
                'client_background_and_integrity_assessment': self.state.client_background_and_integrity_assessment,
                'financial_risk_and_independence_assessment': self.state.financial_risk_and_independence_assessment
            }
        )
        
        # Store individual task outputs based on their order of execution
        for i, task_name in enumerate(self.phase_task_mapping['audit_planning']):
            if i < len(crew_output.tasks_output):
                setattr(self.state, task_name, crew_output.tasks_output[i].raw)
        
        # Store overall crew output
        self.state.audit_planning_result = crew_output.raw

    @listen(audit_planning_crew)
    def testing_evidence_gathering_crew(self):
        test_crew = TestingEvidenceGatheringCrew()
        test_crew.output_dir = test_crew.output_dir.format(run_id=self.state.run_id)
        crew_output = test_crew.crew().kickoff(
            inputs={
                'audit_firm': self.state.audit_firm,
                'company_name': self.state.company_name,
                'central_index_key': self.state.central_index_key,
                'company_ticker': self.state.company_ticker,
                'year': self.state.year,
                'current_date': self.state.current_date,
                # Pass relevant outputs from previous phases
                'internal_control_system_evaluation': self.state.internal_control_system_evaluation,
                'audit_strategy_and_team_allocation': self.state.audit_strategy_and_team_allocation,
                'business_risk_and_fraud_assessment': self.state.business_risk_and_fraud_assessment
            }
        )
        
        # Store individual task outputs based on their order of execution
        for i, task_name in enumerate(self.phase_task_mapping['testing_evidence']):
            if i < len(crew_output.tasks_output):
                setattr(self.state, task_name, crew_output.tasks_output[i].raw)
        
        # Store overall crew output
        self.state.testing_evidence_gathering_result = crew_output.raw

    @listen(testing_evidence_gathering_crew)
    def evaluation_reporting_crew(self):
        eval_crew = EvaluationReportingCrew()
        eval_crew.output_dir = eval_crew.output_dir.format(run_id=self.state.run_id)
        crew_output = eval_crew.crew().kickoff(
            inputs={
                'audit_firm': self.state.audit_firm,
                'company_name': self.state.company_name,
                'central_index_key': self.state.central_index_key,
                'company_ticker': self.state.company_ticker,
                'year': self.state.year,
                'current_date': self.state.current_date,
                # Pass relevant outputs from previous phases
                'control_testing_assessment': self.state.control_testing_assessment,
                'financial_statement_analysis': self.state.financial_statement_analysis,
                'significant_transaction_testing': self.state.significant_transaction_testing,
                'fraud_risk_assessment': self.state.fraud_risk_assessment,
                'financial_risk_and_independence_assessment': self.state.financial_risk_and_independence_assessment
            }
        )
        
        # Store individual task outputs based on their order of execution
        for i, task_name in enumerate(self.phase_task_mapping['evaluation_reporting']):
            if i < len(crew_output.tasks_output):
                setattr(self.state, task_name, crew_output.tasks_output[i].raw)
        
        # Store overall crew output
        self.state.evaluation_reporting_result = crew_output.raw


def kickoff(run_id, company_name, central_index_key, company_ticker, year):
    auditpulse_flow = AuditPulseFlow()
    print(f'Date: {auditpulse_flow.state.current_date}')
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
    start = time.perf_counter()
    # kickoff(
    # run_id="debug_2",
    # company_name="Apple Inc.",
    # central_index_key="320193",
    # company_ticker="AAPL",
    # year=2025
    # )
    print()
    print('-'*75)
    print(f'Completed in {(time.perf_counter()-start)//60} minutes.')