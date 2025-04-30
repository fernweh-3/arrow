# Instructions for Using the COBRArrow Service

This guide will walk you through setting up and running the COBRArrow Service on the server side, which includes starting the Flight RPC service in Python, the optimization service in Julia, and managing user accounts.

To set up and run the COBRArrow Service, you can either use the provided bash scripts or follow the step-by-step guide.

## Option 1: Use Bash Script

To simplify the setup process, you can use the provided bash script.

1. **Set the CPLEX_STUDIO_BINARIES Environment Variable**:
   - Before running the script, ensure that the `CPLEX_STUDIO_BINARIES` environment variable is set in order to use COBRA.jl.
    ```sh
     export CPLEX_STUDIO_BINARIES="/your/path/to/CPLEX/binary"
     ```
    Example: 
    ```bash
    export CPLEX_STUDIO_BINARIES="/opt/ibm/ILOG/CPLEX_Studio_Community2211/cplex/bin/x86-64_linux"
    ```
2. **Run the Initialization Script**:
   - Make the script executable and run it.
     ```sh
     chmod +x init_cobrarrow.sh
     ./init_cobrarrow.sh
     ```
3. **If the service is terminated abruptly, restart the service using `restart_cobrarrow.sh`**
    ```sh
     chmod +x ./restart_cobrarrow.sh && ./restart_cobrarrow.sh
     ```

## Option 2: Step-by-Step Guide
### Step 1: Start the Flight RPC Service

#### 1.1 Create the Python Environment and Install Dependencies

Navigate to the `cobrarrow_rpc` directory:
```sh
cd cobrarrow_rpc
```

1. **Create a virtual environment**:
   ```sh
   python3 -m venv python_env
   ```

2. **Activate the virtual environment**:
   - On Windows:
     ```sh
     .\python_env\Scripts\activate
     ```
   - On macOS and Linux:
     ```sh
     source python_env/bin/activate
     ```

3. **Install the required dependencies**:
   ```sh
   pip install -r requirements.txt
   ```

#### 1.2 Start the RPC Server

**Run the RPC server**:

The server is running on port `50051` by default. The `sudo` command is used if root privileges are required (e.g., for binding to port 443).

```sh
python_env/bin/python3 flight_server.py
```

or **Run the RPC server in the background**:

- On Unix-based systems (Linux and macOS):
  ```sh
  nohup python_env/bin/python3 flight_server.py &
  ```

- On Windows, you can use the `start` command in a Command Prompt window:
  ```sh
  start /B python_env\Scripts\python.exe flight_server.py
  ```


### Step 2: Manage User Accounts
1. **Create the `data` Directory**
   
   Navigate to the `cobrarrow_rpc` directory and create a `data` directory:
   ```sh
   mkdir data
   ```
2. **Execute User Management Commands**
   
   Ensure the `user_management.py` script is in the `cobrarrow_rpc` directory or provide the full path to the script.

#### 2.1 Add a User

To add a new user to the system, use the following command. Replace the example email, first name, last name, username, and password with the actual values for the new user you want to add.

```sh
python user_management.py add --email user@example.com --first-name John --last-name Doe --username johndoe --password 123456
```

#### 2.2 Show All Users

To display all users and their statuses:

```sh
python user_management.py show
```

#### 2.3 Change User Password

To change the password of an existing user:

```sh
python user_management.py change-password --username johndoe --new-password newpassword123
```

#### 2.4 Delete a User

To mark a user as inactive:

```sh
python user_management.py delete --username johndoe
```

### Step 3: Start the Optimization Service

Navigate to the `COBRArrowOptimization` directory:
```sh
cd ../COBRArrowOptimization
```

#### 3.1 Create the Julia Environment and Install Dependencies

1. **Open Julia REPL**: Start the Julia REPL by running `julia` from your terminal or command prompt. This will open an interactive Julia session.
    ```sh
    julia
    ```

2. **Activate the Julia Environment**: In the Julia REPL, activate the Julia environment for your project.
     - **Enter Package Manager Mode**: Press the `]` key to switch from the Julia prompt`julia>` to `(@v1.x) pkg>`.
        ```julia
        julia> ]  # Press the `]` key to switch to the package manager mode
        ```
      - **Activate the Environment**: Once in the package manager mode, you need to activate the environment specific to COBRArrowOptimization project. This is done with the command `activate .`, where the `.` refers to the current directory. This command tells Julia to use the `Project.toml` in the current directory to set up the environment for this project.

        ```julia
        (@v1.x) pkg> activate .  # Type this command and press Enter
        ```

    - **Return to Julia REPL**: Press the Backspace key or Ctrl+C to exit the package manager mode and return to the Julia REPL prompt.

      ```julia
      (@v1.x) pkg>  # After running `activate .`, return to the Julia prompt with Backspace
      ```

3. **Set Up CPLEX and Environment Variables**:
   - **Download and Install CPLEX**: Obtain and install CPLEX from the [IBM website](https://www.ibm.com/products/ilog-cplex-optimization-studio).
   - **Set the CPLEX Environment Variable**: In the Julia REPL, set the `CPLEX_STUDIO_BINARIES` environment variable to point to the CPLEX installation directory:
     ```julia
     ENV["CPLEX_STUDIO_BINARIES"] = "path_to_CPLEX_runtime_binaries"
     ```
     For example:
     ```julia
     ENV["CPLEX_STUDIO_BINARIES"] = "/Applications/CPLEX_Studio_Community2211/cplex/bin/arm64_osx"  # Adjust to your installation path
     ```

4. **Install Dependencies**: Install the required dependencies specified in the `Project.toml` file.
    ```julia
    julia> ]  # Press the `]` key to switch to the package manager mode
     (@v1.x) pkg> instantiate  # Type this command and press Enter
    ```

#### 3.2 Start the Optimization Server

**Run the Optimization Server with the Specific Environment**:

In the `COBRArrowOptimization` directory, execute:
```sh
julia --project=. optimization_server.jl
```
Alternatively, if you’re running the script from a different directory, specify the full path to COBRArrowOptimization project:
```sh
julia --project=/path/to/the/project optimization_server.jl
```
For example:
```sh
julia --project=/Documents/gitlab/COBRArrow/server/COBRArrowOptimization optimization_server.jl
# Adjust the path accordingly
```

**Run the Optimization Server in the Background**:

- **On Unix-based systems (Linux and macOS)**:
  ```sh
  nohup julia --project=. optimization_server.jl &
  ```

- **On Windows**:
  Open Command Prompt and use:
  ```sh
  start /B julia --project=. optimization_server.jl
  ```
