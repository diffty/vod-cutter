import subprocess
import urllib
import xml.etree.ElementTree as ET

import requests


class VLCInterface:
    def __init__(self, path, port=8080, auth=("", "test")):
        self.auth = auth
        self.port = port
        self.path = path
        self.process = None
    
    def launch(self):
        self.process = subprocess.Popen([self.path, "--extraintf=http", "--http-port", str(self.port), "--http-password", self.auth[1]])

    def open_url(self, url):
        file_url = urllib.parse.quote(url)
        r = requests.get(f"http://localhost:{self.port}/requests/status.xml?command=in_play&input={file_url}", auth=self.auth)
        return ET.fromstring(r.text)

    def get_status(self):
        r = requests.get(f"http://localhost:{self.port}/requests/status.xml", auth=self.auth)
        return ET.fromstring(r.text)
    
    def get_current_time(self):
        xml_status = self.get_status()
        position = float(xml_status.find("position").text)
        length = int(xml_status.find("length").text)
        return length * position
    
    def set_current_time(self, new_time):
        r = requests.get(f"http://localhost:{self.port}/requests/status.xml?command=seek&val={new_time}", auth=self.auth)
        return ET.fromstring(r.text)

    def get_duration(self):
        xml_status = self.get_status()
        length = int(xml_status.find("length").text)
        return length