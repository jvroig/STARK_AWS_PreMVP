#STARK Code Generator component.
#Produces the customized dynamic content for an Azure STARK system 

#Python Standard Library
import base64
import textwrap

#Private modules
import convert_friendly_to_system as converter

def create(data):

    source_code = f"""\
    #Python Standard Library

    #Extra modules
    from pymongo import MongoClient
    import azure.functions as func
    import json

    #STARK
    import stark_core

    #######
    #CONFIG
    # ddb_table = stark_core.ddb_table

    def main(req: func.HttpRequest) -> func.HttpResponse:
        # Set up the MongoDB client using the primary connection string

        isAuthorized = False
        username     = ''

        cookies = req.headers.get('Cookie', '').split(';')
        cookies = [c.strip() for c in cookies if c.startswith('sessid=')]
        sess_id = cookies[0][len('sessid='):] if cookies else None

        if sess_id != '':
            #Get session record from DDB
            sess_record = get_session(sess_id)

            if sess_record != {{}}:
                #Get username from record 
                username = sess_record['Username']

                #FIXME: Optional/Future - immediately check permissions here and decide if API endpoint requested is authorized

        #Set authorized if everything is ok 
        if username != '':
            isAuthorized=True

        response = {{
            "isAuthorized": isAuthorized,
            "context": {{
                "Username": username,
            }} 
        }}

        # Return a response
        return func.HttpResponse(
            json.dumps(response),
            status_code = 200
        ) 

    def get_session(sess_id):

        # Select the database and collection you want to fetch data from

        collection = stark_core.mdb_database["STARK_User_Sessions"]

        query_filter_obj = {{
                    "_id": sess_id
                    }}

        item = {{}}
        documents = list(collection.find(query_filter_obj))
        for record in documents:
            item = {{
                'pk': record['_id'],
                'Username': record['Username']
            }}

        return item
    """

    return textwrap.dedent(source_code)
