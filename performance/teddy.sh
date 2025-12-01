#!/bin/bash
# Get the current directory
WORK_DIR=$(pwd)
# Detect OS
OS_TYPE="$(uname -s)"
# Path to Git Bash (on Windows)
GIT_BASH_PATH="/c/Program Files/Git/bin/bash.exe"
# Log file path
LOG_FILE="$WORK_DIR/logs.txt"

# Check if venv exists
if [ ! -d "../venv_sic" ]; then
    echo "Error: venv_sic directory not found in current directory"
    exit 1
fi

# Check if redis.conf exists
if [ ! -f "../conf/redis/redis.conf" ]; then
    echo "Error: ../conf/redis/redis.conf not found"
    exit 1
fi

# Clear/create log file
> "$LOG_FILE"
echo "Output from main_script.py will be written to logs.txt"

# Cleanup handler
cleanup() {
    echo ""
    echo "Shutting down all processes..."
    
    if [[ "$OS_TYPE" == "Linux" ]]; then
        pkill -TERM redis-server
        pkill -TERM run-google-stt
        pkill -TERM run-gpt
        pkill -TERM -f "python main_script.py"
        sleep 5
        pkill -KILL redis-server 2>/dev/null
        pkill -KILL run-google-stt 2>/dev/null
        pkill -KILL run-gpt 2>/dev/null
        pkill -KILL -f "python main_script.py" 2>/dev/null
        pkill -f "gnome-terminal.*Redis Server"
        pkill -f "gnome-terminal.*Google STT"
        pkill -f "gnome-terminal.*Run GPT"
        pkill -f "gnome-terminal.*NAO GPT"
    else
        taskkill //IM redis-server.exe //F 2>nul
        taskkill //IM python.exe //F 2>nul
        taskkill //IM bash.exe //F 2>nul
    fi
    
    echo "All processes terminated"
    echo "Check logs.txt for output from main_script.py"
    exit 0
}

trap cleanup SIGINT SIGTERM

# --- LINUX SECTION ---
if [[ "$OS_TYPE" == "Linux" ]]; then
    echo "Detected Linux: launching gnome-terminal windows"
    
    # Screen dimensions for 1920x1080 with 30px bottom panel
    SCREEN_WIDTH=1920
    SCREEN_HEIGHT=1050
    WIN_WIDTH=960
    WIN_HEIGHT=525
    
    # Window 1: Redis Server (top-left)
    gnome-terminal --title="Redis Server" \
        --geometry=120x30+0+0 \
        -- bash -c "cd '$WORK_DIR' && source ../venv_sic/bin/activate && redis-server ../conf/redis/redis.conf" &
    
    # Window 2: Run GPT (top-right)
    gnome-terminal --title="Run GPT" \
        --geometry=120x30+$WIN_WIDTH+0 \
        -- bash -c "cd '$WORK_DIR' && source ../venv_sic/bin/activate && run-gpt" &
    
    # Window 3: Google STT (bottom-left)
    gnome-terminal --title="Google STT" \
        --geometry=120x30+0+$WIN_HEIGHT \
        -- bash -c "cd '$WORK_DIR' && source ../venv_sic/bin/activate && run-google-stt" &
    
    sleep 3
    
    # Window 4: NAO GPT (bottom-right) with logging
    gnome-terminal --title="NAO GPT" \
        --geometry=120x30+$WIN_WIDTH+$WIN_HEIGHT \
        -- bash -c "cd '$WORK_DIR' && source ../venv_sic/bin/activate && python -u main_script.py 2>&1 | tee '$LOG_FILE'" &

# --- WINDOWS SECTION (Git Bash version) ---
else
    echo "Detected Windows: launching new Git Bash terminals"
    
    # Redis (top-left)
    start "" "$GIT_BASH_PATH" -i -c "cd '$WORK_DIR'; source ../venv_sic/Scripts/activate; ../conf/redis/redis-server.exe conf/redis/redis.conf"
    
    # Run GPT (top-right)
    start "" "$GIT_BASH_PATH" -i -c "cd '$WORK_DIR'; source ../venv_sic/Scripts/activate; run-gpt"
    
    # Google STT (bottom-left)
    start "" "$GIT_BASH_PATH" -i -c "cd '$WORK_DIR'; source ../venv_sic/Scripts/activate; run-google-stt"
    
    sleep 3
    
    # NAO GPT with logging (bottom-right)
    start "" "$GIT_BASH_PATH" -i -c "cd '$WORK_DIR'; source ../venv_sic/Scripts/activate; python -u main_script.py 2>&1 | tee '$LOG_FILE'"
fi

echo "All terminals launched"
echo "Press Ctrl+C to terminate all processes"

# Keep script running
while true; do
    sleep 1
done