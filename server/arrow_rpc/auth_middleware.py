import base64
import secrets
import pyarrow as pa
import duckdb
from pyarrow.flight import FlightMethod

class BasicAuthServerMiddlewareFactory(pa.flight.ServerMiddlewareFactory):
    """
    Middleware that implements username-password authentication.

    Parameters
    ----------
    creds: Dict[str, str]
        A dictionary of username-password values to accept.
    """

    def __init__(self, db_path):
        self.db = db_path
        self.unauthenticated_endpoints = [
            FlightMethod.DO_GET,
            FlightMethod.GET_FLIGHT_INFO,
            FlightMethod.GET_SCHEMA,
            FlightMethod.LIST_ACTIONS,
            FlightMethod.LIST_FLIGHTS
        ]
        self.tokens = {}

    def start_call(self, info, headers):
        """
        Handle the start of a gRPC call, performing authentication if necessary.

        This method checks whether the requested method requires authentication.
        If so, it processes the provided credentials and validates the user.

        Args:
            info (pyarrow.flight.ServerCallInfo): Information about the call, 
                including the method being invoked.
            headers (dict): HTTP headers containing authentication information.

        Returns:
            BasicAuthServerMiddleware: Middleware instance for authenticated sessions.

        Raises:
            pa.flight.FlightUnauthenticatedError: If authentication fails or no 
                credentials are provided.
        """
        # print(info.method)
        # Skip auth for specific endpoints
        if info.method in self.unauthenticated_endpoints:
            return
        # Search for the authentication header (case-insensitive)
        auth_header = None
        for header in headers:
            if header.lower() == "authorization":
                auth_header = headers[header][0]
                break

        if not auth_header:
            raise pa.flight.FlightUnauthenticatedError("No credentials supplied")

        # The header has the structure "AuthType TokenValue", e.g.
        # "Basic <encoded username+password>" or "Bearer <random token>".
        auth_type, _, value = auth_header.partition(" ")

        if auth_type == "Basic":
            conn = duckdb.connect(self.db)
            # Initial "login". The user provided a username/password
            # combination encoded in the same way as HTTP Basic Auth.
            decoded = base64.b64decode(value).decode("utf-8")
            username, _, password = decoded.partition(':')
            hashed_password = base64.b64encode(password.encode())
            result = conn.execute(
                "SELECT * FROM users WHERE username=? AND "+ 
                "password=? and status = 'active'",(username, hashed_password)).fetchone() 
            if result:
                token = secrets.token_urlsafe(32)
                self.tokens[token] = username
                return BasicAuthServerMiddleware(token)
            else:
                raise pa.flight.FlightUnauthenticatedError("Unknown user or invalid password")
        elif auth_type == "Bearer":
            # An actual call. Validate the bearer token.
            username = self.tokens.get(value)
            if username is None:
                raise pa.flight.FlightUnauthenticatedError("Invalid token")
            return BasicAuthServerMiddleware(value)
        raise pa.flight.FlightUnauthenticatedError("No credentials supplied")


class BasicAuthServerMiddleware(pa.flight.ServerMiddleware):
    """Middleware that implements username-password authentication."""

    def __init__(self, token):
        self.token = token

    def sending_headers(self):
        """Return the authentication token to the client."""
        return {"authorization": f"Bearer {self.token}"}


class NoOpAuthHandler(pa.flight.ServerAuthHandler):
    """
    A handler that implements username-password authentication.

    This is required only so that the server will respond to the internal
    Handshake RPC call, which the client calls when authenticate_basic_token
    is called. Otherwise, it should be a no-op as the actual authentication is
    implemented in middleware.
    """

    def authenticate(self, outgoing, incoming):
        """
        This method is a no-op, meaning it does nothing when called.
        """
        pass

    def is_valid(self, token):
        """
        Always returns an empty string, indicating that token validation is effectively bypassed.
        """
        return ""
    