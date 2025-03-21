from flask import Flask, jsonify
from ....DataPipeline.DataValidation import DataValidator

from auditpulse_flow.main import kickoff
app = Flask(__name__)

@app.route("/",methods=["GET"])
def health_check():
    return jsonify({    
        "status":"OK",
        "message":"AuditPulse Live!"}
        )

@app.route("/generate",methods=["GET"])
def generate_audit_report():
    company_name, central_index_key, company_ticker, year = get_update_latest_entry()
    data_validator = DataValidator(company_name, central_index_key, year)
    status, message = data_validator.run_validation()
    if status:
        validated_inputs = data_validator.auditpulse_validated_inputs
        company_name = validated_inputs.company_name
        central_index_key = validated_inputs.company_name
        company_ticker = validated_inputs.company_ticker
        year = validated_inputs.year
        try:
            kickoff(company_name,
                    central_index_key,
                    company_ticker,
                    year)
        except Exception as e:
            status = False
            message = str(e)
    update_results(status, message)

def get_update_latest_entry():
    company_name, central_index_key, company_ticker, year = None, None, None, None
    return (company_name, 
            central_index_key, 
            company_ticker, 
            year)

def update_results(status):
    pass

if __name__=="__main__":
    app.run(debug=True)