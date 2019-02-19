import datetime
import json
import os
import shutil
import subprocess
from subprocess import Popen

from api import Project, Worker, TaskTrackerApi, Task


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
        path = self._get_project_path(task.project)

        if os.path.exists(os.path.join(path, "run")):
            proc = Popen(args=["./run", task.toJSON(), self._projects[task.project.id].secret],
                         stdout=subprocess.PIPE, cwd=os.path.abspath(path))
            result = proc.communicate()[0].decode("utf8")
            try:
                json_result = json.loads(result)
                self._do_post_task_hooks(json_result)
                print(self._worker.release_task(task.id,
                                                json_result["result"],
                                                json_result["verification"] if "verification" in json_result else 0).text)
            except Exception as e:
                print(e)
                return

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


api = TaskTrackerApi("http://localhost:42901")
# w = api.make_worker("python_tt")
# w.dump_to_file()

w1 = Worker.from_file(api)

# print(w1.request_access(1, True, True).text)


# def submit(i):
#     w1.submit_task(project=1, recipe=json.dumps({
#         "tid": str(i),
#     }), hash64=i)


# pool = multiprocessing.Pool(processes=100)
# pool.map(submit, range(0, 500000))
# pool.join()
# print(t.toJSON())

t = w1.fetch_task()

ctx = WorkerContext(w1, "main")
ctx.execute_task(t)