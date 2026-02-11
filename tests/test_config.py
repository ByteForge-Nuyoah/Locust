import os
import unittest
import sys

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.config.manager import ConfigManager

class TestConfigManager(unittest.TestCase):
    def setUp(self):
        # We use the singleton instance but can re-trigger loading if needed
        self.config = ConfigManager()

    def test_get_nested_keys(self):
        """测试点号嵌套访问功能"""
        # 假设 base.yaml 中有 notification.enabled
        val = self.config.get("notification.enabled")
        self.assertIsInstance(val, bool)

    def test_env_substitution(self):
        """测试环境变量替换功能"""
        os.environ["TEST_VAR"] = "hello_world"
        # 这里我们需要读取一个包含 ${TEST_VAR} 的临时文件或者检查现有配置
        # 由于 ConfigManager 在初始化时加载，我们可以通过 get 验证
        # 假设我们在 base.yaml 中添加了一个测试项，或者这里我们手动调用 _read_yaml
        
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tf:
            tf.write("test_key: ${TEST_VAR:-default}\ndefault_key: ${NON_EXISTENT_VAR:-fallback}")
            temp_path = tf.name
        
        try:
            data = self.config._read_yaml(temp_path)
            self.assertEqual(data["test_key"], "hello_world")
            self.assertEqual(data["default_key"], "fallback")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_project_config_merge(self):
        """测试项目配置合并逻辑"""
        crm_config = self.config.get_project_config("crm")
        self.assertIn("host", crm_config)
        # 验证项目配置覆盖了全局配置（如果有同名 key）

if __name__ == "__main__":
    unittest.main()
