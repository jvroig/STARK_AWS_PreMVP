#STARK Code Generator component.
#Produces the customized dynamic content for a STARK system

#Python Standard Library
import base64
import textwrap

#Private modules
import convert_friendly_to_system as converter

def create(data):
  
    ddb_table_name = data["DynamoDB Name"]

    source_code = f"""\
    import logging
    import base64
    import datetime
    import json
    import secrets

    import azure.functions as func

    import stark_core

    from pymongo import MongoClient
    from shared_code import stark_scrypt as scrypt

    def main(req: func.HttpRequest) -> func.HttpResponse:

        logging.info(req)
        bytes_request = req.get_body()
        decoded_request = bytes_request.decode()
        request = json.loads(decoded_request)

        eventCookies = request.get('cookies', {{}})
        cookies = {{}}
        for cookie in eventCookies:
            info = cookie.partition("=")
            cookies[info[0]] = info[2]
        
        data    = {{}}
        headers = {{
            "Content-Type": "application/json"
        }}
        response = {{}}
        payload = request.get('Login', "")
        if payload == "":
            func.HttpResponse(
                "Client payload missing",
                status_code = 400,
                headers= headers
            )
        else:
            data['username'] = payload.get('username','')
            data['password'] = payload.get('password','')

        

        if req.method == "POST":
            sess_id = validate(data)

            if sess_id == False:
                #Auth failure
                response = {{"message": "AuthFailure"}}
            else:
                headers['Set-Cookie'] = f"sessid={{sess_id}}; Path=/; HttpOnly; Secure; SameSite=None; Max-Age=43200"
                
                response = {{"message": "AuthSuccess"}}
                #This should also be where bearer token is sent back when bearer token support is implemented

        else:
            return func.HttpResponse(
                "Could not handle API request",
                status_code = 400,
                headers= headers
            )

        return func.HttpResponse(
            json.dumps(response),
            status_code = 200,
            headers =  headers
        )


    def validate(data):
        username = data['username']
        password = data['password']
        failure  = True
        #Our default password hashing algo is Bcrypt, so the steps here are:
        #   1. Get `PasswordHash` from `User` record for `username`
        #       `Password_Hash` already contains algo (just bcrypt), salt and work factor
        #   2. We verify that the submitted `password` is the original one by calling verify(`password`, `Password_Hash`)
        #       That verify() call will use the algo/salt/work factor info to hash `password`. 
        #       If the result is the same as `Password_Hash`, then we know it is the correct plaintext password.
        #   3. Otherwise, we will return a login failure message.
        #       This same failure message will also handle the case where the `username` submitted is not in our records.

        #1. Get password plain for testing
        
        collection = stark_core.mdb_database["STARK_User"]

        # Fetch all the documents from the collection
        query_filter_obj = {{
                    "_id": username
        }}
        documents = list(collection.find(query_filter_obj))
        response = ""
        # Print out each document
        if len(documents) > 0:
            failure       = False
            password_hash = documents[0]['Password_Hash']
            
        #2. Verify hash
        if failure == False:
            if scrypt.validate(password, password_hash):
                #This means the user exists, and the password was verified.

                #FIXME
                #Stuff to do
                #1. Generate session id token
                sess_id = secrets.token_urlsafe(16)
                #This should also be where bearer token is created when bearer token support is implemented

                #2. Create USER SESSION, with token in it
                dt_now             = datetime.datetime.now()
                ttl_datetime       = dt_now + datetime.timedelta(hours=12)
                ttl_timestamp      = int(ttl_datetime.timestamp()) #int cast to remove microseconds
                item               = {{}}
                item['_id']        = sess_id
                item['TTL']        = str(ttl_timestamp)
                item['Sess_Start'] = str(dt_now)
                item['Username']   = username
            
                collection = stark_core.mdb_database["STARK_User_Session"]
                collection.insert_one(item)
                #3. Return token (and session ID?) to client for cookie creating purposes
                return sess_id
            else:
                failure = True


        #3: If `failure` is True, whether due to non-existent user or wrong password, handle here
        if failure == True:
            return False
    """
    return textwrap.dedent(source_code)
