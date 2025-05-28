import argparse
import string
import pytest
import json
from datetime import datetime, timedelta, timezone
from check_drone_builds import CheckDroneBuilds
from unittest.mock import patch
from requests.models import Response

SERVER = "localhost"
TOKEN = "SUPERSECRET"

def mocked_requests_get(*args, **kwargs):
    response_content = None
    response_code = 500
    request_url = args[0]

    auth_header = kwargs['headers']['Authorization']
    assert auth_header == f"Bearer {TOKEN}"

    if request_url == f"https://{SERVER}:200/api/user/repos":
        response_code = 200
        response_content = get_api_response('repos', response_code)
    elif request_url == f"https://{SERVER}:401/api/user/repos":
        response_code = 401
        response_content = get_api_response('repos', response_code)
    elif request_url == f"https://{SERVER}:500/api/user/repos":
        response_content = "Internal Server Error"
    elif request_url == f"https://{SERVER}:5001/api/user/repos":
        response_code = 200
        response_content = get_api_response('repos', 5001)
    elif request_url == f"https://{SERVER}:5002/api/user/repos":
        response_code = 200
        response_content = get_api_response('repos', 5002)
    else:
        pytest.fail(f"URL[={request_url}] not implemented")
    response = Response()
    response.status_code = response_code
    response._content = str.encode(response_content)
    return response


def get_api_response(uri: string, code: int) -> string:
    with open(f"ApiResponses/{uri}/{code}.json") as f:
        return f.read()


def get_expiration_datetime() -> datetime:
    data = json.loads(get_api_response(200))
    return datetime.fromisoformat(data["updated"])


@patch("sys.exit")
@patch("requests.get", side_effect=mocked_requests_get)
def test_drone_builds_ok(mock_get, mock_sys_exit, capsys):
    url = f"{SERVER}:200"
    args = argparse.Namespace(server=url, token=TOKEN, warning=14, critical=7, verbose=False)
    # expiration_datetime = get_expiration_datetime()
    # expiration_string = expiration_datetime.strftime("%Y-%m-%d %H:%M:%S %Z")
    check = CheckDroneBuilds(args)
    check.check_builds_all_repos()
    captured = capsys.readouterr()
    assert (
        captured.out
        == f"OK - Mullvad VPN account expiration in 15 days ()|days_till_exp=15;14;7\n"
    )


@patch("requests.get", side_effect=mocked_requests_get)
def test_drone_builds_expired_actual_time(mock_get, capsys):
    # test using actual time for timezone issues etc
    args = argparse.Namespace(account=200, warning=14, critical=7, verbose=False)
    expiration_datetime = get_expiration_datetime()
    expiration_string = expiration_datetime.strftime("%Y-%m-%d %H:%M:%S %Z")
    drone_builds = MullvadAccount(args)
    now = datetime.now(timezone.utc)
    with pytest.raises(SystemExit) as system_exit:
        drone_builds.check_expiration_date(now)
    captured = capsys.readouterr()
    expiration_days_delta = expiration_datetime - now
    expiration_days = str(expiration_days_delta.days)
    assert (
        captured.out
        == f"CRITICAL - Mullvad VPN account expiration in {expiration_days} days ({expiration_string})|days_till_exp={expiration_days};14;7\n"
    )
    assert system_exit.value.args[0] == 2


@patch("requests.get", side_effect=mocked_requests_get)
def test_drone_builds_warning(mock_get, capsys):
    args = argparse.Namespace(account=200, warning=16, critical=7, verbose=False)
    expiration_datetime = get_expiration_datetime()
    expiration_string = expiration_datetime.strftime("%Y-%m-%d %H:%M:%S %Z")
    drone_builds = MullvadAccount(args)
    with pytest.raises(SystemExit) as system_exit:
        drone_builds.check_expiration_date(expiration_datetime - timedelta(days=15))
    captured = capsys.readouterr()
    assert (
        captured.out
        == f"WARNING - Mullvad VPN account expiration in 15 days ({expiration_string})|days_till_exp=15;16;7\n"
    )
    assert system_exit.value.args[0] == 1


