from locust import task, constant_pacing, tag
from bs4 import BeautifulSoup
import logging
import os
from projects.crm.scenarios.common import BaseWebsiteUser
from src.config.manager import config

class WebsiteUser(BaseWebsiteUser):
    # 使用 FastHttpUser 提高静态资源下载性能
    wait_time = constant_pacing(3)  # 每个用户每 3 秒执行一次任务
    
    def on_start(self):
        super().on_start()
        self.pages = self.load_pages()

    def load_pages(self):
        """从 data/pages 加载所有 URL"""
        pages = []
        project_root = os.getcwd() # Assumes running from root
        pages_dir = os.path.join(project_root, "projects", "crm", "data", "pages")
        
        if os.path.exists(pages_dir):
            for filename in os.listdir(pages_dir):
                filepath = os.path.join(pages_dir, filename)
                if os.path.isfile(filepath):
                    with open(filepath, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#"):
                                pages.append(line)
        
        if not pages:
            # Fallback if no files or empty
            logging.warning("No pages found in data/pages, using default.")
            pages.append("/admin/me")
            
        logging.info(f"Loaded {len(pages)} pages to test: {pages}")
        return pages

    @task
    @tag('web')
    def load_dynamic_pages(self):
        """
        随机加载列表中的页面并自动发现/下载静态资源
        """
        import random
        if not self.pages:
            return

        target_url = random.choice(self.pages)
        
        # 处理 URL，确保它是相对于 Host 的路径，或者如果是绝对路径则直接使用
        if target_url.startswith("http"):
            # 如果是绝对路径，Locust client.get 通常期望相对路径，但 FastHttpUser 支持绝对路径
            # 为了更好的统计，我们可以提取 path
            from urllib.parse import urlparse
            parsed = urlparse(target_url)
            # 如果 host 不匹配，可能需要警告，但这里直接请求
            url_path = target_url # Use full URL
            request_name = f"Page: {parsed.path}"
        else:
            url_path = target_url
            request_name = f"Page: {target_url}"

        headers = {
            "User-Agent": "Locust Performance Test",
            "Accept-Encoding": "gzip, deflate, br"
        }
        
        # 如果有 Token，添加到 Header
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        # 1. 请求主 HTML 页面
        with self.client.get(url_path, headers=headers, catch_response=True, name=request_name) as response:
            if response.status_code != 200:
                if response.status_code in [301, 302]:
                    logging.info(f"Redirected to: {response.headers.get('Location')}")
                else:
                    response.failure(f"Failed to load page {url_path}: {response.status_code}")
                return
            
            # 2. 解析 HTML 提取静态资源
            soup = BeautifulSoup(response.text, "lxml")
            
            assets = []
            
            # 提取 <script src="...">
            for script in soup.find_all("script", src=True):
                url = script.get("src")
                if url: assets.append(url)
            
            # 提取 <link href="..." rel="stylesheet">
            for link in soup.find_all("link", rel="stylesheet", href=True):
                url = link.get("href")
                if url: assets.append(url)
            
            # 提取 <img src="...">
            for img in soup.find_all("img", src=True):
                url = img.get("src")
                if url: assets.append(url)

            # 去重
            assets = list(set(assets))
            logging.info(f"Found {len(assets)} assets on {url_path}")

            # 3. 并发下载静态资源
            for asset_url in assets:
                # 处理相对路径
                if not asset_url.startswith("http"):
                    if asset_url.startswith("/"):
                        pass 
                    else:
                        asset_url = "/" + asset_url
                
                self.client.get(asset_url, name="Assets", check_response=False)
