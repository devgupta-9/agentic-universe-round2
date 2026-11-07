"""The always-on loop: ingest, reconcile, decide, then advance."""
import json
import os
import time
import httpx
from .client import UncertainWrite
from .governance import Governance
from .learning import Learning
from .store import minute


def peak_memory_mb():
    if os.name != "nt":
        import resource
        import sys
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return value / (1024 * 1024 if sys.platform == "darwin" else 1024)
    import ctypes
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return counters.PeakWorkingSetSize / (1024 * 1024)


class Engine:
    def __init__(self, store, api, crash_after_apply=False):
        self.store, self.api, self.crash_after_apply = store, api, crash_after_apply

    def ingest(self):
        after = self.store.get("last_chunk", -1)
        chunks = self.api.get("/events/chunks", kind="history", after=after)
        chunks += self.api.get("/events/chunks", kind="events", after=after)
        for chunk in sorted(chunks, key=lambda c: c["chunk"]):
            for attempt in range(4):
                try:
                    self.store.ingest(chunk["chunk"], chunk["kind"], self.api.events(chunk["chunk"]))
                    break
                except (httpx.TransportError, json.JSONDecodeError):
                    if attempt == 3:
                        raise
                    time.sleep(.25 * 2 ** attempt)

    def advance(self, state):
        intent = self.store.get("advance_intent")
        if intent and state["sim_minute"] >= intent["to"]:
            self.store.set("advance_intent", None)
            return
        if intent and state["sim_minute"] != intent["from"]:
            raise RuntimeError("An interrupted advance is still in progress; preserve the simulator and restart after it finishes")
        if not intent:
            intent = {"from": state["sim_minute"], "to": min(state["end_minute"], state["sim_minute"] + 60)}
            self.store.set("advance_intent", intent)
        try:
            self.api.write("POST", "/sim/advance", {"minutes": intent["to"] - intent["from"]})
        except UncertainWrite:
            observed = self.api.get("/sim/state")
            if observed["sim_minute"] < intent["to"]:
                raise RuntimeError("Advance result is uncertain; intent retained. Preserve the simulator and restart to reconcile")
        self.store.set("advance_intent", None)

    def run(self):
        started = time.perf_counter()
        state = self.api.get("/sim/state")
        now = minute(state["ts"])
        origin, end = now - state["sim_minute"], now - state["sim_minute"] + state["end_minute"]
        previous = self.store.get("last_state")
        if previous and (previous["scenario"] != state["scenario"] or previous["sim_minute"] > state["sim_minute"] or
                         self.store.get("last_event_id", 0) > state["last_event_id"]):
            raise RuntimeError("This database belongs to a different simulator world; use a fresh CONTROLLER_DB")
        if self.store.get("initial_credit_budget") is None:
            self.store.set("initial_credit_budget", state["credits_remaining"])
        governance = Governance(self.store, self.api, self.crash_after_apply)
        workflows = {w["workflow_id"]: w for w in self.api.get("/workflows")}
        learning = Learning(self.store, self.api, governance, workflows, origin, end)
        performance = self.store.get("performance", {"wall_seconds": 0, "decision_seconds": 0, "decision_ticks": 0, "peak_memory_mb": 0})
        previous_wall = performance["wall_seconds"]
        while True:
            tick_started = time.perf_counter()
            state = self.api.get("/sim/state")
            now = minute(state["ts"])
            self.ingest()
            decision_started = time.perf_counter()
            workflows = {w["workflow_id"]: w for w in self.api.get("/workflows")}
            learning.workflows = workflows
            learning.incidents.workflows = workflows
            governance.reconcile_applied(now)
            learning.handle_applied(now)
            for wid, workflow in sorted(workflows.items()):
                current = self.api.get(f"/workflows/{wid}/config")
                learning.initialize(workflow, current, now)
                if not state["finished"]:
                    learning.decide(workflow, current, now)
            governance.tick(workflows, now)
            learning.handle_applied(now)
            decision_elapsed = time.perf_counter() - decision_started
            performance["decision_seconds"] += decision_elapsed
            performance["decision_ticks"] += 1
            performance["peak_memory_mb"] = max(performance["peak_memory_mb"], peak_memory_mb())
            performance["max_decision_seconds"] = max(performance.get("max_decision_seconds", 0), decision_elapsed)
            performance["simulated_decision_lag_minutes"] = 60
            self.store.set("last_state", state)
            performance["wall_seconds"] = previous_wall + time.perf_counter() - started
            if state["finished"]:
                performance["finished"] = True
                performance["final_sim_minute"] = state["sim_minute"]
                self.store.set("performance", performance)
                self.store.audit(now, "", "run_finished", performance)
                print(json.dumps({"finished": True, "performance": performance, "database": str(self.store.path)}), flush=True)
                return performance
            self.advance(state)
            performance["max_tick_seconds"] = max(performance.get("max_tick_seconds", 0), time.perf_counter() - tick_started)
            self.store.set("performance", performance)
            if state["sim_minute"] % 360 == 0:
                print(json.dumps({"sim_minute": state["sim_minute"], "credits_remaining": state["credits_remaining"],
                                  "last_event_id": self.store.get("last_event_id"), "peak_memory_mb": performance["peak_memory_mb"]}), flush=True)
