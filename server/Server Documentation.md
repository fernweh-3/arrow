# COBRArrow Server Documentation

## Overview

The `COBRArrow` server is composed of two main components:

1. **Python-based Flight RPC module**
   - Flight RPC server
   - Authentication Middleware
   - Data Persistence Service
   - Optimization Client
2. **Julia-based Optimization module**
   - Optimization Server

The `cobrarrow_rpc` module in Python provides a flight RPC server for managing and optimizing data. It is built on top of `pyarrow.flight.FlightServerBase` and provides services for storing, retrieving, and optimizing datasets. The server also includes authentication mechanisms and can handle requests using a defined set of RPC methods. 

The `COBRArrowOptimization` contains a Julia-based server which support performing complex optimization tasks using COBRA.jl. 


## COBRArrow RPC Module Overview

The `cobrarrow_rpc` module in Python provides a Flight RPC server designed for managing and optimizing datasets. Built on top of `pyarrow.flight.FlightServerBase`, this server offers a comprehensive suite of services for data storage, retrieval, and optimization. 

### Components

- **Flight RPC Server**: The core implementation of the Flight RPC server, handling client connections and RPC requests.
- **Authentication Middleware**: Ensures secure access through user authentication.
- **Data Persistence Service**: Manages data storage and retrieval operations using DuckDB databases.
- **Optimization Client**: Communicates with the Julia-based optimization server to process and perform complex optimization tasks.

### 1. Flight RPC Server

#### Public Methods

- **list_flights(context, criteria)**: Lists all available flights (datasets). **Requires Authentication**.
- **get_flight_info(context, descriptor)**: Retrieves metadata about a specific flight. **Requires Authentication**.
- **do_put(context, descriptor, reader, writer)**: Stores a new dataset on the server. **Requires Authentication**.
- **do_get(context, ticket)**: Retrieves a dataset using a ticket. **Requires Authentication**.
- **list_actions(context)**: Lists available server actions (e.g., clear, shutdown, optimize). **No Authentication Required**.
- **do_action(context, action)**: Performs an action on the server like optimizing data or shutting down. **Requires Authentication**.
Here's a detailed documentation for the actions available in the `do_action` method of the `FlightServer` class:

    1. **Clear**
       - **Description**: This action is supposed to clear the stored flights (datasets) on the server. However, in the current implementation, it raises a `NotImplementedError` indicating that the feature is not yet implemented.
       - **Response**: Raises a `NotImplementedError`.

    2. **Shutdown**
       - **Description**: This action gracefully shuts down the server. The server will respond to the request, and then shut down in a separate background thread, allowing the current request to finish.
       - **Response**: Sends a `Shutdown!` message back to the client, then initiates server shutdown.

    3. **Optimize**
       - **Description**: This action triggers the optimization of a dataset based on the provided schema name, solver name, and solver parameters. The data associated with the schema is gathered, and then passed to the `OptimizationService` for processing.
       - **Request Body**: Expects a JSON-encoded string in the action body with the following structure:
         - `schema_name`: The name of the schema to optimize.
         - `solver_name`: The name of the solver to use.
         - `solver_params`: A dictionary of solver parameters in JSON format.
       - **Response**: Returns the optimization result if successful. If no data is found for the specified schema, it returns an error message.
       - This example python code demonstrates how to perform an optimization using the `optimize` action.

            ```python
            # Set up the client
            client = pa.flight.FlightClient("grpc://localhost:8816")

            # Prepare the action body
            action_body = {
                "schema_name": "example_schema",
                "solver_name": "GLPK",
                "solver_params": {"tolerance": 1e-6}
            }
            action_body_str = str(action_body)

            # Create and send the action request
            action = pa.flight.Action("optimize", pa.py_buffer(action_body_str.encode('utf-8')))
            results = client.do_action(action)
            ```

    4. **Persist**
       - **Description**: Persists data associated with a specified schema to storage. The action can optionally overwrite existing data. It uses the `PersistService` to handle the persistence process.
       - **Request Body**: Expects a JSON-encoded string with:
         - `schema_name`: The name of the schema to persist.
         - `to_overwrite`: Boolean value ("true"/"false") indicating whether to overwrite existing data.
       - **Response**: Returns a success message upon successful persistence, or an error if the operation fails.
       - This example python code demonstrates how to persist data using the `persist` action.

            ```python
            # Prepare the action body for persisting data
            action_body = {
                "schema_name": "example_schema",
                "to_overwrite": "true"
            }
            action_body_str = str(action_body)

            # Create and send the action request
            action = pa.flight.Action("persist", pa.py_buffer(action_body_str.encode('utf-8')))
            results = client.do_action(action)
            ```

    5. **Load**
       - **Description**: Loads and restores data associated with a specified schema from persistent storage. The action retrieves the data from storage using `PersistService` and makes it available on the server.
       - **Request Body**: Expects a JSON-encoded string with:
         - `schema_name`: The name of the schema to load.
       - **Response**: Returns a success message upon successfully loading the data. If no data is found, it returns an error.
       - This example python code shows how to load data from persistent storage using the `load` action.

            ```python
            # Prepare the action body for loading data
            action_body = {
                "schema_name": "example_schema"
            }
            action_body_str = str(action_body)

            # Create and send the action request
            action = pa.flight.Action("load", pa.py_buffer(action_body_str.encode('utf-8')))
            results = client.do_action(action)
            ```


