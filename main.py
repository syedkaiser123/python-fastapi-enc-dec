from fastapi import FastAPI, Request
app = FastAPI()

import uuid
import pymongo
import json
import os
from fastapi.responses import JSONResponse
from datetime import datetime
from models import AddMeeting, AddConversation

from tools import Encryptor
encryptor = Encryptor()

mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
mydb = mongo_client["Teams_meetings"]
mycol1 = mydb["meeting_info"]
mycol2 = mydb["meeting_conversation"]


@app.post("/api/add_meeting")
async def add_meeting(info: AddMeeting):     
    req_info = json.loads(info.json())
    result = {
        
        "created_At": str(datetime.now()),
        "meeting_date_time":req_info["meeting_date_time"],
        "host_name":req_info["host_name"],
        "meeting_name": req_info["meeting_name"],
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
async def add_conversation(info: AddConversation):
    req_info = json.loads(info.json())
    meeting_id = req_info["meeting_id"]
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
    
    temp = {"meeting_transcribed_text": req_info["meeting_transcribed_text"], "meeting_translation_text": req_info["meeting_translation_text"] }
    
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
                
                "meeting_Id": req_info["meeting_id"],
                "dec_key":mykey.decode()
                
                }
                
                ]

            f.write(json.dumps(data))
        
    else:
        with open("dec_keys.json", 'r+') as f:
            data = json.load(f)
            if data["decryption_keys"]:
                temp2 = []
                for each in data["decryption_keys"]:
                    if each:
                        temp2.append(each.get("meeting_Id"))

                if meeting_id not in temp2:                    
                    for each in data["decryption_keys"]:
                        if each:
                            res = {"meeting_Id": req_info["meeting_id"],"dec_key":mykey.decode()}
                            data["decryption_keys"].append(res)
                            f.seek(0)
                            break
                else:
                    return {"message":"The Conversation with meeting id: "+meeting_id+" is already present in the database"}

            json.dump(data, f)
        
    
    encryptor.key_write(mykey, 'mykey.key')    
    loaded_key=encryptor.key_load('mykey.key')
    encoded_meeting_transcribed_text = json.dumps(req_info["meeting_translation_text"]).encode('utf-8')
    encoded_meeting_translation_text = json.dumps(req_info["meeting_transcribed_text"]).encode('utf-8')
    encrypted_meeting_transcribed_text = encryptor.file_encrypt(loaded_key, encoded_meeting_transcribed_text)
    encrypted_meeting_translation_text = encryptor.file_encrypt(loaded_key, encoded_meeting_translation_text)

    
    #inserting encrypted data into mongoDB
    if response:
        encrypted_data = {"meeting_id":req_info["meeting_id"],"date_time":req_info["date_time"]}
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
    flag = False
    with open("dec_keys.json", 'r') as f:
        dec_keys = json.load(f)        
        for db_each in conversations:
            if db_each:
                for temp in db_each.items():
                    if "meeting_id" in temp and temp[1] == meeting_id:
                        decrypt["meeting_transcribed_text"] = db_each["meeting_transcribed_text"]
                        decrypt["meeting_translation_text"] = db_each["meeting_translation_text"]
                    else:
                        continue
                        
            for each in dec_keys["decryption_keys"]:
                # if value in each.values():
                flag = True
                dec_key = each.get("dec_key")
                dec_meeting_id = each.get("meeting_Id")
                if dec_meeting_id == meeting_id:
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
    meeting_conversation = list(mydb.get_collection("meeting_conversation").find({"meeting_id":meeting_id}))
    flag = False
    for each in meeting_info:
        if each:
            mycol1.delete_one(each)
            flag = True
    for each in meeting_conversation:
        if each:
            mycol2.delete_one(each)
            flag = True
    if flag == False:
        return {"message":"No document present with meeting id: "+meeting_id}        
    return {"message":"document with meeting id "+meeting_id+" deleted sucessfully"}