import os
import unittest
from unittest.mock import MagicMock, patch, mock_open
import policy_creation

class TestPolicyCreation(unittest.TestCase):

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
        document_name = 'policy'
        expected_document = {
            'active_model_type': 'active_model_type',
            'active_model_id': 'active_model_id',
            'active_standards_path': 'active_standards_path',
            'latest_version': 'latest_version'
        }
        policy_collection = db_client.collection.return_value.document.return_value
        policy_collection.get.return_value.exists = True
        policy_collection.get.return_value.to_dict.return_value = expected_document
        policy_doc = policy_creation.get_document(db_client, collection_name, document_name)
        self.assertEqual(policy_doc.keys(), expected_document.keys())

        # Case - 2:
        db_client = MagicMock()
        policy_collection = db_client.collection.return_value.document.return_value
        policy_collection.get.return_value.exists = False
        with self.assertRaises(ValueError):
            policy_creation.get_document(db_client, collection_name, document_name)

    def test_chunk_pdf(self):
        with patch('policy_creation.PdfReader') as mock_pdf_reader, \
             patch('policy_creation.os.path.exists', return_value=True) as mock_os_path_exists, \
             patch('policy_creation.PdfWriter') as mock_pdf_writer, \
             patch('builtins.open', mock_open()) as mock_open_file:
            num_pages = 10
            chunk_size = 2
            pdf_input_path = './inputs/standards.pdf'
            output_dir = './temp'
            page = MagicMock()
            mock_pdf_reader_instance = MagicMock()
            mock_pdf_writer_instance = MagicMock()
            mock_pdf_reader.return_value = mock_pdf_reader_instance
            mock_pdf_reader_instance.pages = [page] * num_pages
            mock_pdf_writer.return_value = mock_pdf_writer_instance

            chunks = policy_creation.chunk_pdf(pdf_input_path, output_dir, chunk_size)
            expected_chunks = [f"{output_dir}/chunk_{i // chunk_size + 1}.pdf" for i in range(0, num_pages, chunk_size)]

            self.assertEqual(chunks, expected_chunks)

    def test_pdf2text(self):
        with patch('policy_creation.fitz.open') as mock_fitz_open:
            pdf_input_path = './inputs/standards.pdf'
            num_pages = 5
            mock_fitz_open_instance = MagicMock()
            mock_fitz_open.return_value = mock_fitz_open_instance 
            mock_fitz_open_instance.__iter__.return_value = [MagicMock(get_text=MagicMock(return_value=f"Page-{i}")) for i in range(num_pages)]
            output_text = policy_creation.pdf2text(pdf_input_path)
            expected_output_text = '\n'.join([f"Page-{i}"for i in range(num_pages)])
            self.assertEqual(output_text, expected_output_text)

        with patch('policy_creation.fitz.open') as mock_fitz_open:
            pdf_input_path = './inputs/standards.pdf'
            num_pages = 0
            mock_fitz_open_instance = MagicMock()
            mock_fitz_open.return_value = mock_fitz_open_instance 
            mock_fitz_open_instance.__iter__.return_value = [MagicMock(get_text=MagicMock(return_value=f"Page-{i}")) for i in range(num_pages)]
            output_text = policy_creation.pdf2text(pdf_input_path)
            expected_output_text = '\n'.join([f"Page-{i}"for i in range(num_pages)])
            self.assertEqual(output_text, expected_output_text)
    
    def test_generate_rules(self):
        prompt = 'DummyPrompt'
        text = 'DummyText'
        model = 'DummyModel'
        expected_policy = [
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
        sleeptime = 1
        max_tokens = 2048
        temperature = 0.1
        max_retries = 5

        with patch('policy_creation.logging'):
            # Case - 1
            llm_client = MagicMock()
            llm_client.chat.completions.create.return_value = expected_policy
            output_policy = policy_creation.generate_rules(prompt, text, llm_client, model, sleeptime, max_tokens, temperature, max_retries)
            self.assertEqual(output_policy, expected_policy)

            # Case - 2
            llm_client = MagicMock()
            llm_client.chat.completions.create.side_effect = Exception("400")
            output_policy = policy_creation.generate_rules(prompt, text, llm_client, model, sleeptime, max_tokens, temperature, max_retries)
            self.assertEqual(output_policy, [])  

            # Case - 3
            llm_client = MagicMock()
            llm_client.chat.completions.create.side_effect = Exception("413")
            output_policy = policy_creation.generate_rules(prompt, text, llm_client, model, sleeptime, max_tokens, temperature, max_retries)
            self.assertEqual(output_policy, [])  

            # Case - 4
            llm_client = MagicMock()
            llm_client.chat.completions.create.side_effect = Exception("31412")
            output_policy = policy_creation.generate_rules(prompt, text, llm_client, model, sleeptime, max_tokens, temperature, max_retries)
            self.assertEqual(output_policy, [])  

    def test_save_policy(self):
        with patch('builtins.open', mock_open()) as mock_open_file, \
             patch('json.dump') as mock_json_dump:
            policy = [
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
            policy_output_path = './policy_v0.json'

            policy_creation.save_policy(policy, policy_output_path)
            mock_open_file.assert_called_once_with(policy_output_path, 'w', encoding='utf-8')
            mock_json_dump.assert_called_once_with(policy, mock_open_file(), indent=4)

if __name__ == '__main__':
    unittest.main()
