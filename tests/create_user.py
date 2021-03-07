import json
import requests
from credentials import credentials, getAuthHeaders

headers = getAuthHeaders()

data = {"FirstName": "Christian", "LastName": "Nelson", "BirthDate": "07/26/1992"}

out = requests.get(f"{credentials.dns}/api/v1/center/registration")

for center in json.loads(out.text)['Results']:
    data['CenterMoid'] = center['Moid']
    out = requests.post(f"{credentials.dns}/api/v1/center/users", headers=headers, data=json.dumps(data))
    print(out)

