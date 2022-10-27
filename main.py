from fastapi import FastAPI
app = FastAPI()

import uuid
import pymongo
import json
import os
from fastapi.responses import JSONResponse
from datetime import datetime

from tools import Encryptor
encryptor = Encryptor()

mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
mydb = mongo_client["Teams_meetings"]
mycol1 = mydb["meeting_info"]
mycol2 = mydb["meeting_conversation"]


@app.post("/api/add_meeting")
def add_meeting(text,host_name=None,meeting_date_time=None):
    result = {
        
        "created_At": str(datetime.now()),
        "meeting_date_time":meeting_date_time,
        "host_name":host_name,
        "meeting_name": text,
        "meeting_souurce":"Teams app"
    }
    id_value = uuid.uuid4()
    result["meeting_id"] = str(id_value)
    
    
    #inserting encrypted data into mongoDB
    if result:
        mycol1.insert_one(result)
    else:
        return {"message":"unexpected...!"}
    
    #resolving ObjectId() conflict for mongoDB-JSON response
    result["_id"] = str(result["_id"])
    return JSONResponse(result)
    



@app.post('/api/add_conversation')
def add_conversation(meeting_id, meeting_transcribed_text, meeting_translation_text=None,date_time=None):
    # import pdb;pdb.set_trace()
    meeting_info = list(mydb.get_collection("meeting_info").find({"meeting_id":meeting_id}))
    response = []
    for each in meeting_info:
        if each:
            response.append({
                        "meeting_id":each.get("meeting_id"),
                        "created_At": each.get("created_At"),
                        "meeting_date_time":each.get("meeting_date_time"),
                        "host_name":each.get("host_name"),
                        "meeting_name": each.get("meeting_name"),
                        "meeting_source": each.get("meeting_souurce")
                        })
    
    temp = {"meeting_transcribed_text": meeting_transcribed_text, "meeting_translation_text": meeting_translation_text }
    
    for each in response:
        each.update(temp)
    
    #encrypting data
    mykey=encryptor.key_create()
    
    path = "dec_keys.json"
    if os.path.isfile(path) == False:
        with open('dec_keys.json', 'w') as f:
            data = {}
            data["decryption_keys"] = [
                
                {
                
                "meeting_Id": meeting_id,
                "dec_key":mykey.decode()
                
                }
                
                ]

            f.write(json.dumps(data))
        
    else:
        with open("dec_keys.json", 'r+') as f:
            data = json.load(f)
            if data["decryption_keys"]:
                for each in data["decryption_keys"]:
                    if each:
                        if meeting_id in each.keys():
                            continue
                        else:
                            res = {"meeting_Id": meeting_id,"dec_key":mykey.decode()}
                            
                            data["decryption_keys"].append(res)
                            f.seek(0)

             
            json.dump(data, f)
        
    
    encryptor.key_write(mykey, 'mykey.key')    
    loaded_key=encryptor.key_load('mykey.key')
    encoded_meeting_transcribed_text = json.dumps(meeting_translation_text).encode('utf-8')
    encoded_meeting_translation_text = json.dumps(meeting_transcribed_text).encode('utf-8')
    encrypted_meeting_transcribed_text = encryptor.file_encrypt(loaded_key, encoded_meeting_transcribed_text)
    encrypted_meeting_translation_text = encryptor.file_encrypt(loaded_key, encoded_meeting_translation_text)

    
    #inserting encrypted data into mongoDB
    if response:
        encrypted_data = {"meeting_id":meeting_id,"date_time":date_time}
        encrypted_data["meeting_transcribed_text"] = encrypted_meeting_transcribed_text.decode()
        encrypted_data["meeting_translation_text"] = encrypted_meeting_translation_text.decode()
        mycol2.insert_one(encrypted_data)
    else:
        return {"message":"unexpected...!"}
    
    # import pdb;pdb.set_trace()
    #resolving ObjectId() conflict for mongoDB-JSON response
    for each in response:
        if each.get("_id"):
            each["_id"] = str(each["_id"])
        else:
            continue
    return JSONResponse(response)


@app.get("/api/get_meeting_conversation")
def get_meeting_conversation(meeting_id):
    meeting_info = mydb.get_collection("meeting_info").find({"meeting_id":meeting_id})
    conversations = mydb.get_collection("meeting_conversation").find({})
    
    response = []
    decrypt = {}
    # import pdb;pdb.set_trace()
    flag = False
    with open("dec_keys.json", 'r') as f:
        dec_keys = json.load(f)        
        for db_each in conversations:
            if db_each:
                for temp in db_each.items():
                    if "meeting_transcribed_text" in temp:
                        decrypt["meeting_transcribed_text"] = temp[1]
                    elif "meeting_translation_text" in temp:
                        decrypt["meeting_translation_text"] = temp[1]
                        
            for each in dec_keys["decryption_keys"]:
                # if value in each.values():
                flag = True
                dec_key = each.get("dec_key")             
                if each:
                    encoded_meeting_transcribed_text = bytes(decrypt["meeting_transcribed_text"], encoding='utf-8')
                    encoded_meeting_translation_text = bytes(decrypt["meeting_translation_text"], encoding='utf-8')
                    decrypted_meeting_transcribed_text = json.loads(encryptor.file_decrypt(dec_key, encoded_meeting_transcribed_text))
                    decrypted_meeting_translation_text = json.loads(encryptor.file_decrypt(dec_key, encoded_meeting_translation_text))
                    break
            else:
                continue
    
    
    for each in meeting_info:
        if each:
            response.append({
                        "meeting_id":each.get("meeting_id"),
                        "created_At": each.get("created_At"),
                        "meeting_date_time":each.get("meeting_date_time"),
                        "host_name":each.get("host_name"),
                        "meeting_name": each.get("meeting_name"),
                        "meeting_source": each.get("meeting_souurce")
                        })

    temp = {"meeting_transcribed_text": decrypted_meeting_transcribed_text, "meeting_translation_text": decrypted_meeting_translation_text}

    for each in response:
        each.update(temp)
        
    if flag == False:
        response = {"message":"There is no meeting with the given meeting Id."}
    return response



@app.delete("/api/delete_meeting")
def delete_meeting(meeting_id):
    meeting_info = list(mydb.get_collection("meeting_info").find({"meeting_id":meeting_id}))
    flag = False
    for each in meeting_info:
        if each:
            mycol1.delete_one(each)
            flag = True
    if flag == False:
        return {"message":"No document present with meeting id: "+meeting_id}        
    return {"message":"document with meeting id "+meeting_id+" deleted sucessfully"}