@patch("requests.get", side_effect=mocked_requests_get)
def test_drone_builds_critical(mock_get, capsys):
    args = argparse.Namespace(account=200, warning=7, critical=16, verbose=False)
    expiration_datetime = get_expiration_datetime()
    expiration_string = expiration_datetime.strftime("%Y-%m-%d %H:%M:%S %Z")
    drone_builds = MullvadAccount(args)
    with pytest.raises(SystemExit) as system_exit:
        drone_builds.check_expiration_date(expiration_datetime - timedelta(days=15))
    captured = capsys.readouterr()
    assert (
        captured.out
        == f"CRITICAL - Mullvad VPN account expiration in 15 days ({expiration_string})|days_till_exp=15;7;16\n"
    )
    assert system_exit.value.args[0] == 2


@patch("requests.get", side_effect=mocked_requests_get)
def test_drone_builds_critical_one_day(mock_get, capsys):
    args = argparse.Namespace(account=200, warning=7, critical=16, verbose=False)
    expiration_datetime = get_expiration_datetime()
    expiration_string = expiration_datetime.strftime("%Y-%m-%d %H:%M:%S %Z")
    drone_builds = MullvadAccount(args)
    with pytest.raises(SystemExit) as system_exit:
        drone_builds.check_expiration_date(expiration_datetime - timedelta(days=1))
    captured = capsys.readouterr()
    assert (
        captured.out
        == f"CRITICAL - Mullvad VPN account expiration in 1 day ({expiration_string})|days_till_exp=1;7;16\n"
    )
    assert system_exit.value.args[0] == 2


@patch("requests.get", side_effect=mocked_requests_get)
def test_drone_builds_account_not_found(mock_get, capsys):
    args = argparse.Namespace(account=404, warning=14, critical=7, verbose=False)
    drone_builds = MullvadAccount(args)
    with pytest.raises(SystemExit) as system_exit:
        drone_builds.check_expiration_date(datetime.now())
    captured = capsys.readouterr()
    assert captured.out == "CRITICAL - Code 404: Mullvad account not found\n"
    assert system_exit.value.args[0] == 2


@patch("requests.get", side_effect=mocked_requests_get)
def test_drone_builds_error(mock_get, capsys):
    args = argparse.Namespace(account=500, warning=14, critical=7, verbose=False)
    drone_builds = MullvadAccount(args)
    with pytest.raises(SystemExit) as system_exit:
        drone_builds.check_expiration_date(datetime.now())
    captured = capsys.readouterr()
    assert (
        captured.out
        == "UNKNOWN - Mullvad API did not respond with valid JSON (Returned code HTTP 500)\n"
    )
    assert system_exit.value.args[0] == 3


@patch("requests.get", side_effect=mocked_requests_get)
def test_drone_builds_invalid_json_account(mock_get, capsys):
    args = argparse.Namespace(account=5001, warning=14, critical=7, verbose=False)
    drone_builds = MullvadAccount(args)
    with pytest.raises(SystemExit) as system_exit:
        drone_builds.check_expiration_date(datetime.now())
    captured = capsys.readouterr()
    assert (
        captured.out == "UNKNOWN - Error Occurred:  Expiry date missing in API return\n"
    )
    assert system_exit.value.args[0] == 3


@patch("requests.get", side_effect=mocked_requests_get)
def test_drone_builds_invalid_json_account_exp(mock_get, capsys):
    args = argparse.Namespace(account=5002, warning=14, critical=7, verbose=False)
    drone_builds = MullvadAccount(args)
    with pytest.raises(SystemExit) as system_exit:
        drone_builds.check_expiration_date(datetime.now())
    captured = capsys.readouterr()
    assert (
        captured.out
        == "UNKNOWN - Error Occurred:  Invalid isoformat string: 'malformed'\n"
    )
    assert system_exit.value.args[0] == 3
