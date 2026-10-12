from fakes import FakeClient, start

def test_scenario_run_switches_role_and_asks_once():
    client = FakeClient()
    at = start(client, page="pages/scenarios.py")
    at.button(key="run_acl-supervisor").click().run()
    assert at.session_state["role"] == "supervisor"
    assert client.asks == [("How many overrides can a supervisor grant before a review is "
                            "triggered?", None)]
    assert any("Role switched to supervisor" in t.value for t in at.toast)
    assert any("Look for" in i.value for i in at.info)
    at.run()
    assert len(client.asks) == 1  # not asked again on the next rerun
