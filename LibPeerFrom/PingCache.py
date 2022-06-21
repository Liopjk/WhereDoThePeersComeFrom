from LibPeerFrom.Helpers import PingType, GeoIP
from LibPeerFrom.Peer import Peer
from enum import Enum

import json


class PingAccuracy(Enum):
    IP = 0
    City = 1
    Region = 2
    Country = 3
    NA = 999

class PingEstimate:
    Low = None
    Mean = None
    High = None
    Count = None

    def __str__(self):
        return f"(Low:{self.Low}; Mean:{self.Mean}; High:{self.High}; Count:{self.Count})"
    
    def __repr__(self):
        return f"<Low:{self.Low}; Mean:{self.Mean}; High:{self.High}; Count:{self.Count}>"

class PingCacheEstimate:
    Estimate: PingEstimate
    Accuracy: PingAccuracy

    def __init__(self):
        self.Estimate = PingEstimate()
        self.Accuracy = PingAccuracy.NA

    def __str__(self):
        return f"(Accuracy: {str(self.Accuracy)}; Estimate: {str(self.Estimate)})"

    def __repr__(self):
        return f"<Accuracy: {self.Accuracy.__repr__()}; Estimate: {self.Estimate.__repr__()}>"

class PingCache:

    _storage: dict[str,list[float]]
    _fileName: str
    hit_count: int

    def __init__(self, fileName: str = ""):
        self._storage = dict()
        self._fileName = fileName
        self.hit_count = 0
        self.minimum_pings = dict()
        

    def has_backing_cache(self):
        # If the filename isn't defined then we don't persist
        return not self._fileName == ""
    
    def add_peer(self, peer:Peer):
        if peer.ping_type in [PingType.Accurate, PingType.Guess]:
            if peer.geoip.city is None: return
            if peer.geoip.region is None: return
            if peer.geoip.country is None: return

            keys: list[str] = [ f"{peer.geoip.country}, {peer.geoip.region}, {peer.geoip.city}",\
                                f"{peer.geoip.country}, {peer.geoip.region}", \
                                f"{peer.geoip.country}"]
            for key in keys:
                self.upsert(key, peer.ping)
        
    def estimate_key(self, key:str) -> PingEstimate:
        estimate = PingEstimate()
        if key in self:
            total = 0
            estimate.Count = len(self._storage[key])
            
            for ping in self._storage[key]:
                if estimate.High is None \
                or estimate.High < ping:
                    estimate.High = ping
                if estimate.Low is None \
                or estimate.Low > ping:
                    estimate.Low = ping
                total += ping
            try:
                estimate.Mean = total / estimate.Count
            except:
                estimate.Mean = -1
            
        return estimate

    def estimate_peer(self, peer:Peer) -> PingCacheEstimate:
        # use the most accurate way we have to 
        cacheEntry = PingCacheEstimate()
        cacheEntry.Accuracy = PingAccuracy.NA
        if peer.geoip is None:
            return cacheEntry
        cityKey = f"{peer.geoip.country}, {peer.geoip.region}, {peer.geoip.city}"
        regionKey = f"{peer.geoip.country}, {peer.geoip.region}"
        countryKey = f"{peer.geoip.country}"
        if cityKey in self:
            cacheEntry.Estimate = self.estimate_key(cityKey)
            cacheEntry.Accuracy = PingAccuracy.City
            self.hit_count += 1
            return cacheEntry
        if regionKey in self:
            cacheEntry.Estimate = self.estimate_key(regionKey)
            cacheEntry.Accuracy = PingAccuracy.Region
            self.hit_count += 1
            return cacheEntry
        if countryKey in self:
            cacheEntry.Estimate = self.estimate_key(countryKey)
            cacheEntry.Accuracy = PingAccuracy.Country
            self.hit_count += 1
            return cacheEntry
        
        
        return cacheEntry

    def persist_cache(self):
        self.remove_nones()
        if self.has_backing_cache():
            with open(self._fileName, 'w') as backingFile:
                # If self.__fileName doesn't exist this will create it
                json.dump(self._storage, backingFile, sort_keys=True, indent=4)

    def remove_nones(self):
        self._storage = {key: self._storage[key] for key in self._storage.keys() \
                        if key is not None \
                        and len(self._storage[key]) > 0}

    def restore_cache(self):
        if self.has_backing_cache():
            try:
                with open(self._fileName, 'r') as backingFile:
                    self._storage = json.load(backingFile)
                    self.remove_nones()
                    
            except FileNotFoundError:
                # We didn't find the file
                # TODO: error here properly?
                pass

    def load_minimum_pings(self) -> None:
        try:
            with open("minimum_ping.json", 'r') as minPingFile:
                self.minimum_pings = json.load(minPingFile)
        except FileNotFoundError:
            pass

    def apply_minimum_pings(self) -> None:
        if not self.has_backing_cache(): return
        
        self.load_minimum_pings()
        minPingKey: str
        for minPingKey in self.minimum_pings.keys():
            minPingValue = self.minimum_pings[minPingKey]
            cacheKey: str
            for cacheKey in self._storage.keys():
                if cacheKey.startswith(minPingKey):
                    current_cache = self._storage[cacheKey]
                    self._storage[cacheKey] = [p for p in current_cache if p > minPingValue]

    def upsert(self,key:str,ping:float) -> None:
        if key is not None:
            if isinstance(ping,float):
                if key not in self:
                    self._storage[key] = []
                if ping not in self._storage[key]:
                    self._storage[key].append(ping)

    def __contains__(self, key:str):
        return key in self._storage.keys()

    def __str__(self):
        return self._storage.__str__()

    def __repr__(self):
        return self._storage.__repr__()

