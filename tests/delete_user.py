import json
import requests
from credentials import credentials, getAuthHeaders

headers = getAuthHeaders()

out = requests.get(f"{credentials.dns}/api/v1/center/users", headers=headers)

for user in json.loads(out.text)['Results']:
    out = requests.delete(f"{credentials.dns}/api/v1/center/users/{user['Moid']}", headers=headers)
    print(out)

