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

def generate_html_view(headers: list[tuple[str, str]], peers) -> str:
    html =  "<!DOCTYPE html>" \
            "\n<html>" \
            "\n  <head>" \
            "\n  <meta charset=\"utf8\">" \
            "\n  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"> " \
            "\n  <link rel=\"stylesheet\" href=\"./main.css\">"\
            "\n  <script type = \"text/JavaScript\">" \
            "\n    <!--" \
            "\n      function AutoRefresh( t ) {"\
            "\n        setTimeout(\"location.reload(true);\", t);"\
            "\n      }"\
            "\n    //-->" \
            "\n  </script>" \
            "\n    <title>" \
            "WhereDoThePeersComeFrom?" \
            "</title>" 
    html += "\n  </head>"
    html += "\n  <body onload = \"JavaScript:AutoRefresh(1000);\">" 

    if headers is not None and len(headers) > 0:
        header_table =  "\n<h1>Script Parameters</h1><br>" \
                        "<div class=\"container\">" \
                        "\n    <p><table>" \
                        "<th></th>" \
                        "\n     <tb>"
        for h in headers:
            header_table += \
                "\n      <tr>" \
                "\n        <td class=\"left_align\">" + f" {h[0]} " + "</td>" \
                "\n        <td class=\"right_align\">" + f" {h[1]} " + "</td>" \
                "\n      </tr>"
        header_table += "\n    </tb></table></p></div>" 
        html += header_table

    
    
    peers_table =   "<h1>Peers</h1><br>" \
                    "\n<div class=\"container\">"\
                    "\n<p>" \
                    "\n    <table>" \
                    "\n    <th>"\
                    "\n        <tr>"\
                    "\n        <td class=\"center_align\">Remote IP</td>" \
                    "\n        <td class=\"center_align\">Ping</td>" \
                    "\n        <td class=\"center_align\">Ping Type</td>" \
                    "\n        <td class=\"center_align\">Duration</td>" \
                    "\n        <td class=\"center_align\">GeoIP</td>" \
                    "\n        </tr>"\
                    "\n    </th>"\
                    "\n    <tb>"
    if peers is not None and len(peers) > 0:
        for p in peers:
            duration = p.last_seen - p.first_seen
            if p.friendly_name != "": name = p.friendly_name
            else: name = p.remote_ip
            peers_table += \
                "\n      <tr>" \
                "\n        <td class=\"left_align\"> " + f" {name} " + " </td>" \
                "\n        <td class=\"center_align\"> " + f" {int(p.get_ping()):3} ms " + " </td>" \
                "\n        <td class=\"center_align\"> " + f" {p.ping_type.name} " + " </td>" \
                "\n        <td class=\"center_align\"> " \
                    f" {int(duration.total_seconds()) // 60:02}:{int(duration.total_seconds()) % 60:02} " \
                " </td>" \
                "\n        <td class=\"left_align\"> " + f" {p.geoip} " + " </td>" \
                "\n      </tr>" 
        peers_table += "\n    </tb></table></p></div>"     
    html += peers_table
            

        
    html +=  "\n  </body>"
    html += "\n</html>"

    return html
    