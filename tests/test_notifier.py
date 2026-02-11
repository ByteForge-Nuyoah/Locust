import os
import unittest
import sys
from unittest.mock import MagicMock, patch

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.common.notifier import Notifier

class TestNotifier(unittest.TestCase):
    def setUp(self):
        # Mock config to disable actual sending during tests
        with patch('src.config.manager.ConfigManager.get') as mock_get:
            mock_get.return_value = {
                "enabled": True,
                "dingtalk": {"enabled": True, "webhook": "http://mock"},
                "wechat": {"enabled": False},
                "email": {"enabled": False}
            }
            self.notifier = Notifier()

    @patch('requests.post')
    def test_send_dingtalk(self, mock_post):
        """测试钉钉通知发送逻辑"""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"errcode": 0}
        
        # Mock stats
        stats = {
            "requests": 100,
            "failures": 5,
            "rps": 10.5,
            "avg_rt": 150,
            "p95_rt": 200,
            "p99_rt": 300,
            "max_rt": 500,
            "top_slowest": [
                {"method": "GET", "name": "/test", "p95": 200, "avg": 150, "count": 50}
            ]
        }
        
        # We need a dummy report file
        report_path = "test_report.html"
        with open(report_path, "w") as f:
            f.write("test")
            
        try:
            self.notifier.send_report(report_path, "test_project", stats)
            self.assertTrue(mock_post.called)
        finally:
            if os.path.exists(report_path):
                os.remove(report_path)
            zip_path = report_path.replace(".html", ".zip")
            if os.path.exists(zip_path):
                os.remove(zip_path)

if __name__ == "__main__":
    unittest.main()
