module OptimizationServer
using Sockets
using Arrow
using COBRA
using SparseArrays
using DataFrames
# Include the CustomCOBRA module
script_path = @__FILE__
script_dir = dirname(script_path)
include(joinpath(script_dir, "CustomCOBRA.jl"))
using .CustomCOBRA

# Export the functions
export start_server

"""
    start_server(host::String, port::Int)

Starts the server and listens for client connections on the specified `host` and `port`.

# Arguments
- `host::String`: The IP address or hostname where the server will listen for connections.
- `port::Int`: The port number on which the server will listen.

# Example
```julia
start_server("127.0.0.1", 65432)
```
"""
function start_server(host::String, port::Int)
    server = listen(IPv4(host), port)
    println("Listening on $host:$port")

    while true
        client = accept(server)
        client_ip, client_port = getpeername(client)
        println("Accepted client connection from address: $client_ip: $client_port")
        @async handle_optimization_request(client)
    end
end

"""
    handle_optimization_request(client::TCPSocket)

Handles optimization requests from the given client. Processes the received data to form an LP problem,
runs optimization using COBRA.jl, and sends results back to the client.

# Arguments
- `client::TCPSocket`: The client socket connected to the server.
# Example
```julia
# Assuming optimization_client is a connected TCPSocket
handle_optimization_request(optimization_client)

```
"""
function handle_optimization_request(client)
    try
        while true
            data_dict = read_data_from_client(client)
            lpProblem = form_model(data_dict)
            solver = get_solver(data_dict)
            solverName = solver[:name]
            solverParams = solver[:parameters]
            @info "The solver in use is: $solverName with parameters: $solverParams"
            try
                # send success result to client
                status, objval, sol = perform_optimization_using_COBRA(lpProblem, solverName, solverParams)
                send_success_result(client, lpProblem, status, objval, sol)
            catch e
                # send error result to client
                send_failure_result(client, e)
            end
        end
    catch e
        send_failure_result(client, e)
        rethrow(e)
    finally
        close(client)
        println("Closed connection")
    end
end

"""
    read_data_from_client(client::TCPSocket) :: Dict{Symbol, Arrow.Table}

Reads and deserializes Arrow IPC data from the given client and returns it as a dictionary.

# Arguments
-   `client::TCPSocket`: The client socket from which to read data.
# Return
- `Dict{Symbol, Arrow.Table}`: A dictionary where keys are symbols representing table names and values are Arrow.Tables.
# Example
```julia
data_dict = read_data_from_client(client)
```
"""
function read_data_from_client(client)
    data_dict = Dict{Symbol,Arrow.Table}()
    while true
        header = read(client, UInt32)  # Read the fixed-length header
        data_length = Int(header)

        if data_length == 0
            println("Received 'END' marker, processing data...")
            break
        end

        data = read(client, data_length)

        # Deserialize Arrow IPC data
        buf = IOBuffer(data)
        table = Arrow.Table(buf)

        # Extract the key from the table's metadata
        metadata = Arrow.getmetadata(table)
        # println("Metadata: ", metadata)
        if haskey(metadata, "name")
            key = Symbol(metadata["name"])
            data_dict[key] = table
            # println("Deserialized Arrow IPC data with key: ", key)
            # println()
        else
            println("No 'name' metadata found, skipping table")
        end
    end
    println("Received all data from client")
    println()
    return data_dict
end

"""
    get_solver(data::Dict{Symbol, Any}) :: Dict{Symbol, Any}

Extracts the solver name and parameters from the provided data dictionary.

# Arguments
- `data::Dict{Symbol, Any}`: A dictionary containing solver information.
# Returns
- `Dict{Symbol, Any}`: A dictionary with keys :name (solver name as a string) and :parameters (solver parameters as a vector of tuples).
# Example
```julia
solver = get_solver(data_dict)
```
"""
function get_solver(data)
    solver = Dict{Symbol,Any}()
    # Extracts and processes the solver name.
    solver_name_data = data[:solver][:solver_name]
    solver_name = join(collect(skipmissing(solver_name_data)))

    # processes the solver parameters.
    solver_params_vector = []
    if haskey(data[:solver], :solver_params)
        solver_params = data[:solver][:solver_params]
        for param in solver_params
            if !ismissing(param)
                for (k, v) in pairs(param)
                    if !ismissing(v)
                        push!(solver_params_vector, (k, v))
                    end
                end
            end
        end
    end

    # A dictionary holding both the solver name and parameters.
    solver[:name] = solver_name
    solver[:parameters] = solver_params_vector
    return solver
