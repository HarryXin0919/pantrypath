"""Headless smoke test for the Streamlit Web UI (app.py).

Skips when streamlit isn't installed (it's the optional ``[web]`` extra), so the
core test suite stays dependency-light. Uses Streamlit's AppTest to actually run
the app script and assert it renders without raising.
"""

import pytest

pytest.importorskip("streamlit", reason="web UI extra not installed")

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def test_app_runs_without_exception():
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    # title is present
    assert any("PantryPath" in t.value for t in at.title)


def test_app_recipe_flow():
    at = AppTest.from_file(APP, default_timeout=30).run()
    # pick a pantry, type a recipe, click "分析整段菜谱"
    at.sidebar.multiselect[0].select("milk").select("white_vinegar").run()
    at.text_area[0].set_value("1 cup buttermilk\n1 tsp vanilla extract").run()
    # first primary button is the recipe analyze button on the first tab
    at.button[0].click().run()
    assert not at.exception
    # the buttermilk substitution (milk+vinegar) should surface somewhere in output
    blob = " ".join(m.value for m in at.markdown)
    assert "buttermilk" in blob
