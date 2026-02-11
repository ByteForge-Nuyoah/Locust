import os
import yaml
import logging

class ConfigManager:
    _instance = None
    _config = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """
        Load configuration from YAML files based on LOCUST_ENV.
        1. Load Global Base & Env Config
        2. Load Project-specific Base & Env Configs from src/projects/<project>/env/
        """
        env = os.getenv("LOCUST_ENV", "dev")
        # src/config/manager.py -> src/config -> src
        src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        root_dir = os.path.dirname(src_dir)
        
        # Global Config (src/config/env)
        global_env_dir = os.path.join(src_dir, "config", "env")
        
        # 1. Load Global Base
        base_config_path = os.path.join(global_env_dir, "base.yaml")
        self._config = self._read_yaml(base_config_path)
        
        # 2. Load Global Env Override
        env_config_path = os.path.join(global_env_dir, f"{env}.yaml")
        if os.path.exists(env_config_path):
            env_config = self._read_yaml(env_config_path)
            self._merge_config(self._config, env_config)
            logging.info(f"Loaded global config for environment: {env}")
        else:
            logging.warning(f"Global configuration file for environment '{env}' not found.")

        # Initialize projects dict if not present
        if "projects" not in self._config:
            self._config["projects"] = {}

        # 3. Discover and Load Project Configs
        projects_dir = os.path.join(root_dir, "projects")
        if os.path.exists(projects_dir):
            for project_name in os.listdir(projects_dir):
                project_path = os.path.join(projects_dir, project_name)
                if os.path.isdir(project_path):
                    self._load_project_config(project_name, project_path, env)

    def _load_project_config(self, project_name, project_path, env):
        project_env_dir = os.path.join(project_path, "env")
        if not os.path.exists(project_env_dir):
            return

        # Start with empty dict or existing project config (from global)
        p_config = self._config["projects"].get(project_name, {})

        # Load Project Base
        p_base_path = os.path.join(project_env_dir, "base.yaml")
        if os.path.exists(p_base_path):
            p_base = self._read_yaml(p_base_path)
            self._merge_config(p_config, p_base)

        # Load Project Env
        p_env_path = os.path.join(project_env_dir, f"{env}.yaml")
        if os.path.exists(p_env_path):
            p_env = self._read_yaml(p_env_path)
            self._merge_config(p_config, p_env)

        self._config["projects"][project_name] = p_config
        logging.info(f"Loaded config for project: {project_name}")

    def _read_yaml(self, path):
        """Read YAML file and support environment variable substitution like ${VAR:-default}"""
        import re
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Pattern to match ${VAR_NAME} or ${VAR_NAME:-default_value}
            pattern = re.compile(r'\$\{(\w+)(?::-(.*?))?\}')
            
            def replace_match(match):
                env_var = match.group(1)
                default_val = match.group(2)
                return os.getenv(env_var, default_val if default_val is not None else match.group(0))
            
            content = pattern.sub(replace_match, content)
            return yaml.safe_load(content) or {}

    def _merge_config(self, base, override):
        """
        Deep merge dictionary.
        """
        for key, value in override.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def get_project_config(self, project_name):
        """
        Get merged configuration for a specific project.
        Returns: Global defaults merged with Project specifics.
        """
        # Start with a copy of default config (excluding 'projects' and 'notification')
        defaults = {k: v for k, v in self._config.items() if k not in ["projects", "notification"]}
        
        project_specific = self._config.get("projects", {}).get(project_name, {})
        
        # Merge defaults with project specific
        # We want project specific to override defaults
        merged = defaults.copy()
        self._merge_config(merged, project_specific)
        
        return merged

    def get(self, key, default=None):
        """
        Get a value from the configuration.
        Supports dot notation for nested keys (e.g., 'notification.dingtalk.token')
        """
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

# Global instance
config = ConfigManager()
