import unittest
from unittest.mock import patch, MagicMock, mock_open
import numpy as np
import torch
import os

import t5 as t5  # replace with actual filename (without .py), e.g., similarity_pipeline

class TestSimilarityPipeline(unittest.TestCase):

    def test_cosine_similarity_custom(self):
        v1 = np.array([1, 0])
        v2 = np.array([0, 1])
        result = t5.cosine_similarity_custom(v1, v2)
        self.assertAlmostEqual(result, 0.0, places=5)

    @patch('t5.storage.Client')
    @patch('t5.AutoTokenizer.from_pretrained')
    @patch('t5.AutoModel.from_pretrained')
    def test_compare_embedding_with_saved(self, mock_model, mock_tokenizer, mock_storage):
        # Mock GCS download
        mock_blob = MagicMock()
        mock_blob.download_to_filename = lambda filename: np.save(filename, np.ones(768))
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_storage.return_value.bucket.return_value = mock_bucket

        # Mock tokenizer & model
        mock_tokenizer.return_value = MagicMock(return_tensors="pt")
        mock_model_instance = MagicMock()
        mock_model_instance.eval = lambda: None
        mock_model_instance.return_value = mock_model_instance
        mock_model_instance(**MagicMock()).last_hidden_state.mean.return_value.squeeze.return_value = torch.tensor(np.ones(768))
        mock_model.return_value = mock_model_instance

        # Write dummy file
        with open('temp_test.txt', 'w') as f:
            f.write('Test sentence ' * 100)

        result = t5.compare_embedding_with_saved(
            new_file_path='temp_test.txt',
            model_name='some-model',
            gcp_bucket='bucket',
            gcs_embedding_path='path.npy'
        )
        self.assertIsInstance(result, float)
        os.remove('temp_test.txt')

    @patch('t5.mysql.connector.connect')
    def test_files_to_be_evaluated(self, mock_connect):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(1, 'gen.md', 'prompt.md')]
        mock_connect.return_value.cursor.return_value = mock_cursor
        result = t5.files_to_be_evaluated()
        expected = [['gen.md'], [1]]
        self.assertEqual(result, expected)


    @patch('builtins.open', new_callable=mock_open, read_data="# Title\n- Bullet")
    def test_simple_md_to_txt(self, mock_file):
        t5.simple_md_to_txt('file.md', 'file.txt')
        mock_file().write.assert_called_once_with('Title\nBullet')

    @patch('t5.storage.Client')
    def test_alert_trigger(self, mock_storage_client):
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_storage_client.return_value.bucket.return_value = mock_bucket

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"run_id": 1, "value": "some"}
        mock_conn.cursor.return_value = mock_cursor

        with patch('t5.mysql.connector.connect', return_value=mock_conn):
            t5.alert_trigger(1)
            self.assertTrue(mock_blob.upload_from_filename.called)

    @patch('t5.mysql.connector.connect')
    def test_update_metrics_table(self, mock_connect):
        mock_cursor = MagicMock()
        mock_connect.return_value.cursor.return_value = mock_cursor
        t5.update_metrice_table("file", 0.91, 0.92, 0.88, 0.93, 1, "prompt")
        self.assertTrue(mock_cursor.execute.called)

if __name__ == '__main__':
    unittest.main()
