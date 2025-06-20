#!/usr/bin/env python3

import argparse
import json
import logging
import string
import sys
from datetime import datetime
from typing import NoReturn

import requests


class CheckDroneBuilds:
    def __init__(self, server: str, token: str, namespace: str, warning: int, critical: int, verbose: bool = False):
        self.server = server
        self.token = token
        self.namespace = namespace
        self.critical = critical
        self.warning = warning

        log = logging.getLogger(__name__)
        stream = logging.StreamHandler()
        level = logging.DEBUG if verbose else logging.CRITICAL
        log.setLevel(level)
        stream.setLevel(level)
        log.addHandler(stream)
        
        self.log = log

    def check_builds(self) -> None:
        try:
            repos = self.get_all_repos()
        except Exception as e:
            self.log.exception(str(e))
            self.nagios_exit("CRITICAL", f"Error retrieving repos: {str(e)}")

        successful = []
        warning = []
        critical = []
        unknown = []

        for repo in repos:
            try:
                owner = repo.get("namespace")
                name = repo.get("name")
                slug = repo.get("slug")
                if self.namespace and owner != self.namespace:
                    continue
            except Exception as e:
                self.log.exception(str(e))
                self.log.debug(json.dumps(repo))
                self.nagios_exit("CRITICAL", f"Repo API response missing expected data: {str(e)}")

            last_successful_build = 0

            try:
                builds = self.get_builds_for_repo(owner, name)
                if not builds:
                    unknown.append(slug)
                    self.log.debug(f"No builds found for {slug}, skipping")
                    continue
                for build in builds:
                    if build.get("status") == "success":
                        if build.get("finished") > last_successful_build:
                            last_successful_build = build.get("finished")

            except Exception as e:
                self.log.exception(str(e))
                unknown.append(slug)
                continue

            last_successful_build_string = f"{slug} - last succeeded: {self.time_ago(last_successful_build)}"
            warning_threshold = self.get_current_time() - self.warning
            critical_threshold = self.get_current_time() - self.critical
            self.log.debug(f"{slug} - Warning: {warning_threshold} - Critical: {critical_threshold} - Actual: {last_successful_build}")
            if warning_threshold <= last_successful_build != 0 and critical_threshold <= last_successful_build:
                successful.append(last_successful_build_string)
            elif critical_threshold > last_successful_build or last_successful_build == 0:
                critical.append(last_successful_build_string)
            elif warning_threshold > last_successful_build:
                warning.append(last_successful_build_string)

        if critical:
            self.nagios_exit("CRITICAL", f"Failing build(s): {', '.join(critical)}")
        elif warning:
            self.nagios_exit("WARNING", f"Failing build(s): {', '.join(warning)}")
        elif unknown:
            self.nagios_exit("UNKNOWN", f"Unknown build status: {', '.join(unknown)}")
        elif successful:
            self.nagios_exit("OK", ', '.join(successful))
        else:
            self.nagios_exit("UNKNOWN", "No repos/builds found")

    def get_all_repos(self) -> list:
        headers = {"Authorization": f"Bearer {self.token}"}
        # this call has no upper limit (v2.11.1
        url = f"https://{self.server}/api/user/repos?per_page=1000"
        response = requests.get(url, headers=headers)
        status_code = int(response.status_code)

        if status_code != 200:
            self.log.debug(response.text)
            self.nagios_exit("UNKNOWN", f"Drone API /api/user/repos HTTP status code is {status_code}")
            
        try:
            data = response.json()
            assert isinstance(data, list), "Returned json does not contain a list"
            self.log.debug(json.dumps(data, indent=4))
        except Exception as e:
            self.log.exception(str(e))
            self.nagios_exit("UNKNOWN", f"Drone API did not respond with valid JSON (Returned code HTTP {status_code})")

        self.log.debug(json.dumps(data, indent=4))
        return data

    def get_builds_for_repo(self, owner: string, repo: string) -> list | None:
        headers = {"Authorization": f"Bearer {self.token}"}
        # by default, it only returns 25 results, can up it to max 100 with ?per_page=100 and iterate with ?page=X
        url = f"https://{self.server}/api/repos/{owner}/{repo}/builds"
        response = requests.get(url, headers=headers)
        status_code = int(response.status_code)

        if status_code != 200:
            self.nagios_exit("UNKNOWN", f"Drone API /api/repos/{owner}/{repo}/builds HTTP status code is {status_code}")

        try:
            data = response.json()
            assert isinstance(data, list), "Returned json does not contain a list"
            self.log.debug(json.dumps(data, indent=4))
        except Exception as e:
            self.log.exception(str(e))
            self.nagios_exit("UNKNOWN", f"Drone API did not respond with valid JSON for /api/repos/{owner}/{repo}/builds (Returned code HTTP {status_code})")

        return data

    def nagios_exit(self, status: string, message: string) -> NoReturn:
        codes = {
            "OK" : 0,
            "WARNING"   : 1,
            "CRITICAL"  : 2,
            "UNKNOWN"   : 3
        }
        print(f"{status} - {message}")
        sys.exit(codes[status])

    def get_current_time(self) -> int:
        return int(datetime.now().timestamp())

    def time_ago(self, timestamp: int) -> string:
        if timestamp == 0:
            return "Unknown"

        now = datetime.fromtimestamp(self.get_current_time())
        past_time = datetime.fromtimestamp(timestamp)
        difference = now - past_time

        seconds = difference.total_seconds()

        if seconds < 60:
            return f"{int(seconds)} second{'s' if seconds != 1 else ''} ago"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{int(minutes)} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{int(hours)} hour{'s' if hours != 1 else ''} ago"
        else:
            days = seconds // 86400
            return f"{int(days)} day{'s' if days != 1 else ''} ago"

def main():
    parser = argparse.ArgumentParser(
        description="Drone build check all repositories",
    )
    required = parser.add_argument_group("required arguments")
    required.add_argument(
        "--server",
        "-s",
        type=str,
        metavar="<DRONE_SERVER>",
        help="URL of the Drone server (without https)",
        required=True,
    )
    required.add_argument(
        "--token",
        "-t",
        type=str,
        metavar="<DRONE_TOKEN>",
        help="Token to access drone server repositories",
        required=True,
    )
    parser.add_argument(
        "--namespace", "-n", type=str, metavar="<NAMESPACE>", help="Optional namespace to filter the repositories to check", default=""
    )
    parser.add_argument(
        "--warning", "-w", type=int, metavar="<SECONDS>", help="# of seconds since the last successful build", default=9999999999
    )
    parser.add_argument(
        "--critical", "-c", type=int, metavar="<SECONDS>", help="# of seconds since the last successful build", default=9999999999
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    check = CheckDroneBuilds(args.server, args.token, args.namespace, args.warning, args.critical, args.verbose)
    check.check_builds()

if __name__ == "__main__": # pragma: no cover
    main()
