import unittest
from unittest.mock import MagicMock
import policy_creation

class TestPolicyCreation(unittest.TestCase):

    @classmethod
    def setUp(self):
        self.collection_name = 'config'
        self.document_name = 'policy'
    
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

        
    # chunk_pdf
    # pdf2text
    # generate_rules
    # save_policy
    # update collection


if __name__=='__main__':
    unittest.main()