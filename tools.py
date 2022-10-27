from cryptography.fernet import Fernet

class Encryptor():
    
    def __init__(self):
        self.text = ""

    def key_create(self):
        key = Fernet.generate_key()
        return key

    def key_write(self, key, key_name):
        with open(key_name, 'wb') as mykey:
            mykey.write(key)

    def key_load(self, key_name):
        with open(key_name, 'rb') as mykey:
            key = mykey.read()
        return key


    def file_encrypt(self, key, original_data):
        
        f = Fernet(key)
        # self.text = text
        encrypted_data = f.encrypt(original_data)
        return encrypted_data

    def file_decrypt(self, key, encrypted_data):
        
        f = Fernet(key)

        decrypted_data = f.decrypt(encrypted_data)
        return decrypted_data