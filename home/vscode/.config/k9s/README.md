# Dave Sargent's k9s Config

This [k9s](https://k9scli.io/) configuration has been customized by Dave Sargent with many plugins, hotkeys, aliases, all skins from the k9s repo and a custom skin.

## Installation

These instructions are to install this repositories configuration files and assumes you already have k9s installed. Follow [these instructions](https://k9scli.io/topics/install/) to install k9s.

Clone the repo down and copy its contents into your k9s config directroy.  See the "Overview" section in the [configuration](https://k9scli.io/topics/config/) docs for your OSs config directory or run `k9s info` to see what your instance expects.

Example output of my `k9s info` command.

```
Version:           v0.32.4
Config:            /home/vscode/.config/k9s/config.yaml
Custom Views:      /home/vscode/.config/k9s/views.yaml
Plugins:           /home/vscode/.config/k9s/plugins.yaml
Hotkeys:           /home/vscode/.config/k9s/hotkeys.yaml
Aliases:           /home/vscode/.config/k9s/aliases.yaml
Skins:             /home/vscode/.config/k9s/skins
Context Configs:   /home/vscode/.local/share/k9s/clusters
Logs:              /home/vscode/.local/state/k9s/k9s.log
Benchmarks:        /home/vscode/.local/state/k9s/benchmarks
ScreenDumps:       /temp/k9s
```

The `clusters` folder located here must be copied into the "Context Configs" directory.  See the [clusters/README.md](./clusters/README.md) file for more information.

## Config Notes

- `ctrl+c` to quit is disabled.  Use `:q` to quit instead.  This is the way.

## Navigating k9s

- [k9s Cheatsheet](https://www.hackingnote.com/en/cheatsheets/k9s/index.html)
- `shift+?` for help

## Plugins

Some of the [pugins](https://k9scli.io/topics/plugins/) require other tools to function properly.  
See the `plugins/` directory for more information.

- **Dive:** Requries the Linux [dive](https://github.com/wagoodman/dive) utility.
- **Certificate Renew**, **Certificate Status:** and **Inspect CM Secret:** Are specifically for clusters with `cert-manager` installed and require the Linux [cmctl](https://github.com/cert-manager/cmctl) utility.
- **Get All:** Requires the `krew get-all` plugin.
- **Blame:** Requires the `krew blame` plugn.