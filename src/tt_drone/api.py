import base64
import hashlib
import hmac
import json
import os
import time
from email.utils import formatdate
import requests

API_TIMEOUT = 5
MAX_HTTP_RETRIES = 3
VERSION = 1.0

LOG_TRACE = 7
LOG_DEBUG = 6
LOG_INFO = 5
LOG_WARN = 4
LOG_ERROR = 3
LOG_PANIC = 2
LOG_FATAL = 1


class Project:
    def __init__(self, json_obj):
        self.id: int = json_obj["id"]
        self.priority: int = json_obj["priority"]
        self.name: str = json_obj["name"]
        self.clone_url: str = json_obj["clone_url"]
        self.git_repo: str = json_obj["git_repo"]
        self.version: str = json_obj["version"]
        self.motd: str = json_obj["motd"]
        self.public: bool = json_obj["public"]
        self.secret: str

    def toJSON(self):
        return json.dumps({
            "id": self.id, "priority": self.priority, "name": self.name,
            "clone_url": self.clone_url, "git_repo": self.git_repo,
            "version": self.version, "motd": self.motd, "public": self.public,
        })


class Task:
    def __init__(self, json_obj):
        self.id: int = json_obj["id"]
        self.priority: int = json_obj["priority"]
        self.project: Project = Project(json_obj["project"])
        self.retries: int = json_obj["retries"]
        self.max_retries: int = json_obj["max_retries"]
        self.status: int = json_obj["status"]
        self.recipe: str = json_obj["recipe"]
        self.max_assign_time: int = json_obj["max_assign_time"]
        self.assign_time: int = json_obj["assign_time"]
        self.verification_count: int = json_obj["verification_count"]

    def toJSON(self):
        return json.dumps({
            "id": self.id, "priority": self.priority,
            "project": self.project.toJSON(), "retries": self.retries,
            "max_retries": self.max_retries, "status": self.status,
            "recipe": self.recipe, "max_assign_time": self.max_assign_time,
            "verification_count": self.verification_count,
        })


class Worker:
    def __init__(self, wid=None, alias=None, secret=None, api=None):
        self.id: int = wid
        self.alias: str = alias
        self.secret: bytes = base64.b64decode(secret)
        self._secret_b64 = secret
        self._api: TaskTrackerApi = api

    def fetch_task(self, project_id):
        return self._api.fetch_task(self, project_id)

    def submit_task(self, project, recipe, priority=1, max_assign_time=3600, hash64=0, unique_str="",
                    verification_count=1, max_retries=3):
        return self._api.submit_task(self, project, recipe, priority, max_assign_time, hash64, unique_str,
                                     verification_count, max_retries)

    def release_task(self, task_id: int, result: int, verification):
        return self._api.release_task(self, task_id, result, verification)

    def log(self, level: int, message: str, timestamp: int, scope: str):
        return self._api.log(self, level, message, timestamp, scope)

    def request_access(self, project: int, assign=True, submit=True):
        return self._api.request_access(self, project, assign, submit)

    def get_secret(self, project: int):
        return self._api.get_secret(self, project)

    def dump_to_file(self):
        with open("worker.json", "w") as out:
            json.dump({
                "id": self.id,
                "alias": self.alias,
                "secret": self._secret_b64
            }, out)

    @staticmethod
    def from_file(api):
        if os.path.exists("worker.json"):
            with open("worker.json", "r") as f:
                obj = json.load(f)
                return Worker(wid=obj["id"], alias=obj["alias"],
                              secret=obj["secret"], api=api)
        return None


def format_headers(ts: str = None, ua: str = None, wid: int = None, signature: str = None):
    headers = dict()

    if ua is None:
        headers["User-Agent"] = "tt_py_client" + str(VERSION)
    else:
        headers["User-Agent"] = ua

    headers["X-Worker-Id"] = str(wid)
    headers["X-Signature"] = str(signature)
    headers["Timestamp"] = str(ts)

    return headers


