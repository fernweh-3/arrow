import pyarrow as pa
import pyarrow.flight as fl



# location = fl.Location('grpc+tls://localhost:50051')

location = fl.Location('grpc+tcp://cobrarrow.chatimd.org')        
client = fl.connect(location)


# List available flights
# a = client.list_flights()
# print(list(a))

descriptor = fl.FlightDescriptor.for_command("Recon3D_metReconMap");
b = client.get_flight_info(descriptor)
print(b)