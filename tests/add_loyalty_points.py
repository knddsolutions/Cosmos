import requests
import time
import json
from credentials import credentials, getAuthHeaders

headers = getAuthHeaders()
out = requests.get(f"{credentials.dns}/api/v1/center/users?filter=Type eq 'Admin'", headers=headers)
centerMoid = json.loads(out.text)['Results'][0]['CenterMoid']
headers['Center-Moid'] = centerMoid
centerUsers = requests.get(f"{credentials.dns}/api/v1/center/users?filter=Type eq 'User'", headers=headers)

for user in json.loads(centerUsers.text)['Results']:
    pointsMoRes = requests.get(f"{credentials.dns}/api/v1/center/loyaltyPoints?filter=CenterUserMoid eq '{user['Moid']}'", headers=headers)
    pointsMo = json.loads(pointsMoRes.text)['Results'][0]
    data = {"Points": -10}
    res = requests.patch(f"{credentials.dns}/api/v1/center/loyaltyPoints/{pointsMo['Moid']}", headers=headers, data=json.dumps(data))
    print(res)

