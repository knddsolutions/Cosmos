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

LOGO_URL = "https://kd-openbowl-service.s3-us-west-2.amazonaws.com/logo/OpenBowl_Logo.png"
BANNERS_URL = "https://kd-openbowl-service.s3-us-west-2.amazonaws.com/centers/banners/"
CENTERS_CSV = "https://kd-openbowl-service.s3-us-west-2.amazonaws.com/files/2019+Membership_short.csv"

ROOT_USERS = ["cnelson7265@gmail.com"]
DEV_USER = ["k.development@knddsolutions.com"]

CRON_SLEEP_SECONDS = 86400

CENTER_CONFIRMATION_TEMPLATE = "/cosmos/sirius/config/confirmCenterTemplate.txt"
SUCCESS_PAGE_TEMPLATE = "/cosmos/sirius/config/successTemplate.txt"
CENTER_REQUEST_TEMPLATE = "/cosmos/sirius/config/centerRequestTemplate.txt"
CENTER_APPROVED_TEMPLATE = "/cosmos/sirius/config/approvedTemplate.txt"
CENTER_DECLINED_TEMPLATE = "/cosmos/sirius/config/declineTemplate.txt"