class TaskTrackerApi:
    def __init__(self, url: str):
        self.url = url

    def make_worker(self, alias) -> Worker:

        response = self._http_post("/worker/create", body={"alias": alias})
        if response:
            json_response = json.loads(response.text)
            print(response.text)

            if response.status_code != 200:
                raise Exception(json_response["message"])

            worker = Worker(json_response["content"]["worker"]["id"], json_response["content"]["worker"]["alias"],
                            json_response["content"]["worker"]["secret"], self)
            return worker

    def fetch_task(self, worker: Worker, project_id: int) -> Task:
        response = self._http_get("/task/get/%d" % (project_id, ), worker)

        if response:
            json_response = json.loads(response.text)
            if json_response["ok"]:
                return Task(json_response["content"]["task"])
        return None

    def submit_task(self, worker: Worker, project, recipe, priority, max_assign_time, hash64, unique_str,
                    verification_count, max_retries):

        return self._http_post("/task/submit", {
            "project": project,
            "recipe": recipe,
            "priority": priority,
            "max_assign_time": max_assign_time,
            "hash_u64": hash64,
            "unique_str": unique_str,
            "verification_count": verification_count,
            "max_retries": max_retries,
        }, worker)

    def log(self, worker: Worker, level: int, message: str, timestamp: int, scope: str):
        if level == LOG_TRACE:
            return self._http_post("/log/trace", {"level": level, "message": message, "timestamp": timestamp, "scope": scope}, worker)
        if level == LOG_INFO:
            return self._http_post("/log/info", {"level": level, "message": message, "timestamp": timestamp, "scope": scope}, worker)
        if level == LOG_WARN:
            return self._http_post("/log/warn", {"level": level, "message": message, "timestamp": timestamp, "scope": scope}, worker)
        if level == LOG_ERROR:
            return self._http_post("/log/error", {"level": level, "message": message, "timestamp": timestamp, "scope": scope}, worker)

        print("Invalid log level")

    def release_task(self, worker: Worker, task_id: int, result: int, verification: int):
        return self._http_post("/task/release", {
            "task_id": task_id,
            "result": result,
            "verification": verification
        }, worker)

    def request_access(self, worker: Worker, project: int, assign:bool, submit:bool):
        return self._http_post("/project/request_access", {
            "project": project,
            "assign": assign,
            "submit": submit,
        }, worker)

    def get_secret(self, worker: Worker, project: int):
        r = self._http_get("/project/secret/" + str(project), worker)
        if r.status_code == 200:
            return json.loads(r.text)["content"]["secret"]

    def _http_get(self, endpoint: str, worker: Worker = None):
        if worker is not None:
            ts = formatdate(timeval=None, localtime=False, usegmt=True)
            signature = hmac.new(key=worker.secret, msg=(endpoint + ts).encode("utf8"), digestmod=hashlib.sha256).hexdigest()
            headers = format_headers(signature=signature, wid=worker.id, ts=ts)
        else:
            headers = format_headers()
        retries = 0
        while retries < MAX_HTTP_RETRIES:
            try:
                response = requests.get(self.url + endpoint, timeout=API_TIMEOUT,
                                        headers=headers)

                if response.status_code == 429:
                    delay = json.loads(response.text)["rate_limit_delay"] * 20
                    time.sleep(delay)
                    continue

                return response
            except Exception as e:
                retries += 1
                print("ERROR: %s" % (e, ))
                pass
        return None

    def _http_post(self, endpoint: str, body, worker: Worker = None):

        body = json.dumps(body)

        if worker is not None:
            ts = formatdate(timeval=None, localtime=False, usegmt=True)
            signature = hmac.new(key=worker.secret, msg=(body + ts).encode("utf8"), digestmod=hashlib.sha256).hexdigest()
            headers = format_headers(signature=signature, wid=worker.id, ts=ts)
        else:
            headers = format_headers()
        retries = 0
        while retries < MAX_HTTP_RETRIES:
            try:
                response = requests.post(self.url + endpoint, timeout=API_TIMEOUT,
                                         headers=headers, data=body.encode("utf8"))

                if response.status_code == 429:
                    delay = json.loads(response.text)["rate_limit_delay"] * 20
                    time.sleep(delay)
                    continue

                return response
            except Exception as e:
                print(str(type(e)) + str(e))
                retries += 1
                pass
        return None

