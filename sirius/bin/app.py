from flask import Flask, request
from flask_restplus import Api, Resource
from passlib.hash import sha256_crypt
import csv
import time
import json
import re
import pymongo
import threading
from datetime import datetime
from jupiter.vamongo import VaMongo
from jupiter.vaapi import VaApi, RegisterApis
from jupiter.vaschema import VaSchema
from jupiter.valogger import VaLogger
from jupiter.vautil import SendEmail
from jupiter.vacrypto import EncryptPassword, \
                              VerifyPassword, \
                              GenerateToken, \
                              GetExpirationTime, \
                              TimestampExpired
from sirius.config.constants import DB_NAME, APP_NAME, \
                                  COLLECTION, APP_DNS, \
                                  SCHEMA_FILE, ROOT_USERS, \
                                  PORT, LOG_PATH, DEV_USER, \
                                  CENTER_CONFIRMATION_TEMPLATE, \
                                  CENTER_APPROVED_TEMPLATE, \
                                  CENTER_DECLINED_TEMPLATE, \
                                  SUCCESS_PAGE_TEMPLATE, \
                                  CENTER_REQUEST_TEMPLATE, \
                                  CRON_SLEEP_SECONDS, \
                                  LOGO_URL, \
                                  BANNERS_URL, \
                                  CENTERS_CSV, \
                                  Collections


#Set name of flask instance
app = Flask(__name__)
api = Api(app)

#-----GLOBAL VARIABLES-----
SCHEMA = VaSchema.loadYamlFile(SCHEMA_FILE)
logger = VaLogger(APP_NAME, LOG_PATH)
mongoClient = VaMongo(DB_NAME, logger)
apiClient = VaApi(mongoClient, logger)
#--------------------------


#--------CENTER API'S---------
#Api for center registration

def _startup():
    ''' Application startup method
        1. Registers APIS
    '''
    logger.info("Application startup")

    #_tempUpdateDB()
    # Rgister api
    RegisterApis(APP_DNS, SCHEMA, logger)


class CenterRegistration(Resource):
    def __init__(self, resoure):
        self.schema = SCHEMA['externalApis']['centerRegister']
        self.xHeaders = json.loads(request.headers.get("x-auth"))
        self.collection = COLLECTION['centers']

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
        bpaa = mongoClient.getDocument(COLLECTION['members'], {"MemberID": body['MemberID']})
        
        #if bpaa != 200:
        #    logger.error(f"BPAA number {body['MemberID']} is not valid")
        #    return apiClient.badRequest(self.xHeaders, "Please enter a valid BPAA number")

        #Create timestamp
        ts = datetime.utcnow().isoformat()

        #Create temp data
        tempData = body
        tempData['Timestamp'] = ts

        #Store temp center data in pending collection
        res, docMoid = mongoClient.createDocument(COLLECTION['pending'], tempData)
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

class PendingCenterRegistration(Resource):
    def __init__(self, resource):
        self.schema = SCHEMA['externalApis']['centerPending']
        self.xHeaders = json.loads(request.headers.get("x-auth"))
        self.collection = COLLECTION['pending']

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
        postData['Logo'] = BANNERS_URL + body['Path']

        #Insert pending center into active centers collection
        res, registrationMoid =  mongoClient.createDocument(COLLECTION['centers'], postData)
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

class CenterUsers(Resource):
    def __init__(self, resource):
        self.schema = SCHEMA['externalApis']['centerUsers']
        self.xHeaders = json.loads(request.headers.get("x-auth"))
        self.collection = COLLECTION['users']
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

        centerRegistration = mongoClient.getDocument(COLLECTION['centers'], {"Moid": body['CenterMoid']})
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


#Api to add or redeem points to user acount
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

#Api for updating centers and bpaa #s in bpaa collection
class UpdateMembers(Resource):
    def post(self):
        
        #Drop members collection on update
        if not COLLECTION['members'].drop():
            logger.info("Members collection could not be dropped or does not exist")
                
        #Open csv file in read mode
        with open(CENTERS_CSV, 'r') as csvfile:
            header = ["MemberID", "Center", "Contact"]
            csvreader = csv.reader(csvfile)
        
        #Create a doc for each row and store in members collection
        for row in csvreader:
            doc={}
            for n in range(0,len(header)):
                doc[header[n]] = row[n]
            
            res = mongoClient.createDocument(COLLECTION['members'], doc)
            
            if res != 200:
                logger.error("Failed to insert csv file")
                return apiClient.internalServerError()
                
        return apiClient.success({})

'''
#Api for redeeming coupons
class Coupons(Resource):
    def post(self):
        
        #TODO
'''
api.add_resource(UpdateMembers, '/center/update/members')

api.add_resource(CenterRegistration, '/centerRegister')
api.add_resource(CenterRegistration, '/centerRegister/<moid>')
api.add_resource(PendingCenterRegistration, '/centerPending')
api.add_resource(PendingCenterRegistration, '/centerPending/<moid>')
api.add_resource(CenterUsers, '/centerUsers')
api.add_resource(CenterUsers, '/centerUsers/<moid>')
api.add_resource(LoyaltyPoints, '/loyaltyPoints')
api.add_resource(LoyaltyPoints, '/loyaltyPoints/<moid>')

#api.add_resource(Coupons, '/center/loyalty/coupons')

#Run app if main
#Debug not for production
if __name__ == '__main__':
    _startup()
    app.run(host= '0.0.0.0', port=PORT)
