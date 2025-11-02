#!/bin/bash
echo "=== Setting up NERVA full environment ==="

# 1. Virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. Load environment variables
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# 4. Prepare directories
mkdir -p logs memory data tmp

# 5. Run diagnostics or setup checks
python3 -m core.diagnostics --init

# 6. Start orchestrator
python3 orchestrator.py
