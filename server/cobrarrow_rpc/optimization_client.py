import socket
import pyarrow as pa
from pyarrow import ipc

class OptimizationClient:
    """
    A client to connect to the optimization server and send optimization data.
    
    Note:
        The current optimization server is implemented in Julia.

    Attributes:
        optimization_host (str): Hostname of the optimization server.
        optimization_port (int): Port number of the optimization server.
    """

    def __init__(self, optimization_host='localhost', optimization_port=65432):
        """
        Initialize the OptimizationClient with server host and port.

        Args:
            julia_server_host (str): Hostname of the Julia server.
            julia_server_port (int): Port number of the Julia server.
        """
        self.optimization_host = optimization_host
        self.optimization_port = optimization_port

    def optimize(self, data_dict):
        """
        Optimize the provided model using the optimization server.

        Args:
            data_dict (dict): Dictionary containing data tables.

        Returns:
            list: List of result tables from the server.
        """
        filter_data = self.filter_data(data_dict)
        return self._get_result_from_julia(filter_data)

    @staticmethod
    def filter_data(data_dict):
        """
        Filter and prepare data for optimization.

        Args:
            data_dict (dict): Dictionary containing data tables.

        Returns:
            dict: Filtered and prepared data tables.
        """
        try:
            necessary_keys = {"solver", "S", "b", "c", "lb", "ub", "osense", "osenseStr","csense", "rxns", "mets"}
            optional_keys = {"C", "d", "dsense", "ctrs"}

            combined_data = {}

            # Add necessary fields
            for key in necessary_keys:
                if key in data_dict and isinstance(data_dict[key], pa.Table):
                    combined_data[key] = data_dict[key]

            # Add optional fields if they exist
            for key in optional_keys:
                if key in data_dict and isinstance(data_dict[key], pa.Table):
                    combined_data[key] = data_dict[key]

            # handle solver_name
            if "solver" in data_dict and isinstance(data_dict["solver"], pa.Table):
                solver_table = data_dict["solver"]
                # solver_name = solver_table.to_pandas().iloc[0, 0]
                # solver_params = solver_table.to_pandas().iloc[0, 1]
                metadata = {'name': 'solver', 'description': 'Solver used in Julia'}
                solver_table = solver_table.replace_schema_metadata(metadata)
                combined_data["solver"] = solver_table
            else:
                combined_data["solver"] = pa.table({"solver_name": [], "solver_params": []})

            return combined_data
        except Exception as e:
            print(f"Error in load_model_from_flight_rpc: {e}")

    def _get_result_from_julia(self, data):
        """
        Send data to the Julia server and receive the result.

        Args:
            data (dict): Filtered and prepared data tables.

        Returns:
            list: List of result tables from the server.

        Raises:
            RuntimeError: If there are any issues with sending/receiving data.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                client_socket.connect((self.optimization_host, self.optimization_port))
                self._send_tables(client_socket, data)
                return self._receive_result(client_socket)
        except Exception as e:
            print(f"Error in optimization: {e}")
            raise

    def _send_tables(self, client_socket, data):
        """
        Send the data tables to the Julia server.

        Args:
            client_socket (socket.socket): The socket connected to the server.
            data (dict): Filtered and prepared data tables.
        """
        for key, table in data.items():
            # print(f"\nSending table to Julia with key: {key}")
            # print(f"table schema : {table.schema}")
            serialized_table = self.serialize_table(table)

            table_length = len(serialized_table).to_bytes(4, byteorder='little')
            # print(f"sending data size is {len(serialized_table)}")
            client_socket.sendall(table_length)
            client_socket.sendall(serialized_table)
            # print(f"sent table to julia with key: {key}")

        # Send 'END' marker to indicate end of transmission
        client_socket.sendall((0).to_bytes(4, byteorder='little'))
        print("Sent 'END' marker to Julia")

    def _receive_result(self, client_socket):
        """
        Receive the result tables from the Julia server.

        Args:
            client_socket (socket.socket): The socket connected to the server.

        Returns:
            list: List of result tables from the server.
        
        Raises:
            RuntimeError: If the received result tables are not as expected.
        """
        result_tables = []
        while True:
            # Read the length of the result
            length_bytes = self.recvall(client_socket, 4)
            if not length_bytes:
                raise RuntimeError("Server Error.")

            length = int.from_bytes(length_bytes, byteorder='little')
            print(f"Expected result length: {length}")

            if length == 0:
                print("Received 'END' marker from server")
                break

            # Read the actual result
            serialized_result = self.recvall(client_socket, length)
            if len(serialized_result) != length:
                raise RuntimeError(
                    f"Expected to read {length} bytes but got {len(serialized_result)} bytes."
                )

            reader = ipc.RecordBatchStreamReader(pa.BufferReader(serialized_result))
            result_table = reader.read_all()
            result_tables.append(result_table)

        status_table = result_tables[0].to_pandas()
        print(f"Received status table: {status_table}")
        is_success = status_table.loc[0, 'success']
        if is_success:
            num_tables = status_table.loc[0, 'num_tables']
            if len(result_tables) != num_tables + 1:
                raise RuntimeError(
                    f"Expected to receive {num_tables} result tables but got "
                    f"{len(result_tables) - 1} tables."
                )
            return result_tables[1:]
        elif not is_success:
            reason = status_table.loc[0, 'error_message']
            raise RuntimeError(f"Optimization failed: {reason}")
        else:
            raise RuntimeError(f"Unexpected status: {is_success}")

    @staticmethod
    def serialize_table(table):
        """
        Serialize a table to bytes.

        Args:
            table (pa.Table): The table to serialize.

        Returns:
            bytes: The serialized table.
        """
        # Create a buffer output stream to hold serialized table
        with pa.BufferOutputStream() as table_sink:
            with ipc.RecordBatchStreamWriter(table_sink, table.schema) as writer:
                writer.write_table(table)
            return table_sink.getvalue()

    @staticmethod
    def recvall(sock, n):
        """
        Helper function to receive n bytes or return None if EOF is hit.

        Args:
            sock (socket.socket): The socket to receive data from.
            n (int): Number of bytes to receive.

        Returns:
            bytearray: The received data.
        """
        data = bytearray()
        while len(data) < n:
            packet = sock.recv(n - len(data))
            if not packet:
                return None
            data.extend(packet)
        return data
