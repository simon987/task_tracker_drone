import signal
import threading
import time

from tt_drone.api import (Worker, TaskTrackerApi)
from tt_drone.worker import (WorkerContext)

die = False
lock = threading.Lock()
current_tasks = set()
threads = list()

THREAD_COUNT = 10


def cleanup(signum: int, frame):
    global die
    global threads
    die = True

    print("Waiting for threads to die...")
    for t in threads:
        t.join()
    print("Releasing uncompleted tasks...")
    for k, v in current_tasks:
        worker.release_task(v.id, 2, 0)
    print("Goodbye")


signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)


def drone(ctx: WorkerContext):
    global die

    sorted_projects = sorted(worker.get_project_list(), key=lambda p: p["priority"], reverse=True)

    while not die:
        task = None
        try:
            ok = False
            for project in sorted_projects:
                task = worker.fetch_task(project["id"])
                if task is not None:
                    with lock:
                        current_tasks.add(task.id)
                    ctx.execute_task(task)
                    ok = True
                    break

            if not ok:
                print("No tasks, waiting")
                time.sleep(10)
        finally:
            with lock:
                try:
                    if task is not None:
                        current_tasks.remove(task.id)
                except KeyError:
                    pass


api = TaskTrackerApi("https://tt.simon987.net/api")
worker = Worker.from_file(api)
if not worker:
    worker = api.make_worker("drone")
    worker.dump_to_file()
    projects = worker.get_project_list()
    for project in projects:
        r = worker.request_access(project["id"], assign=True, submit=False)
        print("Request access for %d r=%s" % (project["id"], r.text))

print("Starting %d working contexts" % (THREAD_COUNT,))
for i in range(THREAD_COUNT):
    ctx = WorkerContext(worker, "%s_%d" % (worker.alias, i))

    t = threading.Thread(target=drone, args=[ctx, ])
    t.start()
    threads.append(t)
