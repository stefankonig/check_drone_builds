#!/usr/bin/env python3

import argparse
import json
import logging
import string
import sys
from typing import Any

import requests


class CheckDroneBuilds:
    def __init__(self, args: argparse.Namespace):
        self.server = args.server
        self.token = args.token
        self.critical = args.critical
        self.warning = args.warning
        log = logging.getLogger("urllib3")
        stream = logging.StreamHandler()
        if args.verbose:
            log.setLevel(logging.DEBUG)
            stream.setLevel(logging.DEBUG)
        log.addHandler(stream)
        self.log = log

    def check_builds_all_repos(self) -> None:
        repos = []
        failed = []
        running = []
        unknown = []

        try:
            repos = self.get_repos(self.server, self.token)
        except Exception as e:
            self.nagios_exit("CRITICAL", f"Error retrieving repos: {str(e)}")

        for repo in repos:
            owner = repo.get("namespace")
            name = repo.get("name")
            slug = f"{owner}/{name}"

            try:
                status, number = self.get_latest_build(self.server, self.token, owner, name)
            except Exception:
                unknown.append(slug)
                continue

            if status == "success":
                continue
            elif status == "failure":
                failed.append(f"{slug} (#{number})")
            elif status == "running":
                running.append(f"{slug} (#{number})")
            else:
                unknown.append(f"{slug} (#{number or '?'})")

        if len(failed) >= self.critical:
            self.nagios_exit("CRITICAL", f"Failing build(s): {', '.join(failed)}")
        elif len(failed) >= self.warning:
            self.nagios_exit("WARNING", f"Failing build(s): {', '.join(failed)}")
        elif unknown:
            self.nagios_exit("UNKNOWN", f"Unknown statuses: {', '.join(unknown)}")
        else:
            self.nagios_exit("OK", "All builds are successful")

    def get_repos(self, drone_server, token) -> dict:
        headers = {"Authorization": f"Bearer {token}"}
        url = f"https://{drone_server}/api/user/repos"
        response = requests.get(url, headers=headers)
        status_code = response.status_code

        try:
            data = response.json()
            self.log.debug(json.dumps(data, indent=4))
        except Exception:
            self.nagios_exit("UNKNOWN", f"Drone API did not respond with valid JSON (Returned code HTTP {status_code})")

        if status_code != 200:
            self.nagios_exit("UNKNOWN", f"Drone API /api/user/repos HTTP status code is {status_code}")
        data = response.json()
        self.log.debug(json.dumps(data, indent=4))
        return data

    def get_latest_build(self, drone_server, token, owner, repo) -> tuple[Any, Any]:
        headers = {"Authorization": f"Bearer {token}"}
        url = f"https://{drone_server}/api/repos/{owner}/{repo}/builds"
        response = requests.get(url, headers=headers)
        status_code = response.status_code
        data = None

        try:
            data = response.json()
            self.log.debug(json.dumps(data, indent=4))
        except Exception:
            self.nagios_exit("UNKNOWN", f"Drone API did not respond with valid JSON for /api/repos/{owner}/{repo}/builds (Returned code HTTP {status_code})")

        if status_code != 200:
            self.nagios_exit("UNKNOWN", f"Drone API /api/repos/{owner}/{repo}/builds HTTP status code is {status_code}")

        if not data:
            return None, None
        return data[0]["status"], data[0]["number"]

    def nagios_exit(self, status: string, message: string) -> None:
        codes = {
            "OK"      : 0,
            "WARNING" : 1,
            "CRITICAL": 2,
            "UNKNOWN" : 3
        }
        print(f"{status} - {message}")
        sys.exit(codes[status])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Drone build check all repositories",
    )
    required = parser.add_argument_group("required arguments")
    required.add_argument(
        "--server",
        "-s",
        type=int,
        metavar="<DRONE_SERVER>",
        help="URL of the Drone server without https",
        required=True,
    )
    required.add_argument(
        "--token",
        "-t",
        type=int,
        metavar="<DRONE_TOKEN>",
        help="Token to access drone repositories",
        required=True,
    )
    parser.add_argument(
        "--warning", "-w", type=int, metavar="<#BUILDS>", help="warning - amount of builds failed", default=0
    )
    parser.add_argument(
        "--critical", "-c", type=int, metavar="<#BUILDS>", help="critical -  amount of builds failed", default=0
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    parseargs = parser.parse_args()

    check = CheckDroneBuilds(parseargs)
    check.check_builds_all_repos()
