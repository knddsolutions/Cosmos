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
from jupiter.constants import ALLOWED_METHODS
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
                                  CENTERS_CSV


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
    def post(self):

        headers = {}
        xHeaders = json.loads(request.headers.get("x-auth"))

        apiSchema = SCHEMA['externalApis']['centerRegister']

        #Verify body with schema
        valid, body = apiClient.verifyData(request, apiSchema)
        if not valid:
            return apiClient.badRequest(headers, body)
        
        #Check if center is already registered
        center = mongoClient.getDocument(COLLECTION['centers'], {"MemberID":body['MemberID']})
        if center['Results']:
            logger.error("A center is already registered under BPAA number {body['MemberID']}")
            return apiClient.badRequest("This bowling center has already been registered")

        #Check if BPAA number is valid
        bpaa = mongoClient.getDocument(COLLECTION['members'], {"MemberID": body['MemberID']})
        
        if bpaa != 200:
            logger.error(f"BPAA number {body['MemberID']} is not valid")
            return apiClient.badRequest("Please enter a valid BPAA number")

        #Create timestamp
        ts = datetime.utcnow().isoformat()

        #Create temp data
        tempData = {"MemberID" == body['MemberID'],
                    "Email" == body['Email'],
                    "Phone" == body['Phone'],
                    "Name" == body['Name'],
                    "Timestamp" == ts}

        #Store temp center data in pending collection
        res = mongoClient.createDocument(COLLECTION['pending'], tempData)
        if res != 200:
            logger.error("Failed to create new temporary center registration for {tempData['CenterID']}")
            return apiClient.internalServerError()

        #Send confirmation email to center registrant
        with open(CENTER_REQUEST_TEMPLATE, 'r') as stream:
            emailBodyTemplate = stream.read()
        emailBody = emailBodyTemplate.format(logo_location=LOGO_URL, user_email=body['CenterID'])
        SendEmail(body['Email'].lower(), "Confirmation", emailBody)
        
        #Send email to developer for verification
        with open(CONFIRM_CENTER_TEMPLATE, 'r') as stream:
            emailBodyTemplate = stream.read()
        emailBody = emailBodyTemplate.format(logo_location=LOGO_URL, user_email=body['CenterID'])
        SendEmail(DEV_USER, "New Center Request", emailBody)

        return apiClient.success("SUCCESS! Please check email for confirmation and further instrustions")

#Api to add or redeem points to user acount
class LoyaltyPoints(Resource):
    def patch(self, moid=None):

        '''Check center auth first'''

        #Check if auth token in headers
        headers = {}
        xHeaders = json.loads(request.headers.get("x-auth"))
        apiSchema = SCHEMA['externalApis']['loyaltyPoints']

        if not moid:
            return apiClient.badRequest(headers, "User moid required")

        # Get the requester iam moid
        requesterMoid = xHeaders['IamUser']['Moid']

        #Verify body with schema
        valid, body = apiClient.verifyData(request, apiSchema)
        if not valid:
            return apiClient.badRequest(headers, body)

        # First look to see if the user being modified is valid
        #Find user in collection
        loyaltyUser = mongoClient.getDocument(COLLECTION['users'], {"Moid": moid})
        if not user['Results']:
            return apiClient.notFound("User account could not be found")

        # Precautionary 
        if len(loyaltyUser['Results']) > 1:
            logger.error(f"Found more than one user with moid {moid}")
            return apiClient.internalServerError()

        centerMoid = loyaltyUser['Results'][0]['CenterMoid']
    
        #Get user data from DB
        # Requester Moid is the IAM moid from Mars. CenterMoid is found by looking at the loyalty users moid
        # There should be unique UserMoid/CenterMoid combinations in the users db
        centerAdmin = mongoClient.getDocument(COLLECTION['users'], {"UserMoid": requesterMoid, "CenterMoid": centerMoid})
        if not requesterUser['Results']:
            return apiClient.unAuthorized(headers)

        # Verify that the user making the patch is a center admin
        if centerAdmin['Results'][0]['Type'] != "Admin":
            return apiClient.forbidden(headers)

        getPoints = mongoClient.getDocument(COLLECTION['points'], {"UserMoid": moid})
        if not getPoints['Results']:
            return apiClient.notFound("Users points could not be found")

        #Create point variables
        newPts = body['Points']
        currentPts = getPoints['Results'][0]['Points']

        #Add points
        result = currentPts + newPts

        #Results cannot be less than 0
        if result < 0:
            return apiClient.badRequest("User does not have enough points...Please try again!")

        if not mongoClient.updateDocument(COLLECTION['points'], {"Points": result}, {"UserMoid": moid}):
            logger.error(f"Failed to update new point value for {moid}")
            return apiClient.internalServerError()

        return apiClient.success(headers)

    def get(self):
        headers = {}
        xHeaders = json.loads(request.headers.get("x-auth"))
        logger.info(f"Headers: {xHeaders}")
        userMoid = xHeaders['IamUser']['Moid']
        userType = xHeaders['Iamuser']['Type']

        if userType == "Admin":
            # Process request and return
            pass
            # Allow any query

        # TODO need to figure this out
        # Maybe make it specfic to a center        
        # Possibly have admin and users as seperated collections

        return apiClient.success(headers)

