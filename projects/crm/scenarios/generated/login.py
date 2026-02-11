from locust import task, HttpUser, constant_pacing
import json

class LoginUser(HttpUser):
    wait_time = constant_pacing(1)
    host = "https://crmapi-dev.spreadwin.cn"

    def on_start(self):
        # 初始化 Headers
        self.client.headers.update({
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
            "authorization": "Bearer null",
            "content-type": "application/json",
            "origin": "https://workspace-dev.spreadwin.cn",
            "priority": "u=1, i",
            "referer": "https://workspace-dev.spreadwin.cn/",
            "sec-ch-ua": "\"Not(A:Brand\";v=\"8\", \"Chromium\";v=\"144\", \"Google Chrome\";v=\"144\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"macOS\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"
})
        
        # 初始化 Cookies (如果存在)
        # self.client.cookies.update({})

    @task
    def generated_task(self):
        # URL: https://crmapi-dev.spreadwin.cn/api/crm/v4/user/login
        with self.client.request("post", "/api/crm/v4/user/login", catch_response=True, json={
            "username": "admin",
            "password": "123123",
            "appPlatform": "work-space",
            "appVersion": "1.0.1"
}) as response:
            if response.status_code >= 400:
                response.failure(f"Request failed with status {response.status_code}")