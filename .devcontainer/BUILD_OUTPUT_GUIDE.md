# Dev Container Build Output Visibility Guide

The `BUILDKIT_PROGRESS: "plain"` setting in `devcontainer.json` may not always show build output in VS Code. Here are several methods to view Docker build logs:

## Method 1: VS Code Command Palette
1. Open Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`)
2. Run: **`Dev Containers: Show Log`**
3. This shows the dev container build and startup logs

## Method 2: Manual Terminal Rebuild
Use the provided script for verbose terminal output:
```bash
./scripts/manual_rebuild_devcontainer.sh
```

This script:
- Stops any existing container
- Rebuilds with `--progress=plain` and `--no-cache`
- Shows full build output in terminal

## Method 3: VS Code Output Panel
1. Open VS Code Output panel (`View > Output`)
2. Select "Dev Containers" from the dropdown
3. Build logs should appear here during container creation

## Method 4: Manual Docker Commands
```bash
# Build with verbose output
cd /workspaces/dynamic-dev-container
DOCKER_BUILDKIT=1 docker build \
    --progress=plain \
    --no-cache \
    --file .devcontainer/Dockerfile \
    --tag dynamic-dev-container:latest \
    .
```

## Method 5: Enhanced devcontainer.json
The current configuration includes:
```json
{
  "build": {
    "args": {
      "BUILDKIT_PROGRESS": "plain",
      "DOCKER_BUILDKIT": "1"
    },
    "options": [
      "--progress=plain",
      "--no-cache"
    ]
  }
}
```

## Troubleshooting
- If build output is still collapsed, try Method 1 or 2
- The "Show Log" command is the most reliable for VS Code
- Manual rebuild script provides the most detailed output
- Use `--no-cache` to ensure fresh builds for debugging

## Build Process Stages
When verbose logging works, you should see:
1. **Base image pull** - Rocky Linux container download
2. **System updates** - Package manager operations
3. **Tool installation** - mise, kubectl, Python dependencies
4. **Environment setup** - .NET, shell configuration
5. **File copying** - Optional workspace files
6. **Cleanup** - Cache clearing and optimization
