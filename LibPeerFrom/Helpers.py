import sys

import requests
from enum import Enum

class PingType(Enum):
    NA = 0          # We don't have a ping for this peer yet
    Guess = 1       # We're guessing, based off of packet timings
    Estimate = 2    # We're guessing based off of some sort of geoip thing
    Accurate = 3    # We have an ICMP latency

this_module = sys.modules[__name__]
global IPINFO_TOKEN
IPINFO_TOKEN = ""

class GeoIP:
    ip_addr: str
    region: str
    country: str
    city: str

    # The following are not printed by __str__ or __repr__
    timezone: str
    hostname: str
    org: str

    def __repr__(self):
        s = ""
        needs_prefix_comma = False
        if self.ip_addr is not None:
            s += f"ip_addr:{self.ip_addr}"
            needs_prefix_comma = True
        if self.timezone is not None:
            if needs_prefix_comma: s += ";"
            s += f"timezone:{self.timezone}"
            needs_prefix_comma = True
        if self.country is not None:
            if needs_prefix_comma: s += ";"
            s += f"country:{self.country}"
            needs_prefix_comma = True
        if self.region is not None:
            if needs_prefix_comma: s += ";"
            s += f"region:{self.region}"
            needs_prefix_comma = True
        if self.city is not None:
            if needs_prefix_comma: s += ";"
            s += f"city:{self.city}"
            needs_prefix_comma = True
        
        return f"<{s}>"

    def __init__(self,ip_addr:str,token:str = ""):
        if token == "": token = this_module.IPINFO_TOKEN
        if ip_addr == "": return None
        if token != "": token = "?token="+token
        
        self.ip_addr = ip_addr
        resp = requests.get(f"https://ipinfo.io/{ip_addr}/json{token}")
        data = resp.json()
        
        self.region = ""
        self.country = ""
        self.city = ""
        self.timezone = ""
        self.hostname = ""
        self.org = ""

        
        if 'region' in data.keys(): self.region = data['region']
        if 'country' in data.keys(): self.country = data['country']
        if 'city' in data.keys(): self.city = data['city']
        if 'timezone' in data.keys(): self.timezone = data['timezone']
        if 'org' in data.keys(): self.org = data['org']
        if 'hostname' in data.keys(): self.hostname = data['hostname']


    def __str__(self):
        if self.region is None and self.country is None:
            return ""
        elif self.region is not None and self.country is None:
            return self.region
        elif self.region is None and self.country is not None:
            return self.country
        else:
            return f"{self.region}, {self.country}"