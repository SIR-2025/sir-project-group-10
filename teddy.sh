#!/bin/bash

# Get the current directory
WORK_DIR=$(pwd)

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

# Screen dimensions for 1920x1080 with 30px bottom panel
SCREEN_WIDTH=1920
SCREEN_HEIGHT=1050
WIN_WIDTH=960
WIN_HEIGHT=525

# Trap Ctrl+C to kill all child processes
cleanup() {
    echo ""
    echo "Shutting down all processes..."
    
    # Kill by process name
    pkill -TERM redis-server
    pkill -TERM run-gpt
    pkill -TERM run-google-stt
    pkill -TERM -f "python demos/nao/nao_gpt.py"
    
    echo "Waiting 5 seconds for graceful shutdown..."
    sleep 5
    
    # Force kill any remaining
    pkill -KILL redis-server 2>/dev/null
    pkill -KILL run-gpt 2>/dev/null
    pkill -KILL run-google-stt 2>/dev/null
    pkill -KILL -f "python demos/nao/nao_gpt.py" 2>/dev/null
    

    # Kill the terminal windows
    pkill -f "gnome-terminal.*Redis Server"
    pkill -f "gnome-terminal.*GPT"
    pkill -f "gnome-terminal.*Google STT"
    pkill -f "gnome-terminal.*NAO GPT"

    echo "All processes terminated"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Window 1: Redis Server (top-left)
gnome-terminal --title="Redis Server" \
    --geometry=120x30+0+0 \
    -- bash -c "cd '$WORK_DIR' && source venv_sic/bin/activate && redis-server conf/redis/redis.conf" &

# Window 2: run-gpt (top-right)
gnome-terminal --title="GPT" \
    --geometry=120x30+$WIN_WIDTH+0 \
    -- bash -c "cd '$WORK_DIR' && source venv_sic/bin/activate && run-gpt" &

# Window 3: run-google-stt (bottom-left)
gnome-terminal --title="Google STT" \
    --geometry=120x30+0+$WIN_HEIGHT \
    -- bash -c "cd '$WORK_DIR' && source venv_sic/bin/activate && run-google-stt" &

# Wait 3 seconds
sleep 3

# Window 4: nao_gpt.py (bottom-right)
gnome-terminal --title="NAO GPT" \
    --geometry=120x30+$WIN_WIDTH+$WIN_HEIGHT \
    -- bash -c "cd '$WORK_DIR' && source venv_sic/bin/activate && python demos/nao/nao_gpt.py" &

echo "All terminals launched"
echo "Press Ctrl+C to terminate all processes"

# Keep script running
while true; do
    sleep 1
done
