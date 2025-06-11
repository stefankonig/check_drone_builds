import string
import pytest
import json
import re
from unittest.mock import patch, MagicMock
from check_drone_builds import main
from check_drone_builds import CheckDroneBuilds
from requests.models import Response
from pathlib import Path

SERVER = "localhost"
TOKEN = "SUPERSECRET"
NAMESPACE = "docker"
TIME = 1749421177 # 2025-06-08 22:19:37

def get_api_response(uri: string, code: int) -> string:
    with open(f"{get_test_dir()}/ApiResponses/{uri}/{code}.json") as f:
        return f.read()

def get_all_repos_json() -> list:
    return json.loads(get_api_response("user/repos", 200))

def get_builds_json(owner: string, repo: string) -> list:
    return json.loads(get_api_response(f"repos/{owner}/{repo}/builds", 200))

def get_test_dir():
    # Get the root directory of the project
    return Path(__file__).resolve().parent.relative_to(Path.cwd())

def test_script_main():
    test_args = ["check_drone_builds.py", "--server", SERVER, "--token", TOKEN, "--namespace", NAMESPACE, "--warning", "3600", "--critical", "86400", "-v"]
    with patch('sys.argv', test_args):
        with patch("check_drone_builds.CheckDroneBuilds") as mock_main:
            main()
            mock_main.assert_called_with(SERVER, TOKEN, NAMESPACE, 3600, 86400, True)

def test_script_main_defaults():
    test_args = ["check_drone_builds.py", "--server", SERVER, "--token", TOKEN]
    with patch('sys.argv', test_args):
        with patch("check_drone_builds.CheckDroneBuilds") as mock_main:
            main()
            mock_main.assert_called_with(SERVER, TOKEN, "", 9999999999, 9999999999, False)

def check_builds(check: CheckDroneBuilds, repo: list, status: string, message: string) -> None:
    check.get_all_repos = MagicMock()
    check.get_builds_for_repo = MagicMock()
    check.nagios_exit = MagicMock()
    check.get_current_time = MagicMock()

    check.get_all_repos.return_value = repo
    check.get_builds_for_repo.return_value = get_builds_json(repo[0]["namespace"], repo[0]["name"])
    check.get_current_time.return_value = TIME

    check.check_builds()

    check.get_all_repos.assert_called_once_with()
    check.get_builds_for_repo.assert_called_once_with(repo[0]["namespace"], repo[0]["name"])
    check.nagios_exit.assert_called_once_with(status, message)

def check_builds_ok(check: CheckDroneBuilds) -> None:
    repo = [get_all_repos_json()[0]] # first repo has successful build
    check_builds(check, repo, "OK", "BUILDS OK: docker/test-1 - last succeeded: 1 day ago")

def test_check_builds_ok_with_time() -> None:
    check = CheckDroneBuilds(SERVER, TOKEN, NAMESPACE, 86400, 172800, True)
    check_builds_ok(check)

def test_check_builds_ok_without_warning_time() -> None:
    check = CheckDroneBuilds(SERVER, TOKEN, NAMESPACE, 9999999999, 172800, True)
    check_builds_ok(check)

def test_check_builds_ok_without_critical_time() -> None:
    check = CheckDroneBuilds(SERVER, TOKEN, NAMESPACE, 86400, 9999999999, True)
    check_builds_ok(check)

def test_check_builds_ok_without_time() -> None:
    check = CheckDroneBuilds(SERVER, TOKEN, NAMESPACE, 9999999999, 9999999999, True)
    check_builds_ok(check)

def check_builds_all_failed(check: CheckDroneBuilds) -> None:
    repo = [get_all_repos_json()[1]] # second repo has all failing builds
    check_builds(check, repo, "CRITICAL", "Failing build(s): docker/test-2 - last succeeded: Unknown")

def test_check_builds_failed_with_time() -> None:
    check = CheckDroneBuilds(SERVER, TOKEN, NAMESPACE, 86400, 172800, True)
    check_builds_all_failed(check)

def test_check_builds_failed_with_time_only_warning() -> None:
    check = CheckDroneBuilds(SERVER, TOKEN, NAMESPACE, 86400, 9999999999, True)
    check_builds_all_failed(check)

def test_check_builds_failed_with_time_only_critical() -> None:
    check = CheckDroneBuilds(SERVER, TOKEN, NAMESPACE, 9999999999, 172800, True)
    check_builds_all_failed(check)

def test_check_builds_failed_without_time() -> None:
    check = CheckDroneBuilds(SERVER, TOKEN, NAMESPACE, 9999999999, 9999999999, True)
    check_builds_all_failed(check)

