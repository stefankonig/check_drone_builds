# Check_drone_builds

[![Build](https://github.com/stefankonig/check_drone_builds/actions/workflows/build.yml/badge.svg)](https://github.com/stefankonig/check_drone_builds/actions/workflows/build.yml)
[![Coverage](https://raw.githubusercontent.com/stefankonig/check_drone_builds/refs/heads/coverage-badge/coverage.svg)](https://github.com/stefankonig/check_drone_builds/actions/workflows/build.yml)
[![uv](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fstefankonig%2Fcheck_drone_builds%2Frefs%2Fheads%2Fmain%2Fpyproject.toml&style=flat&logo=python&logoColor=lightgrey
)](https://www.python.org)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

Icinga2 check to monitor whether your drone builds are all passing.  
The script has been written and tested on python 3.12 for usage on Ubuntu 24.04 and Debian 12.

## Usage
```console
foo@bar:~$ uv run check_drone_builds.py --help
usage: check_drone_builds.py [-h] --server <DRONE_SERVER> --token <DRONE_TOKEN> [--namespace <NAMESPACE>] [--warning <SECONDS>] [--critical <SECONDS>] [--verbose]

Drone build check all repositories

options:
  -h, --help            show this help message and exit
  --namespace <NAMESPACE>, -n <NAMESPACE>
                        Optional namespace to filter the repositories to check
  --warning <SECONDS>, -w <SECONDS>
                        # of seconds since the last successful build
  --critical <SECONDS>, -c <SECONDS>
                        # of seconds since the last successful build
  --verbose, -v

required arguments:
  --server <DRONE_SERVER>, -s <DRONE_SERVER>
                        URL of the Drone server (without https)
  --token <DRONE_TOKEN>, -t <DRONE_TOKEN>
                        Token to access drone server repositories
```

The check fetches the data from the Drone API. You can retrieve an access token in the Drone user interface by navigating to your user profile.  
When no __warning__ or __critical__ arguments are given, only the last build has to be successful. Mind you, at the moment only the last 25 builds are queried (per repo).

## Icinga CheckCommand definition
```
object CheckCommand "drone-builds" {
    import "plugin-check-command"
    command = [ PluginDir + "/check_drone_builds.py" ]
    timeout = 1m
    arguments += {
        "-c" = {
            description = "Critical seconds"
            required = false
            value = "$drone_critical$"
        }
        "-n" = {
            description = "Filter Namespace"
            required = false
            value = "$drone_namespace$"
        }
        "-s" = {
            description = "Drone Server URL (without https)"
            required = true
            value = "$drone_server$"
        }
        "-t" = {
            description = "Drone API Token"
            required = true
            value = "$drone_token$"
        }
        "-w" = {
            description = "Warning seconds"
            required = false
            value = "$drone_warning$"
        }
    }
}
```

Additionally, add `drone_token` to the *Protected Custom Variables* in the monitoring module of icingaweb2 so it won't show up in plaintext. 

GLHF.