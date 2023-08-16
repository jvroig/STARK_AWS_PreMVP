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
    #Python Standard Library
    import base64
    import datetime
    import json
    import logging


    import azure.functions as func
    #STARK
    import stark_core


    def main(req: func.HttpRequest) -> func.HttpResponse:

        bytes_request = req.get_body()
        decoded_request = bytes_request.decode()
        request = json.loads(decoded_request)
        response = ""
        #Get cookies, if any
        eventCookies = request.get('cookies', {{}})
        cookies = {{}}
        for cookie in eventCookies:
            info = cookie.partition("=")
            cookies[info[0]] = info[2]


        method  = req.method
        headers = {{
            "Content-Type": "application/json"
        }}

        if method == "POST":
            if cookies.get('sessid','') != '':
                response = logout(cookies['sessid'])
                print("Logged out")
                print(response)
                #Send cookie back, this time with past date, to ask client to delete it
                headers['Set-Cookie'] = f"sessid={{cookies['sessid']}}; Path=/; HttpOnly; Secure; SameSite=None; Max-Age=0"
                return func.HttpResponse(
                    "Logged out",
                    status_code = 200,
                    headers= headers
                )
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

    def logout(sess_id):
        #Delete session information
        collection_handler = stark_core.mdb_database["STARK_User_Session"]
        identifier_query = {{ "_id": sess_id }}
        response = collection_handler.delete_one(identifier_query)

        return response

    """

    return textwrap.dedent(source_code)
