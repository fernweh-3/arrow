RPC_LOG_FILE="../cobrarrow_RPC.log"
OPTIMIZATION_LOG_FILE="../cobrarrow_Optimization.log"

# Step 1: Set up Python environment
cd cobrarrow_rpc
if [ ! -d "python_env" ]; then
    python3 -m venv python_env
    echo "Python virtual environment created." 
fi
source python_env/bin/activate
pip install -r requirements.txt 

# Step 2: Start the RPC Server
if pgrep -f "flight_server.py" > /dev/null; then
    pkill -f "flight_server.py"
fi
nohup python_env/bin/python3 flight_server.py 2>&1 | while read -r line; do 
    echo "$(date '+[%Y-%m-%d %H:%M:%S]') $line" >> $RPC_LOG_FILE
done &
echo "\n\nFlight RPC Server started."


# Step 3: Manage User Accounts
if [ ! -d "data" ]; then
    mkdir -p data
fi
python_env/bin/python3 user_management.py add --email user@example.com --first-name John --last-name Doe --username johndoe --password 123456
echo "\n\nUser account created. Username: johndoe, Password: 123456" 

# Step 4: Set up Julia environment and dependencies
cd ../COBRArrowOptimization
# Check if CPLEX_STUDIO_BINARIES is set
if [ -z "${CPLEX_STUDIO_BINARIES}" ]; then
    echo "\n\nError: CPLEX_STUDIO_BINARIES is not set. Please set it before running this script." >&2
    echo "Example: export CPLEX_STUDIO_BINARIES=\"/opt/ibm/ILOG/CPLEX_Studio_Community2211/cplex/bin/x86-64_linux\"" >&2
    exit 1
fi
julia -e 'using Pkg; Pkg.activate("."); Pkg.instantiate();' 
echo "\n\nJulia environment set up." 

# Step 5: Start the Optimization Server
if pgrep -f "optimization_server.jl" > /dev/null; then
    pkill -f "optimization_server.jl"
fi
nohup julia --project=. optimization_server.jl 2>&1  | while read -r line; do 
    echo "$(date '+[%Y-%m-%d %H:%M:%S]') $line" >> $OPTIMIZATION_LOG_FILE
done &
echo "\n\nOptimization Server started."
