import time


def work(seconds):
    time.sleep(abs(seconds))


def contains_successor(identification, successor, node):
    if identification < node <= successor:
        return True
    elif successor < identification and (node > identification or node < successor):
        return True
    return False
