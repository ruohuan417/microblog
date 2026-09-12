from rq import Queue, SimpleWorker

from app import create_app

app = create_app()
queue = Queue('microblog-tasks', connection=app.redis)
worker = SimpleWorker([queue], connection=queue.connection)
worker.work()