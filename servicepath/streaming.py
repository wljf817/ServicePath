import json
from queue import Queue
from threading import Thread


NDJSON_MIMETYPE = "application/x-ndjson"
_STREAM_END = object()


def stream_operation(operation):
    """Run blocking work and yield each event as one JSON line."""
    events = Queue()

    def emit(event):
        events.put(event)

    def run():
        try:
            result = operation(emit)
            emit({"type": "complete", "result": result})
        except Exception as error:
            emit({"type": "error", "error": str(error)})
        finally:
            events.put(_STREAM_END)

    Thread(target=run, daemon=True).start()
    yield json.dumps({"type": "run_started"}) + "\n"

    while True:
        event = events.get()
        if event is _STREAM_END:
            return
        yield json.dumps(event) + "\n"
