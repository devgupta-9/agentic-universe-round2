from controller.engine import Engine
from controller.client import UncertainWrite
from controller.store import Store


def test_lost_advance_reply_uses_server_clock_instead_of_advancing_twice(tmp_path):
    class API:
        calls = 0
        def write(self, method, path, body):
            self.calls += 1
            raise UncertainWrite("response lost after advance")
        def get(self, path):
            return {"sim_minute": 60, "finished": False}
    with Store(tmp_path / "state.sqlite3") as store:
        api = API()
        Engine(store, api).advance({"sim_minute": 0, "end_minute": 120})
        assert api.calls == 1
        assert store.get("advance_intent") is None


def test_restarted_controller_reconciles_a_completed_advance(tmp_path):
    class API:
        def write(self, *args):
            raise AssertionError("must not advance again")
    with Store(tmp_path / "state.sqlite3") as store:
        store.set("advance_intent", {"from": 0, "to": 60})
        Engine(store, API()).advance({"sim_minute": 60, "end_minute": 120})
        assert store.get("advance_intent") is None
