#Python Standard Library
import json
import base64

#Extra modules
import azure.functions as func

import stark_core


#######
#CONFIG
collection_handler  = stark_core.mdb_database["STARK_User_Permissions"]

def main(req: func.HttpRequest) -> func.HttpResponse:

    responseStatusCode = 200

    bytes_request = req.get_body()
    decoded_request = bytes_request.decode()
    request = json.loads(decoded_request)

    request_type = req.params.get('rt','')
    if request_type == '':
        #Default request: Asking for user permissions check
        #event must contain an array of permissions in payload.get('stark_permissions', [])
        permissions = request.get('stark_permissions',[])

        stark_permissions = {}
        for permission in permissions:
            print(permission)
            stark_permissions[permission] = stark_core.sec.az_is_authorized(permission, req)

        return func.HttpResponse(
            json.dumps(stark_permissions),
            status_code = responseStatusCode,
            headers = {
                "Content-Type": "application/json",
            }
        )
    else:
        if request_type == 's3':
            #FIXME: Make sure only logged in and legitimate users can get here
            pass
            #Query for our creds
            # response = ddb.query(
            #     TableName=ddb_table,
            #     Select='ALL_ATTRIBUTES',
            #     KeyConditionExpression="pk = :pk",
            #     ExpressionAttributeValues={
            #         ':pk' : {'S' : "STARK|AccessKey|S3"}
            #     }
            # )

            # raw = response.get('Items')

            # items = []
            # for record in raw:
            #     item = {}
            #     item['access_key_id'] = record.get('sk',{}).get('S','')
            #     item['secret_access_key'] = record.get('key',{}).get('S','')
            #     items.append(item)

            # return {
            #     "isBase64Encoded": False,
            #     "statusCode": responseStatusCode,
            #     "body": json.dumps(items),
            #     "headers": {
            #         "Content-Type": "application/json",
            #     }
            # }

