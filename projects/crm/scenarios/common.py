from locust import FastHttpUser
from src.config.manager import config
import logging

# 加载项目配置
project_config = config.get_project_config("crm")

class BaseWebsiteUser(FastHttpUser):
    """
    Website 用户的基类，封装通用的登录和 Token 管理逻辑
    """
    abstract = True  # 标记为抽象类，Locust 不会直接运行它
    
    # Host 优先使用配置
    host = project_config.get("host")
    token = None

    def on_start(self):
        """
        用户启动时执行登录获取 Token
        """
        self.do_login()

    def do_login(self, retries=3):
        auth_config = project_config.get("auth")
        api_host = project_config.get("api_host")
        
        if not auth_config or not api_host:
            logging.warning("Auth config or API host not found, skipping login.")
            return

        login_url = f"{api_host}/api/crm/v4/user/login"
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Locust Performance Test",
            "Origin": self.host,
            "Referer": f"{self.host}/login"
        }
        
        payload = {
            "username": auth_config.get("username"),
            "password": str(auth_config.get("password")),
            "appPlatform": auth_config.get("appPlatform", "work-space"),
            "appVersion": auth_config.get("appVersion", "1.0.1")
        }

        for attempt in range(retries):
            with self.client.post(login_url, json=payload, headers=headers, catch_response=True, name="API: Login") as response:
                if response.status_code == 200:
                    try:
                        res_json = response.json()
                        # 尝试从常见位置获取 token
                        if isinstance(res_json.get("data"), str):
                            self.token = res_json.get("data")
                        elif isinstance(res_json.get("data"), dict):
                            self.token = res_json.get("data").get("token") or res_json.get("data").get("access_token")
                        
                        if self.token:
                            logging.info(f"Login successful, token: {self.token[:10]}...")
                            return # Success
                        else:
                            logging.warning(f"Login successful but token not found in response: {res_json}")
                            return # No token but success code? Stop retrying.
                    except Exception as e:
                        logging.error(f"Failed to parse login response: {e}")
                        # Don't retry on parsing error unless it's a server issue
                        return 
                else:
                    logging.warning(f"Login failed (Attempt {attempt+1}/{retries}): {response.status_code} - {response.text}")
                    if attempt < retries - 1:
                        import time
                        time.sleep(1) # Wait before retry
                        continue
        
        # All retries failed
        logging.error("All login attempts failed. Stopping user.")
        self.stop()