#### Private Methods

- **descriptor_to_key(descriptor)**: Converts a descriptor to a unique key.
- **_make_flight_info(key, descriptor, table)**: Creates `FlightInfo` objects for flights.
- **_shutdown()**: Shuts down the server after a delay.

### 2. Authentication Middleware

`auth_middleware.py`  implements middleware for handling authentication within the Flight RPC server. It ensures that only authorized users can access certain endpoints or functionalities.

#### Authentication-Free RPC Endpoints

- **list_actions**
- **do_get**
- **list_flights** 
- **get_flight_info** 

#### Endpoints Requiring RPC Authentication
- **do_put**
- **do_action** 


#### Setting Up the Middleware for Authentication on Server Side
The `BasicAuthServerMiddlewareFactory` class reads user credentials from a DuckDB database and issues tokens upon successful authentication. 

In the server code, the authentication middleware can be set up as follows:

```python
server = FlightServer(
    auth_handler=NoOpAuthHandler(),
    location="grpc://0.0.0.0:8816",
    middleware={"basic": BasicAuthServerMiddlewareFactory("cobrarrow_users.duckdb")}
)
```

#### Passing Credentials in Client Requests

When making requests to the server, you need to include the credentials in the `Authorization` header.

**Example for Passing Credentials in Python Client:**

```python
# Set up the client
client = pa.flight.FlightClient("grpc://localhost:8816")

# Encode credentials (username:password) in Base64
credentials = base64.b64encode(b"username:password").decode("utf-8")

# Create headers with the encoded credentials
headers = [("authorization", f"Basic {credentials}")]

# Create call options with headers
options = pa.flight.FlightCallOptions(headers=headers)

# Make a request with the credentials
action = pa.flight.Action("optimize", pa.py_buffer(action_body_str.encode('utf-8')))
results = client.do_action(action, options=options)
```

#### Token-Based Authentication

Once authenticated, the server issues a bearer token that can be used for subsequent requests without needing to resend the username and password.

**Using Bearer Token:**

```python
# Assume you have obtained the token after the first successful authentication
token = "your_token_here"

# Use the token in the Authorization header
headers = [("authorization", f"Bearer {token}")]
options = pa.flight.FlightCallOptions(headers=headers)

# Make a request using the bearer token
results = client.do_action(action, options=options)
```


### 3. Data Persistence Service

The `persist_service.py` module provides services for persisting and retrieving datasets associated with specific schemas. This service allows the server to store data in a DuckDB database and reload it as needed.

#### Core Functions

- **`persist_data(schema_name, data, overwrite=False)`**:
  - **Description**: Persists the given dataset to storage. If `overwrite` is set to `True`, any existing data under the same schema will be replaced.
  - **Arguments**:
    - `schema_name (str)`: The name of the schema under which the data should be stored.
    - `data (Arrow Table)`: The data to be persisted.
    - `overwrite (bool)`: Whether to overwrite existing data (default is `False`).
  - **Returns**: A success message or an error if the operation fails.

- **`load_data(schema_name)`**:
  - **Description**: Loads and restores data associated with the specified schema from persistent storage.
  - **Arguments**:
    - `schema_name (str)`: The name of the schema to load.
  - **Returns**: The retrieved data if found, or an error message if no data is available.

### 4. Optimization Client

The `optimization_client.py` module is responsible for communicating with the Julia-based optimization server. It sends datasets to the Julia server for optimization and retrieves the results.

#### Core Functions

- **`send_optimization_request(schema_name, solver_name, solver_params)`**:
  - **Description**: Sends a dataset along with optimization parameters to the Julia-based server for processing.
  - **Arguments**:
    - `schema_name (str)`: The name of the schema whose data is to be optimized.
    - `solver_name (str)`: The optimization solver to be used (e.g., "GLPK").
    - `solver_params (dict)`: A dictionary of solver parameters.
  - **Returns**: The optimization results or an error message if the optimization fails.

## COBRArrow Optimization Server Overview

The Julia-based optimization server, located in the `COBRArrowOptimization` directory, is responsible for performing complex optimization tasks on datasets received from the Python-based Flight RPC server. The optimization server is built using Julia and leverages powerful optimization libraries such as COBRA.

### Key Components

- **`optimization_server.jl`**:
  - **Description**: This is the main Julia script that starts the optimization server. It listens for incoming requests, processes the data, performs optimization using the specified solver, and returns the results to the requesting client.
  - **Core Functions**:
    - **`start_server(host, port)`**: Starts the server on the specified host and port.
    - **`handle_optimization_request(client)`**: Handles incoming optimization requests, processes the data, performs the optimization, and sends back the results.
    - **`perform_optimization(lpProblem, solverName, solverParams)`**: Executes the optimization based on the problem definition and solver parameters.

### Configuration

- **Project Environment**: The server’s dependencies and environment are managed using Julia’s package management system (`Project.toml`).
- **Dependencies**: The server uses several Julia packages, such as COBRA for optimization and Arrow for data handling.

### Communication with the Python Server

- **Data Exchange**: The Python-based server sends datasets to the Julia server via the `optimization_client.py` module. Data is sent in the Arrow format, and the Julia server processes this data, performs optimization, and sends back the results.
- **Solver Configuration**: The solver and its parameters are configured through requests from the Python server, allowing flexible and powerful optimization capabilities.
