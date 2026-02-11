import unittest
import os
import json
import csv
import yaml
from src.common.data_loader import DataLoaderFactory

class TestDataLoader(unittest.TestCase):
    def setUp(self):
        self.test_dir = "tests/data"
        if not os.path.exists(self.test_dir):
            os.makedirs(self.test_dir)
            
        self.csv_file = os.path.join(self.test_dir, "test.csv")
        self.json_file = os.path.join(self.test_dir, "test.json")
        self.yaml_file = os.path.join(self.test_dir, "test.yaml")
        
        # Create CSV
        with open(self.csv_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['id', 'name'])
            writer.writeheader()
            writer.writerow({'id': '1', 'name': 'Alice'})
            writer.writerow({'id': '2', 'name': 'Bob'})
            
        # Create JSON
        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump([{'id': 1, 'name': 'Alice'}, {'id': 2, 'name': 'Bob'}], f)
            
        # Create YAML
        with open(self.yaml_file, 'w', encoding='utf-8') as f:
            yaml.dump([{'id': 1, 'name': 'Alice'}, {'id': 2, 'name': 'Bob'}], f)

    def tearDown(self):
        for f in [self.csv_file, self.json_file, self.yaml_file]:
            if os.path.exists(f):
                os.remove(f)
        if os.path.exists(self.test_dir):
            os.rmdir(self.test_dir)

    def test_csv_loader(self):
        loader = DataLoaderFactory.get_loader(self.csv_file)
        data1 = loader.next()
        self.assertEqual(data1['id'], '1')
        data2 = loader.next()
        self.assertEqual(data2['id'], '2')
        # Test cycle
        data3 = loader.next()
        self.assertEqual(data3['id'], '1')

    def test_json_loader(self):
        loader = DataLoaderFactory.get_loader(self.json_file)
        data = loader.get_all()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['name'], 'Alice')

    def test_yaml_loader(self):
        loader = DataLoaderFactory.get_loader(self.yaml_file)
        data = loader.next()
        self.assertEqual(data['id'], 1)

    def test_unsupported_format(self):
        with self.assertRaises(ValueError):
            DataLoaderFactory.get_loader("test.txt")

if __name__ == '__main__':
    unittest.main()
