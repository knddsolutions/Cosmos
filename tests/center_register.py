import json
import requests

data = {"Center": "Test Center", "Email": "cnelson7265@gmail.com", "Platform": "BowlingCenter", "MemberID": "12345"}
data2 = {"Center": "Test Center1", "Email": "cnelson7265+1@gmail.com", "Platform": "BowlingCenter", "MemberID": "23456"}
data3 = {"Center": "Test Center2", "Email": "cnelson7265+2@gmail.com", "Platform": "BowlingCenter", "MemberID": "34567"}

url = 'https://openbowlservice.com/api/v1/center/registration'

out = requests.post(url, data=json.dumps(data))
out = requests.post(url, data=json.dumps(data2))
out = requests.post(url, data=json.dumps(data3))

