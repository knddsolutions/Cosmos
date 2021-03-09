import json
from flask import request
from flask_restplus import Resource
from jupiter.vamongo import VaMongo
from jupiter.vaapi import VaApi
from jupiter.vaschema import VaSchema
from jupiter.valogger import VaLogger
from jupiter.vautil import SendEmail
from sirius.config.constants import DB_NAME, APP_NAME, \
                                    SCHEMA_FILE, \
                                    LOG_PATH, DEV_USER, \
                                    CENTER_APPROVED_TEMPLATE, \
                                    CENTER_DECLINED_TEMPLATE, \
                                    LOGO_URL, BANNERS_URL, \
                                    Collections

SCHEMA = VaSchema.loadYamlFile(SCHEMA_FILE)
logger = VaLogger(APP_NAME, LOG_PATH)
mongoClient = VaMongo(DB_NAME, logger)
apiClient = VaApi(mongoClient, logger)

class PendingCenterRegistration(Resource):
    def __init__(self, resource):
        self.schema = SCHEMA['externalApis']['centerPending']
        self.xHeaders = json.loads(request.headers.get("x-auth"))
        self.collection = Collections.pending

    def get(self, moid=None):
        return apiClient.processRequest(self.xHeaders, request, self.collection,
                                        self.schema, moid)

    def delete(self, moid=None):
        # TODO Add reason field?
        # Will remove the pending request
        if not moid:
            return apiClient.badRequest(self.xHeaders, "Pending center moid required")

        pendingCenter = mongoClient.getDocument(self.collection, {"Moid": moid})
        if not pendingCenter['Results']:
            return apiClient.notFound(self.xHeaders, "Pending regitration could not be found")

        res = apiClient.processRequest(self.xHeaders, request, self.collection,
                                       self.schema, moid)

        if res.status_code != 200:
            return res

        # Reason for checking 200 first is so we can send an email after deletion is confirmed
        #Send decline email to center registrant
        with open(CENTER_DECLINED_TEMPLATE, 'r') as stream:
            emailBodyTemplate = stream.read()
        emailBody = emailBodyTemplate.format(logo_location=LOGO_URL, user_email=pendingCenter['Results'][0]['Email'])
        SendEmail(pendingCenter['Results'][0]['Email'].lower(), "An error occured...", emailBody)

        return res

    def post(self, moid=None):
        # For posts we will move the pending document to centers

        if not moid:
            return apiClient.badRequest(self.xHeaders, "Pending center moid required")

        pendingCenter = mongoClient.getDocument(self.collection, {"Moid": moid})

        if not pendingCenter['Results']:
            return apiClient.notFound(self.xHeaders, "Pending regitration could not be found")

        #Verify body with schema
        valid, body = apiClient.verifyData(request, self.schema)
        if not valid:
            return apiClient.badRequest(self.xHeaders, body)

        postData = pendingCenter['Results'][0]

        #Insert pending center into active centers collection
        res, registrationMoid =  mongoClient.createDocument(Collections.centers, postData)
        if not res:
            logger.error("Failed to insert {} into centers collection".format(postData))
            return apiClient.internalServerError(self.xHeaders)

        #Delete old pending center data
        if mongoClient.deleteDocument(self.collection, {"Moid": moid}) != 200:
            logger.error("Failed to delete pending data for {}".format(moid))
            return apiClient.internalServerError(self.xHeaders)

        #Send approval email to center registrant
        with open(CENTER_APPROVED_TEMPLATE, 'r') as stream:
            emailBodyTemplate = stream.read()
        emailBody = emailBodyTemplate.format(logo_location=LOGO_URL, user_email=postData['Email'])
        SendEmail(postData['Email'].lower(), "You're Approved!", emailBody)

        return apiClient.success(self.xHeaders)

