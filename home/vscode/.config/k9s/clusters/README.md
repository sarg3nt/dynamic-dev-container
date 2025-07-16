# Context Configurations

The clusters directory must be copied to your workstations `~/.local/share/k9s/clusters` directroy, or wherever `k9s info` indicates "Context Configs:" are located.
We do this in our VSCode Dev Container automatically.  

See the [k9s config](https://k9scli.io/topics/config/) "context configuration" section for more information.  

There's not a lot of official documentation on k9s context configs so here's the basics.

- These are used to specifically customize a context.  If you don't want or need to do that, don't worry about them.
- For each context you do want to customize, create a new `config.yaml` in a directory like this:  
`~/.local/share/k9s/clusters/cluster-name/context-name/config.yaml` where `cluster-name` and `context-name` matches what is in your `kube.config` file.
- This is the only place where you can turn on `nodeShell`

## Warnings:

- If the `namespace:` section is commented out `:q` to quit will stop working.


