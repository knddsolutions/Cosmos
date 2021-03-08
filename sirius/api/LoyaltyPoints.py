import json
from flask import request
from flask_restplus import Resource
from datetime import datetime
from jupiter.vamongo import VaMongo
from jupiter.vaapi import VaApi
from jupiter.vaschema import VaSchema
from jupiter.valogger import VaLogger
from sirius.config.constants import DB_NAME, APP_NAME, \
                                    SCHEMA_FILE, \
                                    LOG_PATH, \
                                    Collections

SCHEMA = VaSchema.loadYamlFile(SCHEMA_FILE)
logger = VaLogger(APP_NAME, LOG_PATH)
mongoClient = VaMongo(DB_NAME, logger)
apiClient = VaApi(mongoClient, logger)

class LoyaltyPoints(Resource):
    def __init__(self, resource):
        self.schema = SCHEMA['externalApis']['loyaltyPoints']
        self.xHeaders = json.loads(request.headers.get("x-auth"))
        self.collection = Collections.points
        self.iamUser = self.xHeaders['IamUser']
        if "Center-Moid" in self.xHeaders:
            self.centerMoid = self.xHeaders['Center-Moid']
        else:
            self.centerMoid = None

    def patch(self, moid=None):
        if not moid:
            return apiClient.badRequest(self.xHeaders, "Points moid required")

        # Verify body with schema
        valid, body = apiClient.verifyData(request, self.schema)
        if not valid:
            return apiClient.badRequest(self.xHeaders, body)

        # Get user points info
        err, userPoints = mongoClient.getOneDocument(self.collection, {"Moid": moid})
        if err:
            logger.info(err)
            return apiClient.notFound(self.xHeaders, "Users points could not be found")
        logger.info(f"User points: {userPoints}")

        # First look to see if the user being modified is valid
        # Find user in collection
        err, loyaltyUser = mongoClient.getOneDocument(Collections.users, {"Moid": userPoints['CenterUserMoid']})
        if err:
            logger.info(err)
            logger.error("Found loyalty points, but not coresponding user")
            return apiClient.internalServerError(self.xHeaders)
        logger.info(f"Loyalty User: {loyaltyUser}")

        centerMoid = loyaltyUser['CenterMoid']

        # Get user data from DB
        # Requester Moid is the IAM moid from Mars. CenterMoid is found by looking at the loyalty users moid
        # There should be unique UserMoid/CenterMoid combinations in the users db
        err, centerAdmin = mongoClient.getOneDocument(Collections.users, {"IamUserMoid": self.iamUser['Moid'], "CenterMoid": centerMoid})
        if err:
            logger.info(err)
            return apiClient.unAuthorized(self.xHeaders)
        logger.info(f"Center admin: {centerAdmin}")

        # Verify that the user making the patch is a center admin
        if centerAdmin['Type'] != "Admin":
            return apiClient.forbidden(self.xHeaders)

        #Create point variables
        newPts = body['Points']
        currentPts = userPoints['Points']

        #Add points
        result = currentPts + newPts

        #Results cannot be less than 0
        if result < 0:
            return apiClient.badRequest(self.xHeaders, "User does not have enough points...Please try again!")

        if not mongoClient.updateDocument(self.collection, {"Points": result}, {"Moid": moid}):
            logger.error(f"Failed to update new point value for {moid}")
            return apiClient.internalServerError(self.xHeaders)

        return apiClient.success(self.xHeaders, "Success!")

    def get(self, moid=None):
        if self.iamUser['Type'] == "Admin":
            # Allow any query
            return apiClient.processRequest(self.xHeaders, request, self.collection,
                                            self.schema, moid)

        if not self.centerMoid:
            return apiClient.badRequest("Center-Moid is missing in headers")

        # Check for user in db
        err, centerUser = mongoClient.getOneDocument(Collections.users, {"IamUserMoid": self.iamUser['Moid'], "CenterMoid": self.centerMoid})

        logger.info(f"Center user type: {centerUser['Type']}")
        if centerUser['Type'] == "Admin":
            overrideFilters = [("CenterMoid", "$eq", self.centerMoid)]
            # In this case we force a search result for CenterMoid equal to the center in context
            return apiClient.processRequest(self.xHeaders, request, self.collection,
                                            self.schema, moid, overrideFilters)

        else:
            overrideFilters = [("CenterUserMoid", "$eq", centerUser['Moid'])]
            # Here we force center and user id
            return apiClient.processRequest(self.xHeaders, request, self.collection,
                                            self.schema, moid, overrideFilters)

