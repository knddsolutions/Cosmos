import requests
import time
import json
from credentials import credentials, getAuthHeaders

headers = getAuthHeaders()
out = requests.get(f"{credentials.dns}/api/v1/center/registration")

for center in json.loads(out.text)['Results']:
    headers['Center-Moid'] = center['Moid']
    out = requests.get(f"{credentials.dns}/api/v1/center/loyaltyPoints", headers=headers)
    print(out.text)

import pdb; pdb.set_trace()

