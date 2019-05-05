import datetime
import json
import os
import shutil
import subprocess
import time
import traceback
from subprocess import Popen

from tt_drone.api import (Project, Worker, Task)


class WorkerContext:

    def _format_project_path(self, project: Project):
        return "work/%s/%d_%s" % (self._ctx_name, project.id, project.version,)

    def __init__(self, worker: Worker, ctx_name):
        self._worker = worker
        self._projects = dict()
        self._ctx_name = ctx_name

    def _deploy_project(self, project: Project):

        project.secret = self._worker.get_secret(project.id)

        print("Deploying project " + project.name)
        path = self._format_project_path(project)
        if os.path.exists(path):
            shutil.rmtree(path)

        os.makedirs(path, exist_ok=True)
        proc = Popen(args=["git", "clone", project.clone_url, path])
        proc.wait()

        if project.version:
            proc = Popen(args=["git", "checkout", project.version], cwd=os.path.abspath(path))
            proc.wait()

        if os.path.exists(os.path.join(path, "setup")):
            proc = Popen(args=["./setup", ], cwd=os.path.abspath(path))
            proc.wait()

        self._projects[project.id] = project

    def _get_project_path(self, project: Project):
        if project.id not in self._projects or self._projects[project.id].version != project.version:
            self._deploy_project(project)
        return self._format_project_path(project)

    def execute_task(self, task: Task):
        start_time = time.time()
        path = self._get_project_path(task.project)

        if os.path.exists(os.path.join(path, "run")):
            proc = Popen(args=["./run", task.toJSON(), self._projects[task.project.id].secret],
                         stdout=subprocess.PIPE, cwd=os.path.abspath(path))
            result = proc.communicate()[0].decode("utf8")
            try:
                json_result = json.loads(result)
                self._do_post_task_hooks(json_result)
                end_time = time.time()
                print(self._worker.release_task(task.id,
                                                json_result["result"],
                                                json_result[
                                                    "verification"] if "verification" in json_result else 0).text
                      + " in " + str(end_time - start_time) + "s")
            except Exception as e:
                print(str(e) + traceback.format_exc())
        else:
            print(path + "/run doesn't exist!")

    def _do_post_task_hooks(self, res):

        if "logs" in res:
            for log in res["logs"]:
                r = self._worker.log(log["level"] if "level" in log else 7,
                                     log["message"],
                                     log.get("timestamp", int(datetime.datetime.utcnow().timestamp())),
                                     log.get("scope", "tt_py_client"))
                print("LOG: %s <%d>" % (log, r.status_code))

        if "tasks" in res:
            for task in res["tasks"]:
                r = self._worker.submit_task(task["project"],
                                             task["recipe"],
                                             task.get("priority"),
                                             task.get("max_assign_time"),
                                             task.get("hash64"),
                                             task.get("unique_str"),
                                             task.get("verification_count"),
                                             task.get("max_retries"))
                print("SUBMIT: %s <%d>" % (task, r.status_code))

