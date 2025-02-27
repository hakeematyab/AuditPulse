import unittest
from unittest.mock import MagicMock, patch, mock_open
import policy_creation

class TestPolicyCreation(unittest.TestCase):

    @classmethod
    def setUp(self):
        self.collection_name = 'config'
        self.document_name = 'policy'
        self.policy = [
                        {
                            "rule_id": "PCAOB-2401",
                            "standard": "AS 2401 - Consideration of Fraud in a Financial Statement Audit",
                            "description": "Auditors must exercise professional skepticism to detect and respond to fraud risks in financial statements.",
                            "enforcement_guidelines": [
                                "Identify and assess fraud risks, including the risk of management override of controls.",
                                "Implement audit procedures to address fraud risks and verify financial accuracy.",
                                "Communicate fraud risks and findings to management, the audit committee, and regulatory authorities when necessary."
                            ]
                        }
                    ]
        self.policy_output_path = './policy_v0.json'
    
    @classmethod
    def tearDown(self):
        pass

    def test_get_document(self):
        # Case - 1:
        db_client = MagicMock()
        expected_document =  {
                                'active_model_type': 'active_model_type',
                                'active_model_id': 'active_model_id',
                                'active_standards_path': 'active_standards_path',
                                'latest_version': 'latest_version'
                                }
        policy_collection = db_client.collection.return_value.document.return_value
        policy_collection.get.return_value.exists = True
        policy_collection.get.return_value.to_dict.return_value = expected_document
        policy_doc = policy_creation.get_document(db_client, self.collection_name, self.document_name)
        self.assertEqual(policy_doc.keys(), expected_document.keys())

        # Case - 2:
        db_client = MagicMock()
        policy_collection = db_client.collection.return_value.document.return_value
        policy_collection.get.return_value.exists = False
        with self.assertRaises(ValueError):
            policy_creation.get_document(db_client, self.collection_name, self.document_name)

    def test_chunk_pdf(self):
        pass

    def test_pdf2text(self):
        pass

    def test_generate_rules(self):
        pass

    def test_save_policy(self):
        with patch('builtins.open', mock_open()) as mock_open_file,\
        patch('json.dump') as mock_json_dump:
            policy_creation.save_policy(self.policy, self.policy_output_path)
            mock_open_file.assert_called_once_with(self.policy_output_path, 'w', encoding='utf-8')
            mock_json_dump.assert_called_once_with(self.policy, mock_open_file(), indent=4)

if __name__=='__main__':
    unittest.main()