#Api to approve center registration
class ConfirmCenterRegistration(Resource):
    def post(self):
        
        #TODO CHECK FOR DEVELOPER ADMIN PRIVILAGES??
      
        #Load json
        try:
            body = json.loads(request.data)
        except Exception as e:
            return apiClient.badRequest("Invalid json")
            
        #Verify body with schema
        retCode, retMessage = VaSchema.verifyPost(SCHEMA['externalApis']['approveCenter'], body)
        
        if not retCode:
            logger.warn(f"Failed approval: {retMessage}")
            logger.warn(f"Invalid data: {body}")
            return apiClient.badRequest("Invalid parameters")
            
        center = mongoClient.getDocument(COLLECTION['pending'], {"MemberID": body['MemberID']})
        if not center['Results']:
            logger.error("Failed to locate pending bpaa number {}".format(body['MemberID']))
            return apiClient.badRequest("Failed to locate pending center")
            
        #TODO GENERATE CENTER ID??
        
        #Insert file path for center logo
        center['Logo'] = BANNERS_URL + body['Path']
        
        #Insert pending center into active centers collection
        if not mongoClient.createDocument(COLLECTION['centers'], center):
            logger.error("Failed to insert {} into centers collection".format(center['MemberID']))
            return apiClient.internalServerError()
            
        #Delete old pending center data
        if not mongoClient.deleteDocument(COLLECTION['pending'], {"Bpaa": center['MemberID']}):
            logger.error("Failed to delete pending data for {}".format(center['Center']))
            return apiClient.internalServerError()
            
        #Send approval email to center registrant
        with open(CENTER_APPROVED_TEMPLATE, 'r') as stream:
            emailBodyTemplate = stream.read()
        emailBody = emailBodyTemplate.format(logo_location=LOGO_URL, user_email=center['Center'])
        SendEmail(center['Email'].lower(), "Your Approved!", emailBody)
        
        return apiClient.success({})

#Api to decline center registration
class DeclineCenterRegistration(Resource):
    def post(self):
        
        #TODO CHECK FOR DEVELOPER ADMIN PRIVILAGES??
      
        #Load json
        try:
            body = json.loads(request.data)
        except Exception as e:
            return apiClient.badRequest("Invalid json")
            
        #Verify body with schema
        retCode, retMessage = VaSchema.verifyPost(SCHEMA['externalApis']['declineCenter'], body)
        if not retCode:
            logger.warn(f"Failed to decline center: {retMessage}")
            logger.warn(f"Invalid data: {body}")
            return apiClient.badRequest("Invalid parameters")
            
        #Delete doc from pending collection
        if not mongoClient.deleteDocument(COLLECTION['pending'], {"MemberID": body['MemberID']}):
            logger.error("Failed to delete declined centers data under Bpaa number {}".format(body['MemberID']))
            return apiClient.badRequest("Failed to decline center")
            
        #Send decline email to center registrant
        with open(CENTER_DECLINED_TEMPLATE, 'r') as stream:
            emailBodyTemplate = stream.read()
        emailBody = emailBodyTemplate.format(logo_location=LOGO_URL, user_email=center['Center'])
        SendEmail(center['Email'].lower(), "An error occured...", emailBody)

'''
Api for pulling all registered centers
class RegisteredCenters(Resource):
    def get(self):
    
        #TODO
    
#Api for redeeming coupons
class Coupons(Resource):
    def post(self):
        
        #TODO
'''
#Api for suspending center services
class SuspendService(Resource):
    def post(self):
    
        #TODO CHECK FOR DEVELOPER ADMIN PRIVILAGES??
        
        #Load json
        try:
            body = json.loads(request.data)
        except Exception as e:
            return apiClient.badRequest("Invalid json")
            
        #Verify body with schema
        retCode, retMessage = VaSchema.verifyPost(SCHEMA['externalApis']['suspendCenter'], body)
        if not retCode:
            logger.warn(f"Failed to decline center: {retMessage}")
            logger.warn(f"Invalid data: {body}")
            return apiClient.badRequest("Invalid parameters")
        
        #Find registered center
        center = mongoClient.getDocument(COLLECTION['centers'], {"MemberID": body['MemberID']})
        if not center['Results']:
            logger.error("Failed to locate center memberID {}".format(body['MemberID']))
            return apiClient.badRequest("Failed to locate memberID")
        
        #Store registered center in suspended services collection
        if not mongoClient.createDocument(COLLECTION['suspended'], center):
            logger.error("Failed to create suspended center doc for memberID {}".format(body['MemberID']))
            return apiClient.internalServerError()
            
        return apiClient.success({})
            
        
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

class Users(Resource):
    def get(self):
        headers = {}
        xHeaders = json.loads(request.headers.get("x-auth"))
        logger.info(f"Headers: {xHeaders}")
        userMoid = xHeaders['IamUser']['Moid']
        userType = xHeaders['Iamuser']['Type']

        if userType == "Admin":
            pass
            # Allow any query

        # Check for user in db


        # If user, only return specific user info
        # If center admin return all from the center
        # If global admin return all
 
        pass
    def post(self):
        # Center id should be in body. This will be to create a user for a center if it does not exist
        # Verify the user is not already in the db
        # Check the center to see if the user is the root user of the center to make them an admin
        # If user already exists for the center this should return a 400
        pass
    def patch(self):
        # Should be used to updated certain fields. Need to determine what is editable by user and center admins
        pass
    def delete(self):
        # Can be done by the user or center admin
        # Global admin should not be able to delete
        pass


api.add_resource(CenterRegistration, '/centerRegister')
api.add_resource(ConfirmCenterRegistration, '/center/confirmed')
api.add_resource(DeclineCenterRegistration, '/center/declined')
api.add_resource(LoyaltyPoints, '/center/loyalty/points')
api.add_resource(LoyaltyPoints, '/center/loyalty/points/<moid>')
#api.add_resource(Coupons, '/center/loyalty/coupons')
api.add_resource(SuspendService, '/center/suspend-services')
api.add_resource(UpdateMembers, '/center/update/members')

#Run app if main
#Debug not for production
if __name__ == '__main__':
    _startup()
    app.run(debug=True, host= '0.0.0.0', port=PORT)
