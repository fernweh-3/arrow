# Import necessary libraries
import argparse # For parsing command-line arguments
import ast # For safely evaluating expressions from strings
import threading # For creating and managing threads
import time # For handling time-related tasks
import pyarrow # Apache Arrow for in memory columnar data
import pyarrow.flight # Apache Arrow Flight for high-performance data transport
from optimization_client import OptimizationClient # Custom socket client for optimization tasks
from persist_service import PersistService # Custom service for persisting data
from auth_middleware import BasicAuthServerMiddlewareFactory # Custom authentication middleware
from auth_middleware import NoOpAuthHandler # Custom authentication handler
from config import USER_DB_PATH, HOST, PORT # Configuration settings

# Define a custom Flight server by extending FlightServerBase
class FlightServer(pyarrow.flight.FlightServerBase):
    """
    A FlightServer that handles gRPC requests for data optimization.

    Attributes:
        host (str): Hostname or IP address to listen on.
        flights (dict): Dictionary to store flight data.
        tls_certificates (list): TLS certificates.
    """
    def __init__(self, host="localhost", location=None,
                 tls_certificates=None, verify_client=False,
                 root_certificates=None, auth_handler=None,
                 middleware=None):
        """
        Initialize the FlightServer.

        Args:
            host (str): Hostname or IP address.
            location (str): gRPC server location.
            tls_certificates (list): TLS certificates.
            verify_client (bool): Whether to verify client certificates.
            root_certificates (bytes): Root certificates for client verification.
            auth_handler (pyarrow.flight.ServerAuthHandler): Authentication handler.
            middleware (dict): Middleware for handling requests.
        """
        super(FlightServer, self).__init__(
            location, auth_handler, tls_certificates, verify_client,
            root_certificates, middleware)
        self.flights = {} # Dictionary to store flight data
        self.host = host
        self.tls_certificates = tls_certificates

    @classmethod
    def descriptor_to_key(self, descriptor):
        """
        Convert a FlightDescriptor to a key for the flights dictionary.

        Args:
            descriptor (pyarrow.flight.FlightDescriptor): Flight descriptor.

        Returns:
            tuple: Key for the flights dictionary.
        """
        return (descriptor.descriptor_type.value, descriptor.command,
                tuple(descriptor.path or tuple()))

    def _make_flight_info(self, key, descriptor, table):
        """
        Create FlightInfo for the given table.

        Args:
            key (tuple): Key for the flights dictionary.
            descriptor (pyarrow.flight.FlightDescriptor): Flight descriptor.
            table (pyarrow.Table): Arrow table.

        Returns:
            pyarrow.flight.FlightInfo: Flight information.
        """
        if self.tls_certificates:
            location = pyarrow.flight.Location.for_grpc_tls(
                self.host, self.port)
        else:
            location = pyarrow.flight.Location.for_grpc_tcp(
                self.host, self.port)
        endpoints = [pyarrow.flight.FlightEndpoint(repr(key), [location]), ]

        mock_sink = pyarrow.MockOutputStream()
        stream_writer = pyarrow.RecordBatchStreamWriter(
            mock_sink, table.schema)
        stream_writer.write_table(table)
        stream_writer.close()
        data_size = mock_sink.size()

        return pyarrow.flight.FlightInfo(table.schema,
                                         descriptor, endpoints,
                                         table.num_rows, data_size)

    def list_flights(self, context, criteria):
        """
        List available flights.

        Args:
            context (pyarrow.flight.ServerCallContext): Call context.
            criteria (pyarrow.flight.Criteria): Criteria for filtering flights.

        Yields:
            pyarrow.flight.FlightInfo: Flight information for each available flight.
        """
        for key, table in self.flights.items():
            if key[1] is not None:
                descriptor = \
                    pyarrow.flight.FlightDescriptor.for_command(key[1])
            else:
                descriptor = pyarrow.flight.FlightDescriptor.for_path(*key[2])

            yield self._make_flight_info(key, descriptor, table)

    def get_flight_info(self, context, descriptor):
        """
        Get information about a specific flight.

        Args:
            context (pyarrow.flight.ServerCallContext): Call context.
            descriptor (pyarrow.flight.FlightDescriptor): Flight descriptor.

        Returns:
            pyarrow.flight.FlightInfo: Flight information.

        Raises:
            KeyError: If the flight is not found.
        """
        key = FlightServer.descriptor_to_key(descriptor)
        if key in self.flights:
            table = self.flights[key]
            return self._make_flight_info(key, descriptor, table)
        raise KeyError('Flight not found.')

    def do_put(self, context, descriptor, reader, writer):
        """
        Handle data upload (do_put) requests.

        Args:
            context (pyarrow.flight.ServerCallContext): Call context.
            descriptor (pyarrow.flight.FlightDescriptor): Flight descriptor.
            reader (pyarrow.flight.FlightStreamReader): Stream reader.
            writer (pyarrow.flight.FlightStreamWriter): Stream writer.
        """
        key = FlightServer.descriptor_to_key(descriptor)
        self.flights[key] = reader.read_all()

    def do_get(self, context, ticket):
        """
        Handle data download (do_get) requests.

        Args:
            context (pyarrow.flight.ServerCallContext): Call context.
            ticket (pyarrow.flight.Ticket): Ticket containing the key.

        Returns:
            pyarrow.flight.RecordBatchStream: Record batch stream.

        Raises:
            KeyError: If the flight is not found.
        """
        key = ast.literal_eval(ticket.ticket.decode())
        if key not in self.flights:
            return None
        return pyarrow.flight.RecordBatchStream(self.flights[key])

    def list_actions(self, context):
        """
        List available actions.

        Args:
            context (pyarrow.flight.ServerCallContext): Call context.

        Returns:
            list: List of available actions.
        """
        return [
            ("clear", "Clear the stored flights."),
            ("shutdown", "Shut down this server."),
            ("optimize", "Optimize the data for a given schema using a given solver."),
            ("persist", "Persist the data for a given schema to storage."),
            ("load", "Load and restore data for a given schema from storage.")
        ]

    def do_action(self, context, action):
        """
        Handle action requests.

        Args:
            context (pyarrow.flight.ServerCallContext): Call context.
            action (pyarrow.flight.Action): Action to perform.

        Yields:
            pyarrow.flight.Result: Result of the action.

        Raises:
            RuntimeError: If the action is unknown or fails.
        """
        if action.type == "clear":
            for key in list(self.flights.keys()):
                del self.flights[key]
            yield pyarrow.flight.Result(pyarrow.py_buffer(b'All flights cleared!'))
        elif action.type == "shutdown":
            yield pyarrow.flight.Result(pyarrow.py_buffer(b'Shutdown!'))
            # Shut down on background thread to avoid blocking current
            # request
            threading.Thread(target=self._shutdown).start()
        elif action.type == "optimize":
            yield from self._optimize(action)
        elif action.type == "persist":
            yield from self._persist(action)
        elif action.type == "load":
            yield from self._load(action)
        else:
            raise RuntimeError("Unknown action {!r}".format(action.type))

    def _optimize(self, action):
        """
        Optimize data based on the provided action.

        This method extracts relevant information from the action, gathers
        associated data, and invokes the optimization process.

        Args:
            action (pyarrow.flight.Action): The action object containing the 
                schema name, solver name, and solver parameters.

        Yields:
            pyarrow.flight.Result: The results of the optimization process, 
                serialized into Arrow format.

        Raises:
            RuntimeError: If the optimization fails or no data is found for 
                the provided schema name.
        """
        # Extract the schema name from the action body
        action_body_str = action.body.to_pybytes().decode()
        action_dict = ast.literal_eval(action_body_str)
        schema_name = action_dict["schema_name"]
        solver_name = action_dict["solver_name"]
        solver_params = action_dict["solver_params"] # in json format
        # Gather all data associated with the schema name
        data_dict = {}
        for key, table in self.flights.items():
            if key[1] and key[1].startswith(schema_name.encode()):
                field_name = key[1].split(b':', 1)[1].decode()
                data_dict[field_name] = table
        # if data_dict is empty, raise an error
        if not data_dict:
            error_message = f"No data found for schema {schema_name}".encode('utf-8')
            yield pyarrow.flight.Result(pyarrow.py_buffer(error_message))
            return
        # Convert the solver_name to an Arrow table and add it to the data_dict
        solver_table = pyarrow.table(
            {"solver_name": [solver_name],"solver_params": [solver_params]}
        )
        data_dict["solver"] = solver_table
        # Create a new OptimizationClient for each call
        optimization_client = OptimizationClient()
        try:
            result_tables = optimization_client.optimize(data_dict)
            # Return the results
            if result_tables and len(result_tables) == 2:
                main_result_table = result_tables[0]
                status_result_table = result_tables[1]

                # Serialize the main_result_table to bytes
                main_sink = pyarrow.BufferOutputStream()
                with pyarrow.ipc.new_stream(main_sink, main_result_table.schema) as writer:
                    writer.write_table(main_result_table)
                serialized_main_result = main_sink.getvalue().to_pybytes()
                yield pyarrow.flight.Result(serialized_main_result)

                # Serialize the status_result_table to bytes
                status_sink = pyarrow.BufferOutputStream()
                with pyarrow.ipc.new_stream(status_sink, status_result_table.schema) as writer:
                    writer.write_table(status_result_table)
                serialized_status_result = status_sink.getvalue().to_pybytes()
                yield pyarrow.flight.Result(serialized_status_result)
        except Exception as e:
            # raise RuntimeError(f"Optimization failed: {e}")
            error_message = f"Optimization failed: {str(e)}".encode('utf-8')
            yield pyarrow.flight.Result(pyarrow.py_buffer(error_message))
            return

    def _persist(self, action):
        """
        Persist data associated with a schema to storage.

        This method extracts the schema name and persistence options from the 
        provided action, gathers the relevant data, and attempts to persist it.

        Args:
            action (pyarrow.flight.Action): The action object containing the 
                schema name and persistence options (e.g., overwrite).

        Yields:
            pyarrow.flight.Result: A message indicating success or failure of 
                the persistence operation.

        Raises:
            RuntimeError: If the persistence operation fails or no data is found 
                for the specified schema.
        """
        # Extract the schema name from the action body
        action_body_str = action.body.to_pybytes().decode()
        action_dict = ast.literal_eval(action_body_str)
        schema_name = action_dict["schema_name"]
        to_overwrite = action_dict["to_overwrite"]=="true"

        # Gather all data associated with the schema name
        data_dict = {}
        for key, table in self.flights.items():
            if key[1] and key[1].startswith(schema_name.encode()):
                field_name = key[1].split(b':', 1)[1].decode()
                data_dict[field_name] = table

        # if data_dict is empty, raise an error
        if not data_dict:
            error_message = f"No data found for schema {schema_name}".encode('utf-8')
            yield pyarrow.flight.Result(pyarrow.py_buffer(error_message))
            return

        # Create a new PersistClient for each call
        persist_service = PersistService()
        try:
            persist_service.persist(schema_name, data_dict, to_overwrite)
            yield pyarrow.flight.Result(pyarrow.py_buffer(b'Data persisted successfully!'))
        except Exception as e:
            error_message = f'Data persistence failed: {str(e)}'.encode('utf-8')
            yield pyarrow.flight.Result(pyarrow.py_buffer(error_message))
            return

    def _load(self, action):
        """
        Load and restore data associated with a schema from persistent storage.

        This method extracts the schema name from the action, loads the corresponding
        data from storage, and uploads it back to the server.

        Args:
            action (pyarrow.flight.Action): The action object containing the schema name.

        Yields:
            pyarrow.flight.Result: A message indicating the success or failure of the 
                loading operation.

        Raises:
            RuntimeError: If the data loading process fails.
        """
        # Extract the schema name from the action body
        action_body_str = action.body.to_pybytes().decode()
        action_dict = ast.literal_eval(action_body_str)
        schema_name = action_dict["schema_name"]
        # Create a new PersistClient for each call
        persist_service = PersistService()
        try:
            data_dict = persist_service.load(schema_name)
            if data_dict:
                for key, table in data_dict.items():
                    # upload the data to the server
                    descriptor = pyarrow.flight.FlightDescriptor.for_command(key)
                    flight_key = FlightServer.descriptor_to_key(descriptor)
                    self.flights[flight_key] = table
                print(f"Data loaded successfully for schema {schema_name}")
            else:
                error_message = f"No data found for schema {schema_name}".encode('utf-8')
                yield pyarrow.flight.Result(pyarrow.py_buffer(error_message))
        except Exception as e:
            error_message = f'Data loading failed: {str(e)}'.encode('utf-8')
            yield pyarrow.flight.Result(pyarrow.py_buffer(error_message))

    def _shutdown(self):
        """Shut down after a delay."""
        print("Server is shutting down...")
        time.sleep(2)
        self.shutdown()

def main():
    """
    Initialize and start the FlightServer.

    This function sets up the server's scheme, host, and port, initializes 
    the FlightServer with the necessary authentication handler and middleware, 
    and then starts the server.

    The server listens on port 443 for incoming gRPC connections.

    Prints:
        The location where the server is serving.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default=HOST,
                        help="Address or hostname to listen on")
    parser.add_argument("--port", type=int, default=PORT,
                        help="Port number to listen on")
    parser.add_argument("--userdb", type=str, default= USER_DB_PATH,
                        help="Path to the user database file")

    args = parser.parse_args()

    scheme = "grpc+tcp"

    location = "{}://{}:{}".format(scheme, args.host, args.port)

    server = FlightServer(args.host, location,
                        auth_handler=NoOpAuthHandler(),
                         middleware={"basic": BasicAuthServerMiddlewareFactory(args.userdb)}
    )
    print("Using user database:", args.userdb)
    print("Serving on", location)
    server.serve()

if __name__ == '__main__':
    main()
