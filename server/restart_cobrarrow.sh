RPC_LOG_FILE="../cobrarrow_RPC.log"
OPTIMIZATION_LOG_FILE="../cobrarrow_Optimization.log"

# Step 1: Kill the existing Flight RPC Server if running
if pgrep -f "flight_server.py" > /dev/null; then
    pkill -f "flight_server.py"
fi

# Step 2: Restart the Flight RPC Server
cd cobrarrow_rpc
nohup python_env/bin/python3 flight_server.py 2>&1 | while read -r line; do 
    echo "$(date '+[%Y-%m-%d %H:%M:%S]') $line" >> $RPC_LOG_FILE
done &
echo "Flight RPC Server restarted."
echo "Flight RPC Server restarted." >> $RPC_LOG_FILE

# Step 3: Kill the existing Optimization Server if running
if pgrep -f "optimization_server.jl" > /dev/null; then
    pkill -f "optimization_server.jl"
fi

# Step 4: Restart the Optimization Server
cd ../COBRArrowOptimization
nohup julia --project=. optimization_server.jl 2>&1  | while read -r line; do 
    echo "$(date '+[%Y-%m-%d %H:%M:%S]') $line" >> $OPTIMIZATION_LOG_FILE
done &
echo "Optimization Server restarted."
echo "Optimization Server restarted." >> $OPTIMIZATION_LOG_FILE

