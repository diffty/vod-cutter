from utils.time import format_time
import time


class Log:
    def __init__(self):
        self.log = []

    def add(self, msg, prefix="i"):
        full_msg = f"[{format_time(time.time())}][{prefix}] {msg}"
        print(full_msg)
        self.log.append(full_msg)
    
    def write_to_disk(self, filepath):
        fp = open(filepath, "w")
        fp.write("\n".join(self.log))
        fp.close()