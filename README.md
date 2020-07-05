[![CodeFactor](https://www.codefactor.io/repository/github/simon987/task_tracker_drone/badge)](https://www.codefactor.io/repository/github/simon987/task_tracker_drone)

General purpose 'set and forget' task runner and API wrapper for [simon987/task_tracker](https://github.com/simon987/task_tracker).


### Running tests
```bash
cd src
python -m unittest discover
```


## Usage (task runner daemon)

*(Deprecated, please use [task_tracker_drone_go](https://github.com/simon987/task_tracker_drone_go) to use as a task runner)*


## Usage (Library)

```bash
git submodule add https://github.com/simon987/task_tracker_drone
```

In your project:
```python
from task_tracker_drone.src.tt_drone.api import TaskTrackerApi, Worker, LOG_TRACE

api = TaskTrackerApi(https://tt.simon987.net/api)

worker = Worker.from_file(api)
if not worker:
    worker = api.make_worker("alias")
    worker.dump_to_file()

worker.fetch_task(project_id=1)
worker.submit_task(project=1, 
    recipe="",
    priority="",
    max_assign_time=1,
    hash64=0,
    unique_str="",
    verification_count=1,
    max_retries=1)
worker.bulk_submit_task(project=1, tasks=[])
worker.release_task(task_id=0, result=0, verification=0)
worker.get_project_list()
worker.get_secret(project=1)
worker.log(level=LOG_TRACE, message="", timestamp=0, scope="")
# You will have to manually grant permission from the web UI
worker.request_access(project=1, assign=True, submit=True)
```
