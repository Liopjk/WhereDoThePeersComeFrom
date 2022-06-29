from LibPeerFrom.Peer import Peer
from LibPeerFrom.PingCache import PingCache, PingCacheEstimate, PingAccuracy
from LibPeerFrom.Helpers import PingType
from pyshark import packet
from datetime import datetime, timedelta

class Peers:
    _storage: list[Peer]
    _index: set[str]
    _local_ip: str
    sortmode: str
    sortorder: str
    ping_cache: PingCache

    def __init__(self, local_ip, sortmode="last_seen", sortorder="descending", cacheFileName: str = ""):
        if sortmode.lower() not in ["first_seen", "last_seen", "ip", "ping"]: raise ValueError("Invalid sortmode specified")
        if sortorder.lower() not in ["ascending", "descending"]: raise ValueError("Invalid sortorder specified")
        self._storage = list()
        self._index = set()
        self.local_ip = local_ip
        self.sortmode = sortmode.lower()
        self.sortorder = sortorder.lower()
        self.ping_cache = PingCache(cacheFileName)

    def is_private_ip(self, addr: str) -> bool:
        addr = addr.split(".")
        addr = [int(s) for s in addr]
        if addr[0] == 10: 
            return True
        if addr[0] == 172:
            if addr[1] >= 16 and addr[1] < 32:
                return True
        if addr[0] == 192 and addr[1] == 168:
            return True
        return False

    def restore_cache(self) -> None:
        return self.ping_cache.restore_cache()

    def persist_cache(self) -> None:
        return self.ping_cache.persist_cache()

    def add_peer(self, peer: Peer) -> None:
        if  not self.peer_known(peer) \
            and not self.is_private_ip(peer.remote_ip):
            self._storage.append(peer)
            self._index = {p.remote_ip for p in self._storage}
            self.sort_peers()

    def add_peer_from_packet(self, packet: packet) -> None:
        peer = Peer(self.local_ip, packet)
        if self.peer_known(peer):
            self[peer.remote_ip].just_seen(packet)  
        else:
            # packet['data'].data is a string, it has double the length of the actual data
            # as it uses two chars to represent each byte
            # we consider 94 byte packets to be the start of a session
            if 'data' in packet and len(packet['data'].data) == 94*2:
                peer.estimate_geoip()
                if "amazon" not in peer.geoip.org.lower():
                    self.add_peer(peer)    

    def estimate_guess_peers(self) -> None:
        peer: Peer
        for peer in [p for p in self._storage if p.ping_type == PingType.Guess]:
            est: PingCacheEstimate = self.ping_cache.estimate_peer(peer)
            if est.Accuracy != PingAccuracy.NA \
            and est.Estimate.Mean is not None \
            and est.Estimate.Mean > 0:
                self.ping_cache.add_peer(peer)
                self[peer.remote_ip].ping = est.Estimate.Mean
                self[peer.remote_ip].ping_type = PingType.Estimate           

    def peer_known_from_packet(self, packet:packet) -> bool:
        if 'udp' not in packet: return False
        if packet['ip'].dst in self._index: return True
        if packet['ip'].src in self._index: return True
        return False

    def peer_known(self, peer: Peer) -> bool:
        return peer.remote_ip in self._index

    def get_index(self) -> set[str]:
        return self._index
    
    def remove_peer(self, peer: Peer) -> None:
        if peer in self:
            if peer.ping_type in [PingType.Guess, PingType.Accurate]:
                self.ping_cache.add_peer(peer)
            self._storage.remove(peer)                 
            self._index = { p.remote_ip for p in self._storage }
        self.sort_peers()
    
    def ping_peers(self) -> None:
        for peer in self._storage:
            peer.ping_host()

    def remove_stale_peers(self, timestamp: datetime) -> None:
        p: Peer
        for p in list(self._storage):
            if p.last_seen < timestamp:
                self.remove_peer(p)
                continue
            # If we've been in contact for more than 5 minutes but haven't resent anything, remove this peer
            # It's probably a matchmaking server
            if  p.last_seen - p.first_seen > timedelta(minutes=5) \
            and p.packets_resent == 0:
                self._storage.remove(p)
                continue
        self._index = { p.remote_ip for p in self._storage }
        self.sort_peers(ascending=False)

    def sort_peers(self, mode=None, ascending=None) -> None:
        if mode not in ["ping", "first_seen", "ip", "last_seen"]:
            mode = self.sortmode
        if ascending not in [True, False]: 
            ascending = self.sortmode == "ascending"
        if mode == "ping":
            self._storage.sort(reverse=not ascending, key= lambda p: p.get_ping())
        if mode == "first_seen":
            self._storage.sort(reverse=not ascending, key= lambda p: p.first_seen)
        if mode == "ip":
            self._storage.sort(reverse=not ascending, key= lambda p: p.remote_ip)
        if mode == "last_seen":
            p: Peer
            for p in self._storage:
                p.last_seen.microsecond = 0
            self._storage.sort(reverse=not ascending, key= lambda p: p.last_seen)

    def cache_accurate_peers(self):
        peer: Peer
        for peer in self._storage:
            if peer.has_accurate_ping():
                self.ping_cache.add_peer(peer)

    def __getitem__(self, key) -> Peer:
        if key not in self.get_index(): raise KeyError
        for p in self._storage:
            if p.remote_ip == key: return p

    def __iter__(self):
        return self._storage.__iter__()

    def __contains__(self, peer:Peer) -> bool:
        return peer.remote_ip in self._index

    
    def __len__(self) -> int:
        return len(self.get_index())

    def __str__(self) -> str:
        return "\n".join([str(p) for p in self._storage if p.times_seen > 2])