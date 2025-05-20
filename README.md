# COBRArrow Directory Structure
```
COBRArrow/
│
├── client/                          # Client-side APIs for MATLAB and Julia
│   ├── MATLAB_API/                  # MATLAB API code and documentation
│   │   ├── COBRArrow.m              # Main MATLAB API class for COBRArrow
│   │   └── COBRArrowSolver.m        # Solver-related functionalities for MATLAB API
│   │   └── requirements.txt         # Python dependencies in order to use Flight RPC.
│   │   └── README.md                # Documentation for MATLAB API
│   ├── Julia_API/                   # Julia API code and documentation
│   │   ├── COBRArrow.jl             # Main Julia API class for COBRArrow
│   │   └── README.md                # Documentation for Julia API
│
├── server/                          # Server-side components, including Flight RPC and optimization servers
│   ├── cobrarrow_rpc/           # Python-based Flight RPC server
│   │   ├── __init__.py              # Initializes the flight_rpc_server package
│   │   ├── config.py                # Configuration settings for the Flight RPC server
│   │   ├── flight_server.py         # Main Flight RPC server implementation
│   │   ├── auth_middleware.py       # Middleware for handling authentication in Flight RPC
│   │   ├── persist_service.py       # Service for persisting data
│   │   ├── optimization_client.py   # Client for interacting with the optimization server
│   │   ├── data/                    # Directory containing databases or other data files
│   │   │   ├── cobrarrow_data.duckdb     # DuckDB database for COBRArrow data
│   │   │   └── cobrarrow_users.duckdb         # DuckDB database for user credentials
│   │   └── requirements.txt         # Python dependencies for the Flight RPC server
│   ├── COBRArrowOptimization/         # Julia-based optimization server
│   │   ├── Project.toml             # Julia dependencies for the optimization server
│   │   ├── optimization_server.jl   # Main optimization server code in Julia   
│   │   ├── CustomCOBRA.jl  
│   │   ├── solve.jl   
│   ├── README.md                        # Overall project documentation and setup instructions
│   ├── COBRArrow Server Documentation.md
│   ├── init_cobrarrow.sh           # Script to initialize the COBRArrow service
│   ├── restart_cobrarrow.sh        # Script to restart the COBRArrow service
│
├── tests/                           # Unit and integration tests for client and server components
    ├── client_tests/                # Tests for client-side APIs
    │   ├── test_matlab_api.m        # MATLAB API test cases
    │   ├── test_julia_api.jl        # Julia API test cases
    └── server_tests/                # Tests for server-side components
        ├── test_flight_server.py    # Test cases for the Flight RPC server
        └── test_persist_service.py  # Test cases for the persist service

```



![alt text](<COBRArrow Architecture.png>)