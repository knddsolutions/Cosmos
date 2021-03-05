import requests
import time
import json
from credentials import credentials, getAuthHeaders

headers = getAuthHeaders()

pendingCenters = requests.get(f"{credentials.dns}/api/v1/center/pending", headers=headers)

print(pendingCenters.text)
# Cancel registration
#for entry in json.loads(pendingCenters.text)['Results']:
#    out = requests.delete(f"{credentials.dns}/api/v1/center/pending/{entry['Moid']}", headers=headers)
#    import pdb; pdb.set_trace()

# Confirm registration
#for entry in json.loads(out.text)['Results']:
#    out = requests.post(f"{credentials.dns}/api/v1/center/pending/{entry['Moid']}", headers=headers, data=json.dumps({"Path": "/test/test.jpg"}))
#    import pdb; pdb.set_trace()

