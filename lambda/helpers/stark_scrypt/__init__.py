#Scrypt password hashing and validation for STARK default use
import base64
import hashlib
import secrets

def create_hash(password, n=16, r=8, p=1, b64salt="", salt_len=16):
    cpu_cost = 2**n
    blk_size = r
    parallel = p
    dklen    = 32
    
    if b64salt == "":
        b64salt = secrets.token_urlsafe(salt_len).replace('=','')

    salt = b64salt.encode('utf-8')

    password = password.encode('utf-8)')
    raw_hash = hashlib.scrypt(password, salt=salt, n=cpu_cost, r=blk_size, p=parallel, dklen=dklen, maxmem=(cpu_cost * blk_size * parallel * 128 * 2) )
    b64hash  = base64.b64encode(raw_hash).decode('utf-8').replace("=","")

    #Pattern to follow (taken from Passlib / PHC format):
    #     $scrypt$ln=8,r=8,p=1$WKs1xljLudd6z9kbY0wpJQ$yCR4iDZYDKv+iEJj6yHY0lv/epnfB6f/w1EbXrsJOuQ
    #                65536$8$1$c+Ec8UtUKHU$67e45dcd585c11d75d82f4b5abbad167c3dee1f9033bab63db8365ea24c77c22
    #       Notes:
    #       - Main sections separated by $
    #       - Section 1: algo identifier ("scrypt")
    #       - Section 2: all three scrypt settings, separated by commas ("ln=8,r=8,p=1")
    #               - Note: ln (linear rounds) is cpu cost, but instead if the eventual value, it is the exponent of 2 (i.e., instead of writing cpu_cost=65536, you write ln=16 (65536 = 2^16), which is the Passlib default cost/ln)
    #       - Section 3: the salt, 16 bytes (Passlib default), in base64 ("WKs1xljLudd6z9kbY0wpJQ")
    #       - Section 4: password hash, in base64 (yCR4iDZYDKv+iEJj6yHY0lv/epnfB6f/w1EbXrsJOuQ")
    scrypt_hash = f"$scrypt$n={n},r={r},p={p}${b64salt}${b64hash}$"

    return scrypt_hash
    
def validate(password, existing_hash):
    #Get settings from `hash` - call our parse_hash function
    settings = parse_hash(existing_hash)

    if(settings == "INVALID HASH"):
        print ("Logging validation failure: User has invalid existing password hash in user records")
        return False

    n      = settings["n"]
    r      = settings["r"]
    p      = settings["p"]
    salt   = settings["salt"]
    
    new_hash = create_hash(password, n=n, r=r, p=p, b64salt=salt)

    if new_hash == existing_hash:
        return True
    else:
        return False

def parse_hash(hash):
    #Guard clauses
    if hash[0] != "$" or hash[-1] != "$": return "INVALID HASH"

    #First, remove leading and trailing "$" - no need for them
    hash = hash[1:-1]

    #Second, split into sections by "$", resulting in four sections as per PHC spec
    # - Section 1: algo identifier ("scrypt")
    # - Section 2: all three scrypt settings, separated by commas ("ln=8,r=8,p=1")
    # - Section 3: the salt, 16 bytes (Passlib default), in base64
    # - Section 4: password hash, in base64

    try: 
        section = hash.split("$")
        id      = section[0]
        config  = section[1]
        salt    = section[2]
        pwhash  = section[3] 
        params  = config.split(",")

        if id != "scrypt": return "INVALID HASH"

        settings = {
            "salt" : salt,
            "pwhash" : pwhash
        }    

        for param in params:
            key, value = param.split("=")
            settings[key] = int(value)

        if "n" not in settings: return "INVALID HASH"
        if "r" not in settings: return "INVALID HASH"
        if "p" not in settings: return "INVALID HASH"

        return settings

    except:
        return "INVALID HASH"

