from cobrarrow_rpc.persist_service import PersistService  # Custom service for persisting data

import pyarrow as pa

# Create an instance of the PersistService class
persist_service = PersistService()

# modelID_table = pa.table({"modelID": pa.scalar('modelid'),})
# osense_table = pa.table({"osense": pa.scalar('max'),})

mets_table = pa.table({"mets": pa.array(["amets","bmets"]),})
metadata = {b'table_name': b'mets'}
mets_table = mets_table.replace_schema_metadata(metadata)

csense_table = pa.table({"csense": pa.array(["=>"]),})
metadata = {b'table_name': b'csense'}
csense_table = csense_table.replace_schema_metadata(metadata)

S_table = pa.table({"row": pa.array([1,2]),"col": pa.array([1,2]),"val": pa.array([1.11,2.22])})
metadata = {b'table_name': b'S'}
S_table = S_table.replace_schema_metadata(metadata)

data = { "S":S_table, "mets":mets_table, "csense":csense_table }

# persist_service.create_schema("test")
# persist_service.persist("test", data, True)

# a = persist_service.query("SELECT * FROM test.species")
# print(a)

b = persist_service.load("a")
print(b)
# persist_service.conn.sql("CREATE SCHEMA a")
# persist_service.if_schema_exist("a")
# # persist_service.conn.sql("create table a.mets as (select * from mets_table)")
# persist_service.conn.sql("insert into a.mets (select * from mets_table)")
# mets = persist_service.query("SELECT * FROM a.mets")
# print(mets)