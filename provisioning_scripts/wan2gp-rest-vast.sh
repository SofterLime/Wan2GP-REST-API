#!/bin/bash

set -euo pipefail

. /venv/main/bin/activate

apt-get install -y \
    libasound2-dev \
    pulseaudio-utils \
    --no-install-recommends

cd "$WORKSPACE"
[[ -d "${WORKSPACE}/Wan2GP-REST-API" ]] || git clone https://github.com/SofterLime/Wan2GP-REST-API
cd Wan2GP-REST-API
[[ -n "${WAN2GP_VERSION:-}" ]] && git checkout "$WAN2GP_VERSION"

# Find the most appropriate backend given W2GP's torch version restrictions
if [[ -z "${CUDA_VERSION:-}" ]]; then
    echo "Error: CUDA_VERSION is not set or is empty." >&2
    exit 1
fi
cuda_version=$(echo "$CUDA_VERSION" | cut -d. -f1,2)
torch_backend=cu128
# Convert versions like "12.7" and "12.8" to integers "127" and "128" for comparison
cuda_version_int=$(echo "$cuda_version" | awk -F. '{printf "%d%d", $1, $2}')
threshold_version_int=128
if (( cuda_version_int < threshold_version_int )); then
    torch_backend=cu126
fi

uv pip install torch==${TORCH_VERSION:-2.7.1} torchvision torchaudio --torch-backend="${TORCH_BACKEND:-$torch_backend}"
uv pip install -r requirements.txt

# Create Wan2GP startup scripts
cat > /opt/supervisor-scripts/wan2gp-rest-vast.sh << 'EOL'
#!/bin/bash

utils=/opt/supervisor-scripts/utils
. "${utils}/logging.sh"
. "${utils}/cleanup_generic.sh"
. "${utils}/environment.sh"
. "${utils}/exit_serverless.sh"
. "${utils}/exit_portal.sh" "Wan2GP-REST-API"

echo "Starting Wan2GP-REST-API"

. /etc/environment
. /venv/main/bin/activate

cd "${WORKSPACE}/Wan2GP-REST-API"
export XDG_RUNTIME_DIR=/tmp
export SDL_AUDIODRIVER=dummy
python -m server.main 2>&1

EOL

chmod +x /opt/supervisor-scripts/wan2gp-rest-vast.sh

# Generate the supervisor config files
cat > /etc/supervisor/conf.d/wan2gp-rest-vast.conf << 'EOL'
[program:wan2gp-rest-vast]
environment=PROC_NAME="%(program_name)s"
command=/opt/supervisor-scripts/wan2gp-rest-vast.sh
autostart=true
autorestart=true
exitcodes=0
startsecs=0
stopasgroup=true
killasgroup=true
stopsignal=TERM
stopwaitsecs=10
# This is necessary for Vast logging to work alongside the Portal logs (Must output to /dev/stdout)
stdout_logfile=/dev/stdout
redirect_stderr=true
stdout_events_enabled=true
stdout_logfile_maxbytes=0
stdout_logfile_backups=0
EOL

# Register the REST API service in the Vast portal so it is allowed to start
if [[ -f /etc/portal.yaml ]]; then
    if ! grep -q 'Wan2GP-REST-API' /etc/portal.yaml; then
        cat >> /etc/portal.yaml << 'PORTAL'
  Wan2GP-REST-API:
    hostname: localhost
    external_port: 8100
    internal_port: 8100
    open_path: /api/health
    name: Wan2GP-REST-API
PORTAL
        echo "Added Wan2GP-REST-API to /etc/portal.yaml"
    fi
fi

# Update supervisor to start the new service
supervisorctl reread
supervisorctl update