# Directory Structure
```
Arrow/
│
├── client/                          # Client-side APIs for MATLAB and Julia
│   ├── MATLAB_API/                  # MATLAB API code and documentation
│   ├── Julia_API/                   # Julia API code and documentation
│
├── server/                          # Server-side components, including Flight RPC and optimization servers
│   ├── arrow_rpc/           # Python-based Flight RPC server
│   │   ├── __init__.py              # Initializes the flight_rpc_server package
│   │   ├── config.py                # Configuration settings for the Flight RPC server
│   │   ├── flight_server.py         # Main Flight RPC server implementation
│   │   ├── auth_middleware.py       # Middleware for handling authentication in Flight RPC
│   │   ├── persist_service.py       # Service for persisting data
│   │   ├── optimization_client.py   # Client for interacting with the optimization server
│   │   ├── data/                    # Directory containing databases or other data files
│   │   └── requirements.txt         # Python dependencies for the Flight RPC server
│   ├── ArrowOptimization/         # Julia-based optimization server
│   │   ├── Project.toml             # Julia dependencies for the optimization server
│   │   ├── optimization_server.jl   # Main optimization server code in Julia   
│   │   ├── Custom.jl  
│   │   ├── solve.jl   
│   ├── README.md                        # Overall project documentation and setup instructions
│   ├── Server Documentation.md
│   ├── init_arrow.sh           # Script to initialize the Arrow service
│   ├── restart_arrow.sh        # Script to restart the Arrow service
│
├── tests/                           # Unit and integration tests for client and server components
    ├── client_tests/                # Tests for client-side APIs
    └── server_tests/                # Tests for server-side components
        ├── test_flight_server.py    # Test cases for the Flight RPC server
        └── test_persist_service.py  # Test cases for the persist service

```
