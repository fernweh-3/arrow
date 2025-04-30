import duckdb
import json
import ast
import pyarrow as pa
from config import DATA_DB_PATH

class PersistService:
    """
    Service class for managing the persistence and loading of schema-based data.

    This class provides methods to save and load data associated with various schemas
    in a DuckDB database. It supports mapping MATLAB-like field names to database 
    columns and vice versa.
    """
    MAT_FIELD_DB_COLUMN_MAPPING_DICTS = {
            "model": {
                "osense": "objective",
                "osenseStr": "objective",
                "description": "description",
                "modelVersion": "version",
                "version": "version",
                "modelName": "name",
                "modelID": "model_id", # to avoid name conflict with ID
            },
            "species": {
                "mets": "id",
                "b": "coefficient",
                "csense": "flux_bound_operation",
                "metCharges": "charge",
                "metFormulas": "chemical_formula",
                "metSmiles": "smile",
                "metNames": "name",
                "metNotes": "note",
                "metHMDBID": "hmdb",
                "metInChIString": "inchi",
                "metKEGGID": "kegg",
                "metChEBIID": "chebi",
                "metCHEBIID": "chebi",
                "metPubChemID": "pubchem",
                "metMetaNetXID": "metanetx",
                "metSEEDID": "seed",
                "metBiGGID": "bigg",
                "metBioCycID": "biocyc",
                "metEnviPathID": "envipath",
                "metLIPIDMAPSID": "lipidmaps",
                "metReactomeID": "reactome",
                "metSABIORKID": "sabiork",
                "metSLMID": "slm",
                "metSBOTerms": "sbo",
                # "metPdMap": "pdmap",
                # "metReconMap": "reconmap",
            },
            "additional_constraints": {
                "ctrs": "id",
                "d": "coefficient",
                "ctrNames": "name",
                "dsense": "flux_bound_operation"
            },
            "reactions": {
                "rxns": "id",
                "lb": "lower_flux_bound",
                "ub": "upper_flux_bound",
                "c": "coefficient",
                "rxnConfidenceScores": "confidence_score",
                "rxnNames": "name",
                "rxnNotes": "description",
                "rxnECNumbers": "ec_number",
                "rxnReferences": "reference",
                "rxnKEGGID": "kegg",
                "rxnKEGGPathways": "kegg_pathway",
                # "rxnKeggOrthology": "kegg_orthology",
                "rxnMetaNetXID": "metanetx",
                "rxnBRENDAID": "brenda",
                "rxnBioCycID": "biocyc",
                "rxnReactomeID": "reactome",
                "rxnSABIORKID": "sabio",
                "rxnSEEDID": "seed",
                "rxnRheaID": "rhea",
                "rxnBiGGID": "bigg",
                "rxnSBOTerms": "sbo",
                # "rxnCOG": "cog",
                # "rxnReconMap":"reconmap",
                "subSystems": "subsystem",
                "rules": "rules",
                # "grRules": "grRules"
            },
            "additional_variables":{
                "evars": "id",
                "evarlb": "lower_flux_bound",
                "evarub": "upper_flux_bound",
                "evarc": "coefficient",
                "evarNames": "name",
            },
            "compartments":{
                "comps": "id",
                "compNames": "name"
            },
            "genes": {
                "genes": "id",
                "geneNames": "name",
                "geneEntrezID": "entrez",
                "geneRefSeqID": "refseq",
                "geneUniprotID": "uniprot",
                "geneEcoGeneID": "ecogene",
                "geneKEGGID": "kegg",
                "geneHPRDID": "hprd",
                "geneASAPID": "asap",
                "geneCCDSID": "ccds"
            },
            "proteins": {
                "proteins": "id",
                "proteinNames": "name",
                "geneNCBIProteinID": "ncbi",
            }
        }

    def __init__(self, database_path = DATA_DB_PATH):         
        self.conn = duckdb.connect(database_path)
        print("Connected to database")

    def persist(self, schema_name, data, to_overwrite = False):
        """
        Persists a schema and its associated data into the database.

        Args:
            schema_name (str): The name of the schema to persist.
            data (dict): The data to be persisted, structured as tables.
            to_overwrite (bool, optional): Whether to overwrite an existing schema. Defaults to False.

        Raises:
            RuntimeError: If the schema already exists and `to_overwrite` is False.
            Exception: If an error occurs during the persisting process.

        Description:
            This method checks if a schema already exists in the database. If it does and `to_overwrite` is not enabled, 
            a `RuntimeError` is raised. If overwriting is allowed or the schema doesn't exist, the method proceeds to 
            drop any existing schema with the same name, create a new schema, and then process and persist each table 
            in the `data`. Metadata from the tables is added as comments to the respective columns or tables in the 
            database.

        Example:
            self.persist('my_schema', data, to_overwrite=True)
        """
        try:
            # Start a new transaction
            self.conn.sql("BEGIN")

            if self._if_schema_exist(schema_name) and not to_overwrite:
                print(f"Schema {schema_name} already exists!!!")
                raise RuntimeError("Schema already exists")
            else:
                print(f"begin to persist schema {schema_name}")
                self.conn.sql(f"drop schema if exists {schema_name} cascade")
                self.conn.sql(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
                tables = self.process_tables(data)

                for key,table in tables.items():
                    # reference: https://duckdb.org/docs/guides/python/import_arrow
                    arrow_table = table
                    metadata = arrow_table.schema.metadata

                    self.conn.sql(
                        f'create table "{schema_name}"."{key}" as (select * from arrow_table)'
                    )
                    # if metadata has comment field, add comment to the column
                    if b'column_comments' in metadata:
                        comment_dict_bytes = metadata[b'column_comments']
                        comment_dict_str = comment_dict_bytes.decode('utf-8')
                        comment_dict = ast.literal_eval(comment_dict_str)

                        for col_name, col_comment in comment_dict.items():
                            # Convert the comment dictionary to a string and escape single quotes
                            col_comment_str = str(col_comment).replace("'", "''")
                            query = f'COMMENT ON COLUMN "{schema_name}"."{key}"."{col_name}" IS \'{col_comment_str}\''
                            self.conn.execute(query)
                    else:
                        # Decode byte strings to regular strings
                        decoded_dict = {key.decode('utf-8'): value.decode('utf-8') for key, value in metadata.items()}
                        dict_as_string = str(decoded_dict)
                        # Escape single quotes for SQL
                        escaped_dict_as_string = dict_as_string.replace("'", "''")

                        # Add metadata to the table
                        self.conn.execute(
                            f'COMMENT ON TABLE "{schema_name}"."{key}" IS \'{escaped_dict_as_string}\'')
                
                # Commit the transaction after successful execution
                self.conn.sql("COMMIT")
                print(f"Schema {schema_name} persisted successfully")
        except Exception as e:
            # Rollback the transaction in case of an error
            self.conn.sql("ROLLBACK")
            print(f"Failed to persist schema {schema_name}. Error: {str(e)}")
            raise e
        finally:
            # Ensure the connection is closed
            self.conn.close()

    def load(self, schema_name):
        """
        Load the schema from the database
        Args:
            schema_name (str): name of the schema to load
                
        Returns:
            dict: dictionary of tables in the schema
        """
        # Query to get the tables in the schema
        tables_query = f"""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = '{schema_name}'
        """

        table_name_records = self.conn.execute(tables_query).fetchall()
        # error handling here, if the schema does not exist or is empty, throw an error
        if len(table_name_records) == 0:
            raise RuntimeError("Schema does not exist or is empty")

        print(f"Loading schema {schema_name}")
        table_names = [record[0] for record in table_name_records]
        data = {}
        for table_name in table_names:
            # get table description
            metadata = self.conn.execute(f"""
                    SELECT table_comment
                    FROM information_schema.tables
                    WHERE table_name = '{table_name}'
                    AND table_schema = '{schema_name}'
                """).fetchone()
            table_comment = metadata[0]

            if table_comment:
                # load tables not defined in the mapping dictionary
                metadata = self.comment_to_dict(table_comment)
                mat_field_name = metadata["name"]
                query = f'select * from "{schema_name}"."{table_name}"'
                # concat schema name and mat_field_name as key for flight descriptor
                key = f"{schema_name}:{mat_field_name}"
                arrow_table = self.conn.execute(query).arrow()               
                comment_dict = self.comment_to_dict(table_comment)
                data[key] = self.add_metadata(comment_dict, arrow_table)
            else:
            # load tables defined in the mapping dictionary
                query = f"""
                        SELECT column_name, column_comment 
                        FROM information_schema.columns 
                        WHERE table_name = '{table_name}' 
                        AND table_schema = '{schema_name}';
                        """
                result = self.conn.execute(query).fetchall()

                # query as arrow table
                for column_name, column_comment in result:
                    comment_dict = self.comment_to_dict(column_comment)
                    mat_field_name = comment_dict["name"] 
                    key = f"{schema_name}:{mat_field_name}"
                    try:
                        # if column name is flux_bound_operation
                        if column_name == "flux_bound_operation":
                            column_data = self.conn.execute(
                                f'select flux_bound_operation from "{schema_name}"."{table_name}"').fetchdf()
                            # Join all values into a single string
                            operation_array = pa.array(
                                ["".join(column_data['flux_bound_operation'].tolist())]
                            )
                            arrow_table = pa.Table.from_pydict({mat_field_name: operation_array})
                        else:
                            # using double quotes to aviod SQL syntax error such as using reserved keywords
                            query = f'select "{column_name}" as "{mat_field_name}" from {schema_name}.{table_name}'
                            # mapping column name back to matlab field name
                            arrow_table = self.conn.execute(query).arrow()

                        data[key] = self.add_metadata(comment_dict, arrow_table)
                    except Exception as e:
                        print(f"Error in processing column {column_name} in table {table_name}")
                        print(e)
                        raise e
        self.conn.close()
        return data

    @staticmethod
    def comment_to_dict(comment):
        """
        Converts a comment string to a dictionary.

        Args:
            comment (str): The comment string to convert.

        Returns:
            dict: The dictionary representation of the comment.
        """
        # Replace single quotes with double quotes to form valid JSON
        comment = comment.replace("'", '"')
        return json.loads(comment)

    @staticmethod
    def add_metadata(comment_dict, arrow_table):
        """
        Adds metadata to an Apache Arrow table.

        Args:
            comment (dict): The metadata, expected to be a JSON string or a dictionary.
            arrow_table (pa.Table): The Apache Arrow table to which the metadata will be added.

        Returns:
            pa.Table: The Arrow table with the updated schema metadata.
        """
        metadata = {}
        for key, value in comment_dict.items():
            metadata[key.encode('utf-8')] = value.encode('utf-8')
        return arrow_table.replace_schema_metadata(metadata)

    def _if_schema_exist(self, schema_name):
        """
        Check if the schema exists in the database
        Args:
            schema_name (str): name of the schema
            
        Returns:
                bool: True if the schema exists, False otherwise
        """

        schema_query = f"""
        SELECT schema_name 
        FROM information_schema.schemata 
        WHERE schema_name = '{schema_name}'
        """
        schema_exists = self.conn.execute(schema_query).fetchall()
        return len(schema_exists) > 0

    @staticmethod
    def process_tables(tables):
        """
            Process tables to format them correctly
        
        Args: 
            tables (dict): dictionary of tables to process

        Returns:
            dict: dictionary of processed tables         
        """
        processed_tables = {}
        delete_keys = []
        for key, table in tables.items():
            # get the size of the table
            col_size = table.num_columns
            # get the name of the table
            table_name = table.schema.metadata[b'name'].decode('utf-8')

            if key in ('csense', 'dsense'):
                # Convert StringArray to character array and create a new table
                single_string = table[0].chunk(0).to_pylist()[0]
                char_array = pa.array(list(single_string))
                processed_table = pa.Table.from_pydict({key: char_array})
                processed_table = processed_table.replace_schema_metadata(table.schema.metadata)
                tables[key] = processed_table

            # process matrix tables
            if col_size > 1:
                processed_tables[table_name] = table
                delete_keys.append(key)

        # delete the processed tables  
        for key in delete_keys:
            del tables[key]

        # get a copy of MAT_FIELD_DB_COLUMN_MAPPING_DICTS
        dict = PersistService.MAT_FIELD_DB_COLUMN_MAPPING_DICTS.copy()
        size_tables = tables.copy()
        size_dict = {}
        new_entries = {}
        # get the size of the tables defined in the mapping dictionary
        for category, mapping_dict in PersistService.MAT_FIELD_DB_COLUMN_MAPPING_DICTS.items():
            for mat_field, db_column in mapping_dict.items():
                if mat_field in size_tables.keys():
                    size_dict[category] = size_tables[mat_field].num_rows
                    del size_tables[mat_field]

        # iterate through the size_tables dictionary to categorize the tables
        for key, table in size_tables.items():
            num_rows = table.num_rows
            found_match = False
            for category, size in size_dict.items():
                if num_rows == size:
                    # if the size of the table matches the size of the category
                    dict[category][key] = key
                    found_match = True
                    break
            # if the table size does not match any category, add it to the new_entries dictionary
            if not found_match:
                # Add new entries to the temporary dictionary
                new_entries[key] = num_rows
                dict[key] = {key: key}
            # Update the size dictionary after the iteration
            size_dict.update(new_entries)         

        # process tables with single column defined in the updated mapping dictionary
        for category, mapping_dict in dict.items():
            category_data = []
            category_columns = []
            category_comment_dict = {}
            for mat_field, db_column in mapping_dict.items():
                if mat_field in tables.keys():
                    table = tables[mat_field]
                    metadata = table.schema.metadata
                    comment = {}
                    for key in metadata.keys():
                        comment[key.decode('utf-8')] = metadata[key].decode('utf-8')
                    # Add data and column name to lists
                    data = tables[mat_field][0].chunk(0)
                    category_data.append(data)
                    category_columns.append(db_column)
                    category_comment_dict[db_column] = comment
                    delete_keys.append(mat_field)
            # Create a RecordBatch and then an Arrow Table
            category_batch = pa.RecordBatch.from_arrays(category_data, category_columns)
            if category_batch:
                category_table = pa.Table.from_batches([category_batch])
                # Convert the dictionary to a plain string format
                comment_str = str(category_comment_dict)
                # Replace schema metadata with the plain string (UTF-8 encoded)
                category_table = category_table.replace_schema_metadata({b'column_comments': comment_str.encode('utf-8')})
                processed_tables[category] = category_table
        return processed_tables

    @staticmethod
    def reverse_mapping(mapping_dict):
        """
        Reverse the mapping dictionary with the first occurrence of the value as the
        key and the key as the value

        Args:
            mapping_dict (_type_): _description_

        Returns:
            _type_: _description_
        """
        reversed_dict = {}
        for key, value in mapping_dict.items():
            if value not in reversed_dict:
                reversed_dict[value] = key
        return reversed_dict
