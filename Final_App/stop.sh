#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# stop.sh — Stop Backend and Frontend services for Final_app
#
# Usage:
#   cd Final_app
#   bash stop.sh
#
# Flags:
#   --backend-only   Kill only the Backend (uvicorn / main.py)
#   --frontend-only  Kill only the Frontend (vite dev server)
# ---------------------------------------------------------------------------

BACKEND_ONLY=false
FRONTEND_ONLY=false
ML_ONLY=false
OLLAMA_ONLY=false

for arg in "$@"; do
  case "$arg" in
    --backend-only)  BACKEND_ONLY=true ;;
    --frontend-only) FRONTEND_ONLY=true ;;
    --ml-only)       ML_ONLY=true ;;
    --ollama-only)   OLLAMA_ONLY=true ;;
  esac
done

killed_any=false

kill_backend() {
  echo "[stop.sh] Stopping Backend (uvicorn / main.py)..."

  # Kill uvicorn processes
  UVICORN_PIDS=$(pgrep -f "uvicorn" 2>/dev/null || true)
  if [ -n "$UVICORN_PIDS" ]; then
    echo "$UVICORN_PIDS" | xargs kill 2>/dev/null && echo "[stop.sh] ✓ Killed uvicorn (PID: $UVICORN_PIDS)"
    killed_any=true
  fi

  # Kill python main.py processes
  MAIN_PIDS=$(pgrep -f "python.*main\.py" 2>/dev/null || true)
  if [ -n "$MAIN_PIDS" ]; then
    echo "$MAIN_PIDS" | xargs kill 2>/dev/null && echo "[stop.sh] ✓ Killed main.py (PID: $MAIN_PIDS)"
    killed_any=true
  fi

  # Free port 8000 if still occupied
  PORT_PID=$(lsof -ti tcp:8000 2>/dev/null || true)
  if [ -n "$PORT_PID" ]; then
    echo "$PORT_PID" | xargs kill -9 2>/dev/null && echo "[stop.sh] ✓ Freed port 8000 (PID: $PORT_PID)"
    killed_any=true
  fi

  if [ "$killed_any" = false ]; then
    echo "[stop.sh] No Backend processes found."
  fi
}

kill_frontend() {
  echo "[stop.sh] Stopping Frontend (vite dev server)..."
  local killed_fe=false

  # Kill vite processes
  VITE_PIDS=$(pgrep -f "vite" 2>/dev/null || true)
  if [ -n "$VITE_PIDS" ]; then
    echo "$VITE_PIDS" | xargs kill 2>/dev/null && echo "[stop.sh] ✓ Killed vite (PID: $VITE_PIDS)"
    killed_fe=true
    killed_any=true
  fi

  # Free port 8082 if still occupied
  PORT_PID=$(lsof -ti tcp:8082 2>/dev/null || true)
  if [ -n "$PORT_PID" ]; then
    echo "$PORT_PID" | xargs kill -9 2>/dev/null && echo "[stop.sh] ✓ Freed port 8082 (PID: $PORT_PID)"
    killed_fe=true
    killed_any=true
  fi

  if [ "$killed_fe" = false ]; then
    echo "[stop.sh] No Frontend processes found."
  fi
}

kill_ml() {
  echo "[stop.sh] Stopping ML Inference Server (gradio / app.py)..."
  local killed_ml=false

  ML_PIDS=$(pgrep -f "python.*app\.py" 2>/dev/null || true)
  if [ -n "$ML_PIDS" ]; then
    echo "$ML_PIDS" | xargs kill 2>/dev/null && echo "[stop.sh] ✓ Killed app.py (PID: $ML_PIDS)"
    killed_ml=true
    killed_any=true
  fi

  PORT_PID=$(lsof -ti tcp:7860 2>/dev/null || true)
  if [ -n "$PORT_PID" ]; then
    echo "$PORT_PID" | xargs kill -9 2>/dev/null && echo "[stop.sh] ✓ Freed port 7860 (PID: $PORT_PID)"
    killed_ml=true
    killed_any=true
  fi

  if [ "$killed_ml" = false ]; then
    echo "[stop.sh] No ML Inference processes found."
  fi
}

kill_ollama() {
  echo "[stop.sh] Stopping Ollama server..."
  local killed_ol=false

  OLLAMA_PIDS=$(pgrep -f "ollama serve" 2>/dev/null || true)
  if [ -n "$OLLAMA_PIDS" ]; then
    echo "$OLLAMA_PIDS" | xargs kill 2>/dev/null && echo "[stop.sh] ✓ Killed ollama serve (PID: $OLLAMA_PIDS)"
    killed_ol=true
    killed_any=true
  fi

  if [ "$killed_ol" = false ]; then
    echo "[stop.sh] No Ollama server processes found."
  fi
}

# ── Main ───────────────────────────────────────────────────────────────────
if [ "$BACKEND_ONLY" = true ]; then
  kill_backend
elif [ "$FRONTEND_ONLY" = true ]; then
  kill_frontend
elif [ "$ML_ONLY" = true ]; then
  kill_ml
elif [ "$OLLAMA_ONLY" = true ]; then
  kill_ollama
else
  kill_backend
  kill_frontend
  kill_ml
fi

echo ""
echo "[stop.sh] Done."

