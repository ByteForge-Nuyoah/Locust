import socket
import datetime
import gevent
import logging
from influxdb import InfluxDBClient
from locust import events
from src.config.manager import config

logger = logging.getLogger(__name__)

class InfluxDBListener:
    def __init__(self, env):
        self.env = env
        influx_conf = config.get("influxdb", {})
        self.client = InfluxDBClient(
            host=influx_conf.get("host", "localhost"),
            port=int(influx_conf.get("port", 8086)),
            username=influx_conf.get("username", "root"),
            password=influx_conf.get("password", "root"),
            database=influx_conf.get("database", "locust")
        )
        self.hostname = socket.gethostname()
        
        # 订阅事件
        self.env.events.request.add_listener(self.on_request)
        self.env.events.test_start.add_listener(self.on_test_start)
        self.env.events.test_stop.add_listener(self.on_test_stop)
        
        self.user_monitor_greenlet = None

    def on_test_start(self, environment, **kwargs):
        """
        测试开始时启动用户监控协程
        """
        self.user_monitor_greenlet = gevent.spawn(self.monitor_users)

    def on_test_stop(self, environment, **kwargs):
        """
        测试结束时停止用户监控协程
        """
        if self.user_monitor_greenlet:
            self.user_monitor_greenlet.kill()

    def monitor_users(self):
        """
        定期记录当前用户数
        """
        while True:
            try:
                user_count = self.env.runner.user_count
                self.write_user_count(user_count)
            except Exception as e:
                logger.error(f"Error monitoring users: {e}")
            gevent.sleep(1)

    def write_user_count(self, count):
        json_body = [
            {
                "measurement": "locust_users",
                "tags": {
                    "host": self.hostname
                },
                "time": datetime.datetime.utcnow().isoformat(),
                "fields": {
                    "user_count": int(count)
                }
            }
        ]
        try:
            self.client.write_points(json_body)
        except Exception as e:
            logger.error(f"Failed to write user count to InfluxDB: {e}")

    def on_request(self, request_type, name, response_time, response_length, exception, **kwargs):
        """
        Locust request event hook
        """
        success = 1 if exception is None else 0
        error = str(exception) if exception else ""
        
        # 构造 InfluxDB 数据点
        json_body = [
            {
                "measurement": "locust_requests",
                "tags": {
                    "host": self.hostname,
                    "method": request_type,
                    "name": name,
                    "success": str(success),
                    "exception": error
                },
                "time": datetime.datetime.utcnow().isoformat(),
                "fields": {
                    "response_time": float(response_time),
                    "response_length": int(response_length) if response_length else 0,
                    "success": int(success),
                    "fail": 1 if not success else 0
                }
            }
        ]
        
        try:
            self.client.write_points(json_body)
        except Exception as e:
            logger.error(f"Failed to write request to InfluxDB: {e}")
