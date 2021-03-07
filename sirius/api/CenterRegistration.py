import json
from flask import Flask, request
from flask_restplus import Api, Resource
from datetime import datetime
from jupiter.vamongo import VaMongo
from jupiter.vaapi import VaApi, RegisterApis
from jupiter.vaschema import VaSchema
from jupiter.valogger import VaLogger
from jupiter.vautil import SendEmail
from sirius.config.constants import DB_NAME, APP_NAME, \
                                    SCHEMA_FILE, \
                                    LOG_PATH, DEV_USER, \
                                    CENTER_CONFIRMATION_TEMPLATE, \
                                    CENTER_APPROVED_TEMPLATE, \
                                    CENTER_DECLINED_TEMPLATE, \
                                    SUCCESS_PAGE_TEMPLATE, \
                                    CENTER_REQUEST_TEMPLATE, \
                                    LOGO_URL, \
                                    BANNERS_URL, \
                                    CENTERS_CSV, \
                                    Collections


SCHEMA = VaSchema.loadYamlFile(SCHEMA_FILE)
logger = VaLogger(APP_NAME, LOG_PATH)
mongoClient = VaMongo(DB_NAME, logger)
apiClient = VaApi(mongoClient, logger)

class CenterRegistration(Resource):
    def __init__(self, resoure):
        self.schema = SCHEMA['externalApis']['centerRegister']
        self.xHeaders = json.loads(request.headers.get("x-auth"))
        self.collection = Collecitons.centers

    def get(self, moid=None):
        return apiClient.processRequest(self.xHeaders, request, self.collection,
                                        self.schema, moid)
    def patch(self, moid=None):
        return apiClient.processRequest(self.xHeaders, request, self.collection,
                                        self.schema, moid)

    def post(self, moid=None):

        #Verify body with schema
        valid, body = apiClient.verifyData(request, self.schema)
        if not valid:
            return apiClient.badRequest(self.xHeaders, body)

        #Check if center is already registered
        center = mongoClient.getDocument(self.collection, {"MemberID": body['MemberID']})
        if center['Results']:
            logger.error("A center is already registered under BPAA number {body['MemberID']}")
            return apiClient.badRequest("This bowling center has already been registered")

        #Check if BPAA number is valid
        bpaa = mongoClient.getDocument(Collections.members, {"MemberID": body['MemberID']})

        #if bpaa != 200:
        #    logger.error(f"BPAA number {body['MemberID']} is not valid")
        #    return apiClient.badRequest(self.xHeaders, "Please enter a valid BPAA number")

        #Create timestamp
        ts = datetime.utcnow().isoformat()

        #Create temp data
        tempData = body
        tempData['Timestamp'] = ts

        #Store temp center data in pending collection
        res, docMoid = mongoClient.createDocument(Collections.pending, tempData)
        if res != 200:
            logger.error(f"Failed to create new temporary center registration for {tempData['MemberID']}")
            return apiClient.internalServerError(self.xHeaders)

        #Send confirmation email to center registrant
        with open(CENTER_REQUEST_TEMPLATE, 'r') as stream:
            emailBodyTemplate = stream.read()
        emailBody = emailBodyTemplate.format(logo_location=LOGO_URL, center_name=body['Center'], verify_url="test")
        SendEmail(body['Email'].lower(), "Confirmation", emailBody)

        #Send email to developer for verification
        with open(CENTER_CONFIRMATION_TEMPLATE, 'r') as stream:
            emailBodyTemplate = stream.read()
        emailBody = emailBodyTemplate.format(logo_location=LOGO_URL, center_name=body['Center'])
        SendEmail(DEV_USER, "New Center Request", emailBody) # TODO need to make pan able to handle lists

        return apiClient.success(self.xHeaders, "SUCCESS! Please check email for confirmation and further instrustions")

    def delete(self, moid=None):
        return apiClient.processRequest(self.xHeaders, request, self.collection,
                                        self.schema, moid)

