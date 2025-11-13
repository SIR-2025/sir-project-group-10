#!/bin/bash

# Get the current directory
WORK_DIR=$(pwd)

# Detect OS
OS_TYPE="$(uname -s)"

# Path to Git Bash (on Windows)
GIT_BASH_PATH="/c/Program Files/Git/bin/bash.exe"

# Check if venv exists
if [ ! -d "venv_sic" ]; then
    echo "Error: venv_sic directory not found in current directory"
    exit 1
fi

# Check if redis.conf exists
if [ ! -f "conf/redis/redis.conf" ]; then
    echo "Error: conf/redis/redis.conf not found"
    exit 1
fi

# Cleanup handler
cleanup() {
    echo ""
    echo "Shutting down all processes..."

    if [[ "$OS_TYPE" == "Linux" ]]; then
        pkill -TERM redis-server
        pkill -TERM run-gpt
        pkill -TERM run-google-stt
        pkill -TERM -f "python demos/nao/nao_gpt.py"
        sleep 5
        pkill -KILL redis-server 2>/dev/null
        pkill -KILL run-gpt 2>/dev/null
        pkill -KILL run-google-stt 2>/dev/null
        pkill -KILL -f "python demos/nao/nao_gpt.py" 2>/dev/null
        pkill -f "gnome-terminal.*Redis Server"
        pkill -f "gnome-terminal.*GPT"
        pkill -f "gnome-terminal.*Google STT"
        pkill -f "gnome-terminal.*NAO GPT"
    else
        taskkill //IM redis-server.exe //F 2>nul
        taskkill //IM python.exe //F 2>nul
        taskkill //IM bash.exe //F 2>nul
    fi
    echo "All processes terminated"
    exit 0
}

trap cleanup SIGINT SIGTERM

# --- LINUX SECTION ---
if [[ "$OS_TYPE" == "Linux" ]]; then
    echo "Detected Linux - launching gnome-terminal windows..."

    gnome-terminal --title="Redis Server" \
        -- bash -c "cd '$WORK_DIR' && source venv_sic/bin/activate && redis-server conf/redis/redis.conf" &

    gnome-terminal --title="GPT" \
        -- bash -c "cd '$WORK_DIR' && source venv_sic/bin/activate && run-gpt" &

    gnome-terminal --title="Google STT" \
        -- bash -c "cd '$WORK_DIR' && source venv_sic/bin/activate && run-google-stt" &

    sleep 3

    gnome-terminal --title="NAO GPT" \
        -- bash -c "cd '$WORK_DIR' && source venv_sic/bin/activate && python demos/nao/nao_gpt.py" &

# --- WINDOWS SECTION (Git Bash version) ---
else
    echo "Detected Windows - launching new Git Bash terminals..."

    # Escape path for Windows Git Bash
    WIN_WORK_DIR=$(cygpath -w "$WORK_DIR")

    # Redis (both redis-server.exe and conf are under conf/redis)
    start "" "$GIT_BASH_PATH" -i -c "cd '$WORK_DIR'; source venv_sic/Scripts/activate; ./conf/redis/redis-server.exe conf/redis/redis.conf; exec bash"

    # GPT
    start "" "$GIT_BASH_PATH" -i -c "cd '$WORK_DIR'; source venv_sic/Scripts/activate; run-gpt; exec bash"

    # Google STT
    start "" "$GIT_BASH_PATH" -i -c "cd '$WORK_DIR'; source venv_sic/Scripts/activate; run-google-stt; exec bash"

    sleep 3

    # NAO GPT
    start "" "$GIT_BASH_PATH" -i -c "cd '$WORK_DIR'; source venv_sic/Scripts/activate; python demos/nao/nao_gpt.py; exec bash"
fi

echo "All terminals launched"
echo "Press Ctrl+C to terminate all processes"

# Keep script running
while true; do
    sleep 1
done
