# check_drone_builds

Icinga2 check to monitor whether your drone builds are all passing.  
The script has been written and tested on python 3.12 for usage on Ubuntu 24.04 and Debian 12.

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
object CheckCommand "mullvad-account-exp" {
    import "plugin-check-command"
    command = [ PluginDir + "/check_mullvad_account_exp.py" ]
    timeout = 2m
    arguments += {
        "-a" = {
            description = "Account number"
            required = true
            value = "$mullvad_account$"
        }
        "-c" = {
            description = "Critical days"
            required = false
            value = "$mullvad_critical$"
        }
        "-w" = {
            description = "Warning days"
            required = false
            value = "$mullvad_warning$"
        }
    }
}
```

Additionally, add `drone_token` to the *Protected Custom Variables* in the monitoring module of icingaweb2 so it won't show up in plaintext. 

GLHF.