import os
import logging
import json
import time
import hmac
import hashlib
import base64
import urllib.parse
import smtplib
import zipfile
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import requests
from src.config.manager import config

logger = logging.getLogger(__name__)

class Notifier:
    def __init__(self):
        self.config = config.get("notification", {})
        # Global switch
        self.enabled = self.config.get("enabled", False)
        # Channel switches
        self.enable_dingtalk = self.config.get("dingtalk", {}).get("enabled", False)
        self.enable_wechat = self.config.get("wechat", {}).get("enabled", False)
        self.enable_email = self.config.get("email", {}).get("enabled", False)

    def send_report(self, report_path, project_name, stats=None):
        if not self.enabled:
            logger.info("Notifications are globally disabled.")
            return

        # Prepare ZIP file
        zip_path = self._zip_report(report_path)
        
        # Construct message content
        title = f"Locust Test Report - {project_name}"
        tester = stats.get("tester", self.config.get("tester", "Unknown"))
        department = stats.get("department", self.config.get("department", "Unknown"))
        host = stats.get("host", "Unknown")
        start_time = stats.get("start_time", time.strftime('%Y-%m-%d %H:%M:%S'))
        duration = stats.get("duration", "0s")
        users = stats.get("users", "Unknown")
        
        requests = stats.get('requests', 0)
        failures = stats.get('failures', 0)
        rps = stats.get('rps', 0.0)
        
        failure_rate = 0.0
        if requests > 0:
            failure_rate = (failures / requests) * 100.0

        avg_rt = stats.get('avg_rt', 0.0)
        max_rt = stats.get('max_rt', 0.0)
        p95_rt = stats.get('p95_rt', 0.0)
        p99_rt = stats.get('p99_rt', 0.0)

        content = f"各位同事, 大家好:\n"
        content += f"【{project_name}】性能压测于 {start_time} 开始运行，运行时长：{duration}，目前已执行完成。\n\n"
        content += f"测试人： {tester}\n"
        content += f"所属部门： {department}\n"
        content += f"压测环境： `{host}`\n"
        content += f"并发用户数： {users}\n\n"
        content += f"核心指标如下: \n"
        content += f"• 总请求数 (Requests): {requests}\n"
        content += f"• 吞吐量 (RPS): {rps:.2f} /s\n"
        content += f"• 失败率 (Failure Rate): {failure_rate:.2f}% ({failures} failures)\n"
        content += f"• 平均响应时间 (Avg RT): {avg_rt:.0f} ms\n"
        content += f"• P95 响应时间: {p95_rt:.0f} ms\n"
        content += f"• P99 响应时间: {p99_rt:.0f} ms\n"
        content += f"• 最大响应时间 (Max RT): {max_rt:.0f} ms\n\n"

        top_slowest = stats.get("top_slowest", [])
        if top_slowest:
            content += f"耗时最长 Top 5 接口 (P95):\n"
            for i, item in enumerate(top_slowest, 1):
                content += f"{i}. [{item['method']}] {item['name']} - P95: {item['p95']:.0f}ms (Avg: {item['avg']:.0f}ms, Count: {item['count']})\n"
            content += "\n"

        content += f"附件为详细的 HTML 性能报告及数据文件，请查阅。谢谢。"

        # Send Notifications based on channel config
        if self.enable_dingtalk:
            self._send_dingtalk(title, content)
        if self.enable_wechat:
            self._send_wechat(title, content)
        if self.enable_email:
            self._send_email(title, content, zip_path)

    def _zip_report(self, report_path):
        """Compress the HTML report and associated CSV files into a ZIP file"""
        if not report_path or not os.path.exists(report_path):
            logger.warning(f"Report file not found, skipping zip: {report_path}")
            return None
            
        zip_path = report_path.replace(".html", ".zip")
        base_name = os.path.splitext(os.path.basename(report_path))[0]
        report_dir = os.path.dirname(report_path)
        
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add HTML report
                zf.write(report_path, os.path.basename(report_path))
                
                # Add associated CSV files
                for filename in os.listdir(report_dir):
                    if filename.startswith(base_name) and filename.endswith(".csv"):
                        full_path = os.path.join(report_dir, filename)
                        zf.write(full_path, filename)
                        
            return zip_path
        except Exception as e:
            logger.error(f"Failed to zip report: {e}")
            return None

    def _send_dingtalk(self, title, content):
        dt_config = self.config.get("dingtalk", {})
        webhook = dt_config.get("webhook")
        secret = dt_config.get("secret")
        
        if not webhook:
            return

        # Add timestamp and sign if secret is present
        if secret:
            timestamp = str(round(time.time() * 1000))
            secret_enc = secret.encode('utf-8')
            string_to_sign = '{}\n{}'.format(timestamp, secret)
            string_to_sign_enc = string_to_sign.encode('utf-8')
            hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
            sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
            webhook = f"{webhook}&timestamp={timestamp}&sign={sign}"

        data = {
            "msgtype": "text",
            "text": {
                "content": content
            }
        }
        
        try:
            resp = requests.post(webhook, json=data)
            logger.info(f"DingTalk notification sent: {resp.text}")
        except Exception as e:
            logger.error(f"Failed to send DingTalk notification: {e}")

    def _send_wechat(self, title, content):
        wc_config = self.config.get("wechat", {})
        webhook = wc_config.get("webhook")
        
        if not webhook:
            return

        data = {
            "msgtype": "text",
            "text": {
                "content": content
            }
        }
        
        try:
            resp = requests.post(webhook, json=data)
            logger.info(f"WeChat notification sent: {resp.text}")
        except Exception as e:
            logger.error(f"Failed to send WeChat notification: {e}")

    def _send_email(self, title, content, attachment_path):
        email_config = self.config.get("email", {})
        host = email_config.get("smtp_host")
        port = email_config.get("smtp_port")
        sender = email_config.get("sender")
        password = email_config.get("password")
        receivers = email_config.get("receivers")

        if not (host and sender and receivers):
            return

        msg = MIMEMultipart()
        msg['Subject'] = title
        msg['From'] = sender
        msg['To'] = ", ".join(receivers)
        
        msg.attach(MIMEText(content, 'plain'))

        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
                msg.attach(part)

        try:
            if email_config.get("use_ssl"):
                server = smtplib.SMTP_SSL(host, port)
            else:
                server = smtplib.SMTP(host, port)
                server.starttls()
            
            server.login(sender, password)
            server.sendmail(sender, receivers, msg.as_string())
            server.quit()
            logger.info(f"Email sent to {receivers}")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