def check_builds_partial_failed(check: CheckDroneBuilds, status: string, message: string) -> None:
    repo = [get_all_repos_json()[2]] # third repo has partial failed builds
    check_builds(check, repo, status, message)

def test_check_builds_failed_partial_with_time_ok() -> None:
    check = CheckDroneBuilds(SERVER, TOKEN, NAMESPACE, 12182400, 12182600, True)
    check_builds_partial_failed(check, "OK", "BUILDS OK: docker/test-3 - last succeeded: 140 days ago")

def test_check_builds_failed_partial_with_time_critical() -> None:
    check = CheckDroneBuilds(SERVER, TOKEN, NAMESPACE, 86400, 12096000, True)
    check_builds_partial_failed(check, "CRITICAL", "Failing build(s): docker/test-3 - last succeeded: 140 days ago")

def test_check_builds_failed_partial_with_time_warning() -> None:
    check = CheckDroneBuilds(SERVER, TOKEN, NAMESPACE, 12096000, 12182400, True)
    check_builds_partial_failed(check, "WARNING", "Failing build(s): docker/test-3 - last succeeded: 140 days ago")

def test_check_builds_failed_partial_with_only_time_critical() -> None:
    check = CheckDroneBuilds(SERVER, TOKEN, NAMESPACE, 9999999999, 12096000, True)
    check_builds_partial_failed(check, "CRITICAL", "Failing build(s): docker/test-3 - last succeeded: 140 days ago")

def test_check_builds_failed_partial_with_only_time_warning() -> None:
    check = CheckDroneBuilds(SERVER, TOKEN, NAMESPACE, 12096000, 9999999999, True)
    check_builds_partial_failed(check, "WARNING", "Failing build(s): docker/test-3 - last succeeded: 140 days ago")

def test_check_builds_failed_partial_without_time() -> None:
    check = CheckDroneBuilds(SERVER, TOKEN, NAMESPACE, 9999999999, 9999999999, True)
    check_builds_partial_failed(check, "OK", "BUILDS OK: docker/test-3 - last succeeded: 140 days ago")

def check_builds_empty_builds(check: CheckDroneBuilds) -> None:
    repo = [get_all_repos_json()[3]] # fourth repo has no builds
    check_builds(check, repo, "UNKNOWN", "Unknown build status: docker/test-4")

def test_check_builds_empty_with_time() -> None:
    check = CheckDroneBuilds(SERVER, TOKEN, NAMESPACE, 86400, 172800, True)
    check_builds_empty_builds(check)

def test_check_builds_empty_with_time_only_warning() -> None:
    check = CheckDroneBuilds(SERVER, TOKEN, NAMESPACE, 86400, 9999999999, True)
    check_builds_empty_builds(check)

def test_check_builds_empty_with_time_only_critical() -> None:
    check = CheckDroneBuilds(SERVER, TOKEN, NAMESPACE, 9999999999, 172800, True)
    check_builds_empty_builds(check)

def test_check_builds_empty_without_time() -> None:
    check = CheckDroneBuilds(SERVER, TOKEN, NAMESPACE, 9999999999, 9999999999, True)
    check_builds_empty_builds(check)

def test_check_builds_build_exception():
    check = CheckDroneBuilds(SERVER, TOKEN, NAMESPACE, 2, 1)
    check.get_all_repos = MagicMock()
    check.nagios_exit = MagicMock()

    check.get_all_repos.side_effect = ValueError("An error occurred")
    check.nagios_exit.side_effect = ValueError("STOP") # just so it stops executing any other code, as it would in IRL

    try:
        check.check_builds()
    except Exception:
        pass
    check.nagios_exit.assert_called_once_with("CRITICAL", "Error retrieving repos: An error occurred")

def test_check_builds_incomplete_data():
    check = CheckDroneBuilds(SERVER, TOKEN, NAMESPACE, 2, 1)
    check.get_all_repos = MagicMock()
    check.nagios_exit = MagicMock()

    check.get_all_repos.return_value = "Lassie"
    check.nagios_exit.side_effect = ValueError("STOP") # just so it stops executing any other code, as it would in IRL

    try:
        check.check_builds()
    except Exception:
        pass
    check.nagios_exit.assert_called_once_with("CRITICAL", "Repo API response missing expected data: 'str' object has no attribute 'get'")

