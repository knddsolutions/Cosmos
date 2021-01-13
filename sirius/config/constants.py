'''
    Constants file for sirius
'''
import os

DB_NAME = "Global-Sirius"
APP_NAME = "sirius"

if os.getenv("ONPREM") == "true":
    PORT=8082
    SCHEMA_FILE = "/Users/kylecermak/Desktop/cosmos/sirius/config/schema.yaml"
    APP_DNS = f"localhost:{PORT}"
    LOG_PATH = f"./{APP_NAME}.log"
else:
    PORT=80
    SCHEMA_FILE = "/cosmos/sirius/config/schema.yaml"
    APP_DNS = f"{APP_NAME}.default.svc.cluster.local"
    LOG_PATH = f"/var/log/{APP_NAME}.log"

COLLECTION = {"users": "iamUsers",
              "password": "iamUserPasswords",
              "pending": "iamPendingUsers",
              "auth": "iamAuthTokens",
              "centers": "iamCenter",
              "bpaa": "bpaaNumber",
              "points": "userPoints"}

ROOT_USERS = ["cnelson7265@gmail.com"]
DEV_USER = ["k.development@knddsolutions.com"]

CRON_SLEEP_SECONDS = 86400

CONFIRM_CENTER_TEMPLATE = "/cosmos/sirius/config/confirmCenterTemplate.txt"
SUCCESS_PAGE_TEMPLATE = "/cosmos/sirius/config/successTemplate.txt"
CENTER_REQUEST_TEMPLATE = "/cosmos/sirius/config/centerRequestTemplate.txt"
CENTER_APPROVED_TEMPLATE = "/cosmos/sirius/config/centerApprovedTemplate.txt"



