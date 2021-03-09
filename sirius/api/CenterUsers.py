import json
from flask import request
from flask_restplus import Resource
from datetime import datetime
from jupiter.vamongo import VaMongo
from jupiter.vaapi import VaApi
from jupiter.vaschema import VaSchema
from jupiter.valogger import VaLogger
from jupiter.vautil import SendEmail
from sirius.config.constants import DB_NAME, APP_NAME, \
                                    SCHEMA_FILE, \
                                    LOG_PATH, \
                                    Collections

SCHEMA = VaSchema.loadYamlFile(SCHEMA_FILE)
logger = VaLogger(APP_NAME, LOG_PATH)
mongoClient = VaMongo(DB_NAME, logger)
apiClient = VaApi(mongoClient, logger)

class CenterUsers(Resource):
    def __init__(self, resource):
        self.schema = SCHEMA['externalApis']['centerUsers']
        self.xHeaders = json.loads(request.headers.get("x-auth"))
        self.collection = Collections.users
        self.iamUser = self.xHeaders['IamUser']
        if "Center-Moid" in self.xHeaders:
            self.centerMoid = self.xHeaders['Center-Moid']
        else:
            self.centerMoid = None

    def get(self, moid=None):
        if self.iamUser['Type'] == "Admin":
            # Allow any query
            return apiClient.processRequest(self.xHeaders, request, self.collection,
                                            self.schema, moid)

        logger.info(f"Headers: {self.xHeaders}")
        if not self.centerMoid:
            overrideFilters = [("IamUserMoid", "$eq", self.iamUser['Moid'])]
            return apiClient.processRequest(self.xHeaders, request, self.collection,
                                            self.schema, moid, overrideFilters)

        # Check for user in db
        centerUser = mongoClient.getDocument(self.collection, {"IamUserMoid": self.iamUser['Moid'], "CenterMoid": self.centerMoid})
        if not centerUser['Results']:
            return apiClient.forbidden(self.xHeaders)

        if centerUser['Results'][0]['Type'] == "Admin":
            overrideFilters = [("CenterMoid", "$eq", self.centerMoid)]
            # In this case we force a search result for CenterMoid equal to the center in context
            return apiClient.processRequest(self.xHeaders, request, self.collection,
                                            self.schema, moid, overrideFilters)

        else:
            overrideFilters = [("CenterMoid", "$eq", self.centerMoid), ("IamUserMoid", "$eq", self.iamUser['Moid'])]
            # Here we force center and user id
            return apiClient.processRequest(self.xHeaders, request, self.collection,
                                            self.schema, moid, overrideFilters)

    def post(self, moid=None):

        #Verify body with schema
        valid, body = apiClient.verifyData(request, self.schema)
        if not valid:
            return apiClient.badRequest(self.xHeaders, body)

        centerRegistration = mongoClient.getDocument(Collections.centers, {"Moid": body['CenterMoid']})
        if not centerRegistration['Results']:
            return apiClient.notFound(self.xHeaders, "Center could not be found")

        centerInfo = centerRegistration['Results'][0]

        # Center id should be in body. This will be to create a user for a center if it does not exist
        # Verify the user is not already in the db
        pendingCenter = mongoClient.getDocument(self.collection, {"IamUserMoid": self.iamUser['Moid'], "CenterMoid": body['CenterMoid']})
        if pendingCenter['Results']:
            return apiClient.badRequest(self.xHeaders, "User already exists for this center")

        # TODO Check birthdate

        # Check the center to see if the user is the root user of the center to make them an admin
        logger.info(f"Checking if admin center admin: {centerInfo['Email']}, userEmail: {self.iamUser['Email']}")
        if centerInfo['Email'] == self.iamUser['Email']:
            body['Type'] = "Admin"
        else:
            body['Type'] = "User"

        body['IamUserMoid'] = self.iamUser['Moid']

        logger.info(f"Creating user {body}")
        res, centerUserMoid = mongoClient.createDocument(self.collection, body)
        if not res:
            logger.error("Failed to insert {} into centers users".format(body))
            return apiClient.internalServerError(self.xHeaders)


        # Create loayalty points
        loyaltyData = {"Points": 0, "CenterUserMoid": centerUserMoid, "CenterMoid": centerInfo['Moid']}
        res, moid = mongoClient.createDocument(Collections.points, loyaltyData)

        return apiClient.success(self.xHeaders, "Success")

    def patch(self):
        # TODO
        # Should be used to updated certain fields. Need to determine what is editable by user and center admins
        pass

    def delete(self, moid=None):
        if not moid:
            return apiClient.badRequest(self.xHeaders, "User moid required")

        err, centerUser = mongoClient.getOneDocument(self.collection, {"Moid": moid})
        if err:
            return apiClient.notFound(self.xHeaders, "User does not exist")

        err, requesterUser = mongoClient.getOneDocument(self.collection, {"IamUserMoid": self.iamUser['Moid'], "CenterMoid": centerUser['CenterMoid']})
        if err:
            return apiClient.forbidden(self.xHeaders)

        if centerUser['Moid'] == requesterUser['Moid'] or requesterUser['Type'] == "Admin":
            return apiClient.processRequest(self.xHeaders, request, self.collection,
                                            self.schema, moid)
        else:
            return apiClient.forbidden(self.xHeaders)

