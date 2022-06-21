import pyshark
from ping3 import ping
from LibPeerFrom.Helpers import GeoIP, PingType
from datetime import datetime, timedelta

class Peer:
    ping_type: PingType
    local_ip: str
    packet_data_sent: set[str]
    packets_resent: int
    remote_ip: str
    packets_sent: int
    packets_received: int
    first_seen: datetime
    last_seen: datetime
    times_seen: int
    ping: float
    geoip: GeoIP


    def __init__(self, local_ip: str, packet: pyshark.packet):
        if 'udp' not in packet: return None
        self.ping_type = PingType.NA
        self.local_ip = local_ip
        self.packet_data_sent = set()
        self.packets_resent = 0
        if packet['ip'].src == local_ip: 
            self.remote_ip = packet['ip'].dst
            self.packets_sent = 1
            self.packets_received = 0
            if 'data' in packet:
                self.packet_data_sent.add(packet['data'].data)
        elif packet['ip'].dst == local_ip: 
            self.remote_ip = packet['ip'].src
            self.packets_received = 1
            self.packets_sent = 0
        else: raise ValueError("No Local IP Address Found")
        self.first_seen = packet.sniff_time
        self.last_seen = packet.sniff_time
        self.times_seen = 1
        self.ping = -1
        self.geoip = None

    
    def just_seen(self, packet: pyshark.packet) -> int:
        if 'udp' not in packet: return None
        if self.geoip == None: self.geoip = GeoIP(self.remote_ip)
        if packet['ip'].src == self.local_ip:
            self.packets_sent += 1
            if 'data' in packet:
                if packet['data'].data in self.packet_data_sent:
                    self.packets_resent += 1
                else:
                    self.packet_data_sent.add(packet['data'].data)
        elif packet['ip'].dst == self.local_ip:
            self.packets_received += 1
        else:
            return None
        if  self.ping_type == PingType.NA:
            guess = (packet.sniff_time - self.first_seen)/timedelta(milliseconds=1)
            if guess > 5: 
                self.ping = guess # assume we'll never be below 5ms
                self.ping_type = PingType.Guess
        self.last_seen = packet.sniff_time
        self.times_seen += 1
        
        return self.times_seen

    def ping_host(self) -> float:
        if not self.has_accurate_ping():
            # if we're not sure that we'll get a response, do it once
            p = ping(self.remote_ip, unit="ms", timeout = 1)
            if isinstance(p, float):
                self.ping_type = PingType.Accurate
                self.ping = p
        else:
            # otherwise, do three pings and average
            total_ping = 0
            ping_count = 0
            for i in range(3):
                p = ping(self.remote_ip, unit="ms", timeout = 1)
                if isinstance(p, float):
                    total_ping += p
                    ping_count += 1
            if ping_count > 0:
                self.ping = total_ping / ping_count
        return self.ping
            
    def estimate_geoip(self):
        if self.geoip is None:
            self.geoip = GeoIP(self.remote_ip)

    def has_accurate_ping(self) -> bool:
        return self.ping_type == PingType.Accurate

    def get_ping(self) -> float:
        return self.ping
    
    def __str__(self):        
        try:
            packet_resent_perc = str(100*self.packets_resent / self.packets_sent) + "0000000"
        except:
            packet_resent_perc = "NA"
        ping_type_display = f"({self.ping_type.name}).".lower()
        duration: timedelta = self.last_seen - self.first_seen
        s = ""
        try:
            s = f"{self.remote_ip:15}: {int(self.get_ping()):3} ms " \
                f"{ping_type_display:12} " \
                f"{packet_resent_perc[:4]}% loss. " \
                f"duration {int(duration.total_seconds()) // 60:02}:{int(duration.total_seconds()) % 60:02}. " \
                f"({self.geoip})"
        except:
            pass

        return s
