import yaml
import csv
import json
import os
import threading
import logging
from itertools import cycle

logger = logging.getLogger(__name__)

class BaseDataLoader:
    """
    基础数据加载器，实现线程安全的数据获取
    """
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = self._load_data()
        if not self.data:
            logger.warning(f"Data source is empty: {file_path}")
            self.data = [{}] # Avoid cycle error with empty list
        self.iterator = cycle(self.data)
        self.lock = threading.Lock()

    def _load_data(self):
        raise NotImplementedError("Subclasses must implement _load_data")

    def next(self):
        """
        线程安全地获取下一条数据
        """
        with self.lock:
            return next(self.iterator)

    def get_all(self):
        """
        获取所有原始数据
        """
        return self.data

class YamlDataLoader(BaseDataLoader):
    def _load_data(self):
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"YAML file not found: {self.file_path}")
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return data if isinstance(data, list) else [data] if data else []
        except Exception as e:
            logger.error(f"Error loading YAML {self.file_path}: {e}")
            return []

class CsvDataLoader(BaseDataLoader):
    def _load_data(self):
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"CSV file not found: {self.file_path}")
        data = []
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append(row)
        except Exception as e:
            logger.error(f"Error loading CSV {self.file_path}: {e}")
        return data

class JsonDataLoader(BaseDataLoader):
    def _load_data(self):
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"JSON file not found: {self.file_path}")
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else [data] if data else []
        except Exception as e:
            logger.error(f"Error loading JSON {self.file_path}: {e}")
            return []

class DataLoaderFactory:
    """
    数据加载器工厂，根据文件后缀自动返回对应的 Loader
    """
    @staticmethod
    def get_loader(file_path):
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        if ext in ['.yaml', '.yml']:
            return YamlDataLoader(file_path)
        elif ext == '.csv':
            return CsvDataLoader(file_path)
        elif ext == '.json':
            return JsonDataLoader(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
