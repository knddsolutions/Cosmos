import json
import requests
from types import SimpleNamespace

USERNAME = "cnelson7265@gmail.com"
PASSWORD = "Nbv12345"
DNS = "https://openbowlservice.com"
credsDict = {"username": USERNAME, "password": PASSWORD, "dns": DNS}

credentials = SimpleNamespace(**credsDict)

def getAuthHeaders():
    data = {"Email": credentials.username, "Password": credentials.password}
    try:
        out = requests.post(f"{credentials.dns}/api/v1/iam/Login", data=json.dumps(data))
    except Exception as exc:
        print(f"Failed to login {exc}")
        exit(0)
    
    token = json.loads(out.text)['AuthToken']
    
    return {"X-Auth-Token": token}
    
