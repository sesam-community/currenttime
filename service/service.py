from flask import Flask, request, jsonify, Response
from sesamutils import VariablesConfig, sesam_logger 
import json
import requests
import os
import sys

app = Flask(__name__)
logger = sesam_logger("Steve the logger", app=app)

## Logic for running program in dev
try:
    with open("helpers.json", "r") as stream:
        logger.info("Using env vars defined in helpers.json")
        env_vars = json.load(stream)
        os.environ['current_url'] = env_vars['current_url']
        os.environ['current_user'] = env_vars['current_user']
        os.environ['current_password'] = env_vars['current_password']
except OSError as e:
    logger.info("Using env vars defined in SESAM")
##

required_env_vars = ['current_user', 'current_password', 'current_url']
optional_env_vars = ['test1', 'test2']

headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
}

## Helper functions
def stream_json(clean):
    first = True
    yield '['
    for i, row in enumerate(clean):
        if not first:
            yield ','
        else:
            first = False
        yield json.dumps(row)
    yield ']'


@app.route('/')
def index():
    output = {
        'service': 'CurrentTime up and running...',
        'remote_addr': request.remote_addr
    }
    return jsonify(output)


@app.route('/get/<path>', methods=['GET'])
def get_data(path):
    config = VariablesConfig(required_env_vars)
    if not config.validate():
        sys.exit(1)

    exceed_limit = True
    result_offset = 0

    if request.args.get('since') != None:
        logger.info('Requesting resource with since value.')
        result_offset = int(request.args.get('since'))

    def emit_rows(exceed_limit, result_offset, config):
        while exceed_limit is not None:
            try:
                logger.info("Requesting data...")             
                request_url = f"{config.current_url}/{path}?%24count=true&%24skip={result_offset}"
                data = requests.get(request_url, headers=headers, auth=(f"{config.current_user}", f"{config.current_password}"))
                
                if not data.ok:
                    logger.error(f"Unexpected response status code: {data.content}")
                    return f"Unexpected error : {data.content}", 500
                    raise

                else:
                    data_count = json.loads(data.content.decode('utf-8-sig'))["@odata.count"]
                    updated_value = result_offset+1
                    for entity in json.loads(data.content.decode('utf-8-sig'))["value"]:
                        entity['_updated'] = updated_value
                        yield json.dumps(entity)
                        updated_value += 1
                    
                    if exceed_limit != None:          
                        if exceed_limit != data_count:
                            exceed_limit = data_count
                            result_offset+=exceed_limit
                            logger.info(f"Result offset is now {result_offset}")
                            logger.info(f"extending result")
                    
                        if exceed_limit == data_count:
                            logger.info(f"Paging is complete.")
                            exceed_limit = None
            
            except Exception as e:
                logger.warning(f"Service not working correctly. Failing with error : {e}")

        logger.info("Returning objects...")
    
    try:
        return Response(emit_rows(exceed_limit, result_offset, config), status=200, mimetype='application/json')
    except Exception as e:
        logger.error("Error from Currenttime: %s", e)
        return Response(status=500)

@app.route('/chained/<path>/', defaults={'resource_path': None}, methods=['GET','POST'])
@app.route('/chained/<path>/<resource_path>', methods=['GET','POST'])
def chain_data(path, resource_path):
    config = VariablesConfig(required_env_vars)
    if not config.validate():
        sys.exit(1)

    request_data = request.get_data()
    json_data = json.loads(str(request_data.decode("utf-8")))

    def emit_rows(config, json_data):
        for element in json_data[0].get("payload"):
            resource = [*element.values()][0]
            if resource_path == None:
                request_url = f"{config.current_url}/{path}({resource})"
                data = requests.get(request_url, headers=headers, auth=(f"{config.current_user}", f"{config.current_password}"))
            else:
                request_url = f"{config.current_url}/{path}({resource})/{resource_path}"
                data = requests.get(request_url, headers=headers, auth=(f"{config.current_user}", f"{config.current_password}"))
            
            if not data.ok:
                logger.error(f"Unexpected response status code: {data.content}")
                return f"Unexpected error : {data.content}", 500
                raise

            else:
                yield json.dumps(data.json())
        
        logger.info("Returning objects...")

    try:
        return Response(emit_rows(config, json_data), status=200, mimetype='application/json')
    except Exception as e:
        logger.error("Error from Currenttime: %s", e)
        return Response(status=500)


@app.route('/post/<path>/', defaults={'resource_path': None}, methods=['GET','POST'])
@app.route('/post/<path>/<resource_path>', methods=['GET','POST'])
def post_data(path, resource_path):
    config = VariablesConfig(required_env_vars)
    if not config.validate():
        sys.exit(1)

    request_data = request.get_data()
    json_data = json.loads(str(request_data.decode("utf-8")))

    for element in json_data:
        try:
            resource_id = element["id"]
        except:
            resource_id = None
        
        if resource_path == None and resource_id == None:
            request_url = f"{config.current_url}/{path}"
            data = requests.post(request_url, headers=headers, auth=(f"{config.current_user}", f"{config.current_password}"), data=json.dumps(element))
            if not data.ok:
                logger.error(f"Unexpected response status code: {data.content}")
                return f"Unexpected error : {data.content}", 500
                raise

        if resource_path == None and resource_id != None:
            if element['deleted'] == True:
                request_url = f"{config.current_url}/{path}({resource_id})"
                data = requests.delete(request_url, headers=headers, auth=(f"{config.current_user}", f"{config.current_password}"))
                if not data.ok:
                    logger.error(f"Unexpected response status code: {data.content}")
                    return f"Unexpected error : {data.content}", 500
                    raise
            else:
                request_url = f"{config.current_url}/{path}({resource_id})"
                data = requests.put(request_url, headers=headers, auth=(f"{config.current_user}", f"{config.current_password}"), data=json.dumps(element))
                if not data.ok:
                    logger.error(f"Unexpected response status code: {data.content}")
                    return f"Unexpected error : {data.content}", 500
                    raise
        
        if resource_path != None and resource_id != None:
            request_url = f"{config.current_url}/{path}({resource_id})/{resource_path}"
            data = requests.put(request_url, headers=headers, auth=(f"{config.current_user}", f"{config.current_password}"), data=json.dumps(element))
            if not data.ok:
                logger.error(f"Unexpected response status code: {data.content}")
                return f"Unexpected error : {data.content}", 500
                raise

        else:
            logger.info("Nothing to do... Look at the README or in the code to modify the if clauses.")

    return jsonify({'Steve reporting': "work complete..."})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)