end

"""
    form_model(data::Dict{Symbol, Arrow.Table}) :: COBRA.LPproblem

Forms an LP problem from the provided data dictionary and returns it as a COBRA.LPproblem.

# Arguments
- `data::Dict{Symbol, Arrow.Table}`: A dictionary containing data tables required to construct the LP problem.
# Returns
- `COBRA.LPproblem`: The constructed LP problem based on the provided data.
# Example
```julia
lpProblem = form_model(data)
```
"""
function form_model(data)
    # Extract and convert the data
    S_data = data[:S]
    metadata = Arrow.getmetadata(S_data)
    dimensions_str = metadata["dimensions"]
    dimensions = parse.(Int, split(strip(dimensions_str, ['[', ']']), ", "))
    println("Dimensions: ", dimensions)
    row = Vector{Int64}(S_data[:row])
    col = Vector{Int64}(S_data[:col])
    val = Vector{Float64}(S_data[:val])
    nrows = dimensions[1]
    ncols = dimensions[2]
    println("maximum_row: ", maximum(row), " maximum_col: ", maximum(col))
    println(" nrows: ", nrows, " ncols: ", ncols)
    S = sparse(row, col, val, nrows, ncols)

    b = Vector{Float64}(data[:b][:b])
    c = Vector{Float64}(data[:c][:c])
    lb = Vector{Float64}(data[:lb][:lb])
    ub = Vector{Float64}(data[:ub][:ub])

    # deal with osense or osenseStr
    if haskey(data, :osenseStr)
        osense_value = data[:osenseStr][:osenseStr][1]
        # Interpret the value of 'osenseStr' as an integer
        if osense_value == "min"
            osense = Int8(-1)
        elseif osense_value == "max"
            osense = Int8(1)
        end
    elseif haskey(data, :osense)
        osense = data[:osense][:osense][1]
    else
        error("Objective sense not found in the data.")
    end

    # Assuming data is already loaded and contains the csense field
    csense_data = data[:csense][:csense]
    # Combine the array of strings into a single string, ignoring any potential Missing values
    csense_string = join(collect(skipmissing(csense_data)))
    # Convert the single string to a character array
    csense = collect(csense_string)


    rxns = Vector{String}(data[:rxns][:rxns])
    mets = Vector{String}(data[:mets][:mets])

    if haskey(data, :d) && haskey(data, :C)
        @info "The model is a coupled model."
        C_data = data[:C]
        metadata = Arrow.getmetadata(C_data)
        dimensions_str = metadata["dimensions"]
        dimensions = parse.(Int, split(strip(dimensions_str, ['[', ']']), ", "))

        row = Vector{Int64}(C_data[:row])
        col = Vector{Int64}(C_data[:col])
        val = Vector{Float64}(C_data[:val])
        nrows = dimensions[1]
        ncols = dimensions[2]
        C = sparse(row, col, val, nrows, ncols)

        d = Vector{Float64}(data[:d][:d])
        ctrs = Vector{String}(data[:ctrs][:ctrs])

        dsense_data = data[:dsense][:dsense]
        dsense_string = join(collect(skipmissing(dsense_data)))
        dsense = collect(dsense_string)

        # append the C, d, dsense, and mets vectors for a coupled model
        S = [S; C]
        b = [b; d]
        csense = [csense; dsense]
        mets = [mets; ctrs]
    else
        @info "The model is an uncoupled model."
    end

    # Construct the LPproblem struct
    return COBRA.LPproblem(S, b, c, lb, ub, osense, csense, rxns, mets)
end


