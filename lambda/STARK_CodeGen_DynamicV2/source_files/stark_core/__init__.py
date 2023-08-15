import os
import stark_core.data_abstraction as data
import stark_core.security as sec
import stark_core.logging as log
from pymongo import MongoClient
region_name = "[[REGION_NAME]]"

test_region = 'eu-west-2'
page_limit  = 100
##Cosmos DB Configuration
client            = MongoClient("[[COSMOSDB_CONNECTION_STRING]]")
mdb_database      = client["[[STARK_MDB_TABLE_NAME]]"]

TTL_for_deleted_records_in_days = 120

##file storage related config
bucket_name = "[[STARK_WEB_BUCKET]]"
file_storage = "[[FILE_STORAGE_NAME]]"
file_storage_url  = "[[FILE_STORAGE_URL]]"
file_storage_tmp  = f"{file_storage_url}tmp/"
upload_dir  = f"uploaded_files/"

analytics_raw_bucket_name       = "[[STARK_RAW_BUCKET]]"
analytics_processed_bucket_name = "[[STARK_PROCESSED_BUCKET]]"
analytics_athena_bucket_name    = "[[STARK_ATHENA_BUCKET]]"

##Sequence config
separator = '-'