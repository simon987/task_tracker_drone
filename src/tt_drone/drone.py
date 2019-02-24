import signal
import time

die = False


def cleanup(signum, frame):
    global die
    die = True


signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

while True:
    time.sleep(1)
    print("tick")
    if die:
        break

