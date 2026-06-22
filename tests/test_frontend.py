import shutil
import pytest
from fastapi.testclient import TestClient
from gdg_yorku_submission.app import app

client = TestClient(app)


def test_static_index_route():
    # Verify we can fetch the index.html from static files mount
    response = client.get("/static/index.html")
    assert response.status_code == 200
    assert "GDG-YorkU Code Review Dashboard" in response.text
    assert 'href="styles.css"' in response.text
    assert 'src="app.js"' in response.text


def test_static_css_route():
    # Verify styles.css is loaded properly
    response = client.get("/static/styles.css")
    assert response.status_code == 200
    assert "--bg-main:" in response.text


def test_static_js_route():
    # Verify app.js is loaded properly
    response = client.get("/static/app.js")
    assert response.status_code == 200
    assert "MOCK_DEMO_REPORT" in response.text



# Let's test with follow_redirects=False to verify the 307 redirect status
def test_ui_redirect_route():
    # By default, client.get follows redirects, so it should resolve to index.html with a 200 status
    response = client.get("/ui")
    assert response.status_code == 200
    assert "GDG-YorkU Code Review Dashboard" in response.text

    # Let's test with follow_redirects=False to verify the 307 redirect status
    response_no_follow = client.get("/ui", follow_redirects=False)
    assert response_no_follow.status_code in (302, 307)
    assert "/static/index.html" in response_no_follow.headers.get("location", "")


@pytest.mark.skipif(not shutil.which("node"), reason="Node.js is not installed/available in PATH")
def test_frontend_dom_behavior():
    # Execute the node-based DOM behavioral test script to verify JS rendering and filtering logic
    import subprocess
    result = subprocess.run(["node", "tests/test_frontend_dom.js"], capture_output=True, text=True)
    assert result.returncode == 0, f"JS DOM tests failed with stdout:\n{result.stdout}\nstderr:\n{result.stderr}"