"""
    perform_optimization_using_COBRA(lpProblem::COBRA.LPproblem, solverName::String="GLPK", solverParams::Dict{Symbol, Any}=Dict())

Performs optimization on the given lpProblem using COBRA.jl and the specified solver and parameters.

# Arguments
- `lpProblem::COBRA.LPproblem`: The LP problem to be solved.
- `solverName::String="GLPK"`: The name of the solver to use (default is "GLPK").
- `solverParams::Dict{Symbol, Any}=Dict()`: Solver parameters.
# Returns
- `(status::MathOptInterface.TerminationStatusCode, objval::Float64, sol::Vector{Float64})`: The status of the optimization, the objective value, and the solution vector.
# Example
```julia
status, objval, sol = perform_optimization_using_COBRA(lpProblem, "GLPK", Dict())
```
"""
function perform_optimization_using_COBRA(lpProblem, solverName="GLPK", solverParams=Dict())
    # Perform optimization
    start_time = time()
    # Set the solver according to https://github.com/opencobra/COBRA.jl/blob/master/docs/src/configuration.md
    # pkgDir = joinpath(dirname(pathof(COBRA)), "..")
    # include(pkgDir * "/config/solverCfg.jl")
    solver = CustomCOBRA.changeCobraSolver(solverName, solverParams)
    status, objval, sol = CustomCOBRA.solveCobraLP(lpProblem, solver)
    end_time = time()
    @info "Time taken to solve the LP problem in COBRA.jl: $(end_time - start_time) seconds."
    return status, objval, sol

end


"""
    send_success_result(client::Sockets.Socket, lpProblem::COBRA.LPproblem, status::MathOptInterface.TerminationStatusCode, objval::Float64, sol::Vector{Float64})

Sends the results of an optimization problem back to the client upon successful completion. The function constructs and sends several data tables, including the main results, the status of the optimization, and the objective value.

# Arguments
- `client::Sockets.Socket`: The client socket to which the results will be sent.
- `lpProblem::COBRA.LPproblem`: The linear programming problem that was solved.
- `status::MathOptInterface.TerminationStatusCode`: The status of the optimization process.
- `objval::Float64`: The objective value obtained from the optimization.
- `sol::Vector{Float64}`: The solution vector obtained from the optimization.

# Example
```julia
# Assuming `client` is a valid Sockets.Socket, and `lpProblem`, `status`, `objval`, and `sol` are defined
send_success_result(client, lpProblem, status, objval, sol)
```
"""
function send_success_result(client, lpProblem, status, objval, sol)
    success_table = DataFrame(success=true, num_tables=2)

    # Convert status(MathOptInterface.TerminationStatusCode) to string
    status = string(status)

    main_result_df = DataFrame(rxns=lpProblem.rxns, flux=sol)
    status_result_df = DataFrame(status=status, objective_value=objval)

    # Send result back to client
    send_result(client, success_table)
    send_result(client, main_result_df)
    send_result(client, status_result_df)
    send_end_marker(client)
end

"""
    send_failure_result(client::Sockets.Socket, error::Exception)

Sends the results of a failed optimization attempt back to the client. The function constructs and sends a data table containing an error message indicating the failure of the optimization process.

# Arguments
- `client::Sockets.Socket`: The client socket to which the error result will be sent.
- `error::Exception`: The exception that was raised during the optimization process. This exception message will be included in the response to the client.

# Example
```julia
# Assuming `client` is a valid Sockets.Socket and `error` is an Exception object
send_failure_result(client, error)
```
"""
function send_failure_result(client, error)
    failure_table = DataFrame(success=false, error_message=string(error))
    # Send result back to client
    send_result(client, failure_table)
    send_end_marker(client)
end

"""
    send_result(client::Sockets.Socket, result_table::DataFrames.DataFrame)

Sends a result table to the client through the specified socket. The function serializes the `result_table` using Arrow IPC format, writes its length as a header, and then sends the serialized data.

# Arguments
- `client::Sockets.Socket`: The client socket through which the result will be sent.
- `result_table::DataFrames.DataFrame`: The result table that will be serialized and sent to the client. This table contains the data to be transmitted.

# Example
```julia
# Assuming `client` is a valid Sockets.Socket and `result_table` is a DataFrame
send_result(client, result_table)
```
"""
function send_result(client, result_table)
    result_io = IOBuffer()
    Arrow.write(result_io, result_table)
    result_data = take!(result_io)
    write(client, UInt32(length(result_data)))
    write(client, result_data)
end


"""
    send_end_marker(client::Sockets.Socket)

Sends an end marker to the client to indicate that no more data will follow. The end marker is a fixed-length header with a value of zero, which is used to signal the end of the data stream.

# Arguments
- `client::Sockets.Socket`: The client socket through which the end marker will be sent.

# Example
```julia
# Assuming `client` is a valid Sockets.Socket
send_end_marker(client)
```
"""
function send_end_marker(client)
    write(client, UInt32(0))  # Send a header with length 0 to indicate the end
end
end  # module




# Usage
using .OptimizationServer
# Start the server
host = "127.0.0.1"
port = 65432
start_server(host, port)