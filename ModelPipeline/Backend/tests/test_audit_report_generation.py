import os
import unittest
from unittest.mock import MagicMock, patch, mock_open
import json
import sys
sys.path.append('./src')
import app

class TestAuditReportGeneration(unittest.TestCase):

    @classmethod
    def setUp(self):
        pass

    @classmethod
    def tearDown(self):
        pass

    def test_get_document(self):
        # Case - 1:
        db_client = MagicMock()
        collection_name = 'config'
        document_name = 'deployment'
        expected_document = {
            'active_policy_path': 'active_policy_path',
            'active_prompts_path': 'active_prompts_path'
        }
        policy_collection = db_client.collection.return_value.document.return_value
        policy_collection.get.return_value.exists = True
        policy_collection.get.return_value.to_dict.return_value = expected_document
        
        document = app.get_document(db_client, collection_name, document_name)
        self.assertEqual(document.keys(), expected_document.keys())

        # Case - 2:
        db_client = MagicMock()
        policy_collection = db_client.collection.return_value.document.return_value
        policy_collection.get.return_value.exists = False
        
        with self.assertRaises(ValueError):
            app.get_document(db_client, collection_name, document_name)

    def test_compile_report(self):
        base_path = 'output/123'
        final_report_path = 'output/final_report/audit_report_123.md'
        
        with patch('os.path.exists', return_value=True), \
             patch('os.makedirs') as mock_makedirs, \
             patch('builtins.open', mock_open()) as mock_file:
            
            # Mock the file reads for each phase and task
            mock_file.return_value.read.side_effect = [
                '```markdown\nClient Background Content\n```',
                '```\nFinancial Risk Content\n```',
                '```\nEngagement Scope Content\n```',
                '```\nPreliminary Engagement Content\n```',
                '```\nBusiness Risk Content\n```',
                '```\nInternal Control Content\n```',
                '```\nAudit Strategy Content\n```',
                '```\nControl Testing Content\n```',
                '```\nFinancial Statement Analysis Content\n```',
                '```\nSignificant Transaction Testing Content\n```',
                '```\nFraud Risk Assessment Content\n```',
                '```\nEvidence Evaluation Content\n```',
                '```\nFinancial Statement Compliance Content\n```',
                '```\nGoing Concern Content\n```',
                '```\nAudit Opinion Content\n```'
            ]
            
            app.compile_report(base_path, final_report_path)
            
            # Check that the directory was created
            # mock_makedirs.assert_called_once()
            
            # Check that files were opened for reading and one for writing
            self.assertEqual(mock_file.call_count, 16)  # 15 reads + 1 write

    def test_upload_to_gcp(self):
        bucket = MagicMock()
        gcp_file_path = 'generated_reports/audit_report/audit_report_123.md'
        local_file_path = 'output/final_report/audit_report_123.md'
        
        # Case - 1: File exists
        with patch('os.path.exists', return_value=True):
            app.upload_to_gcp(bucket, gcp_file_path, local_file_path)
            bucket.blob.assert_called_once_with(gcp_file_path)
            bucket.blob.return_value.upload_from_filename.assert_called_once_with(local_file_path)
        
        # Case - 2: File does not exist
        bucket = MagicMock()
        with patch('os.path.exists', return_value=False), \
             patch('os.makedirs') as mock_makedirs, \
             patch('builtins.open', mock_open()) as mock_file:
            
            app.upload_to_gcp(bucket, gcp_file_path, local_file_path)
            
            mock_makedirs.assert_called_once()
            mock_file.assert_called_once_with(local_file_path, 'w')
            mock_file().write.assert_called_once_with('Hello World!')
            bucket.blob.assert_called_once_with(gcp_file_path)
            bucket.blob.return_value.upload_from_filename.assert_called_once_with(local_file_path)

if __name__ == '__main__':
    unittest.main()