def mocked_requests_get(*args, **kwargs):
    request_url = args[0]
    auth_header = kwargs['headers']['Authorization']
    assert auth_header == f"Bearer {TOKEN}"

    match  = re.search(f"^https:\/\/{SERVER}:(?P<response_code>\d+)\/api/(?P<uri>\S+)$", request_url)

    if match:
        response_code = int(match.group('response_code'))
        uri = match.group('uri')
        optional_query_params = re.search("(?P<uri>\S+)\?(?P<query>\S+)",uri)
        if optional_query_params:
            # not checking the query is correct :( letting it bite some dust
            uri = optional_query_params.group('uri')
        response = Response()
        response_content = get_api_response(uri, response_code)
        if 200 < response_code < 300:
            response_code = 200
        response.status_code = response_code
        response._content = str.encode(response_content)
        return response
    else:
        pytest.fail(f"URL[={request_url}] not parsable")
        return None

@patch("requests.get", side_effect=mocked_requests_get)
def test_get_all_repos(mock_get, capsys):
    check = CheckDroneBuilds(f"{SERVER}:200", TOKEN, NAMESPACE, 0, 0)
    repos = check.get_all_repos()
    assert repos == get_all_repos_json()

@patch("requests.get", side_effect=mocked_requests_get)
def test_get_all_repos_error(mock_get, capsys):
    check = CheckDroneBuilds(f"{SERVER}:401", TOKEN, NAMESPACE, 0, 0)
    check.nagios_exit = MagicMock()
    check.nagios_exit.side_effect = ValueError("STOP")  # just so it stops executing any other code, as it would in IRL
    try:
        check.get_all_repos()
    except Exception:
        pass
    check.nagios_exit.assert_called_once_with("UNKNOWN", "Drone API /api/user/repos HTTP status code is 401")

@patch("requests.get", side_effect=mocked_requests_get)
def test_get_all_repos_error_malformed(mock_get, capsys):
    check = CheckDroneBuilds(f"{SERVER}:201", TOKEN, NAMESPACE, 0, 0)
    check.nagios_exit = MagicMock()
    check.nagios_exit.side_effect = ValueError("STOP")  # just so it stops executing any other code, as it would in IRL
    try:
        check.get_all_repos()
    except Exception:
        pass
    check.nagios_exit.assert_called_once_with("UNKNOWN", "Drone API did not respond with valid JSON (Returned code HTTP 200)")

@patch("requests.get", side_effect=mocked_requests_get)
def test_get_all_repos_error_weird_json(mock_get, capsys):
    check = CheckDroneBuilds(f"{SERVER}:202", TOKEN, NAMESPACE, 0, 0)
    check.nagios_exit = MagicMock()
    check.nagios_exit.side_effect = ValueError("STOP")  # just so it stops executing any other code, as it would in IRL
    try:
        check.get_all_repos()
    except Exception:
        pass
    check.nagios_exit.assert_called_once_with("UNKNOWN", "Drone API did not respond with valid JSON (Returned code HTTP 200)")

@patch("requests.get", side_effect=mocked_requests_get)
def test_get_builds_for_repo(mock_get, capsys):
    check = CheckDroneBuilds(f"{SERVER}:200", TOKEN, NAMESPACE, 0, 0)
    builds = check.get_builds_for_repo('docker', 'test-4')
    assert builds == get_builds_json('docker', 'test-4')

@patch("requests.get", side_effect=mocked_requests_get)
def test_get_builds_for_repo_error(mock_get, capsys):
    check = CheckDroneBuilds(f"{SERVER}:401", TOKEN, NAMESPACE, 0, 0)
    check.nagios_exit = MagicMock()
    check.get_all_repos()
    check.nagios_exit.assert_called_once_with("UNKNOWN", "Drone API /api/user/repos HTTP status code is 401")

@patch("requests.get", side_effect=mocked_requests_get)
def test_get_builds_for_repo_error_malformed(mock_get, capsys):
    check = CheckDroneBuilds(f"{SERVER}:201", TOKEN, NAMESPACE, 0, 0)
    check.nagios_exit = MagicMock()
    check.nagios_exit.side_effect = ValueError("STOP")  # just so it stops executing any other code, as it would in IRL
    try:
        check.get_all_repos()
    except Exception:
        pass
    check.nagios_exit.assert_called_once_with("UNKNOWN", "Drone API did not respond with valid JSON (Returned code HTTP 200)")

@patch("requests.get", side_effect=mocked_requests_get)
def test_get_builds_for_repo_error_weird_json(mock_get, capsys):
    check = CheckDroneBuilds(f"{SERVER}:202", TOKEN, NAMESPACE, 0, 0)
    check.nagios_exit = MagicMock()
    check.nagios_exit.side_effect = ValueError("STOP")  # just so it stops executing any other code, as it would in IRL
    try:
        check.get_all_repos()
    except Exception:
        pass
    check.nagios_exit.assert_called_once_with("UNKNOWN", "Drone API did not respond with valid JSON (Returned code HTTP 200)")

