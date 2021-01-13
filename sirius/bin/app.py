from flask import Flask, request
from flask_restplus import Api, Resource
from passlib.hash import sha256_crypt
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
from jupiter.constants import ALLOWED_METHODS, APP_DOMAIN_NAME
from jupiter.vacrypto import EncryptPassword, \
                              VerifyPassword, \
                              GenerateToken, \
                              GetExpirationTime, \
                              TimestampExpired
from sirius.config.constants import DB_NAME, APP_NAME, \
                                  COLLECTION, APP_DNS, \
                                  SCHEMA_FILE, ROOT_USERS, \
                                  PORT, LOG_PATH, DEV_USER, \
                                  CONFIRM_CENTER_TEMPLATE, \
                                  CENTER_APPROVED_TEMPLATE, \
                                  SUCCESS_PAGE_TEMPLATE, \
                                  CENTER_REQUEST_TEMPLATE, \
                                  CRON_SLEEP_SECONDS, \
                                  LOGO_URL, \


#Set name of flask instance
app = Flask(__name__)
api = Api(app)

#-----GLOBAL VARIABLES-----
SCHEMA = VaSchema.loadYamlFile(SCHEMA_FILE)
app = Flask(__name__)
logger = VaLogger(APP_NAME, LOG_PATH)
mongoClient = VaMongo(DB_NAME, logger)
apiClient = VaApi(mongoClient, logger)
#--------------------------


#--------CENTER API'S---------
class CenterRegistration(Resource):
    def post(self):

        #Load json
        try:
            body = json.loads(request.data)
        except Exception as e:
            return apiClient.badRequest("Invalid json")

        #Verify body with schema
        retCode, retMessage = VaSchema.verifyPost(SCHEMA['externalApis']['centerRegister'], body)
        
        if not retCode:
            logger.warn(f"Failed registration: {retMessage}")
            logger.warn(f"Invalid data: {body}")
            return apiClient.badRequest("Invalid parameters")

        #Check if center is already registered
        center = mongoClient.getDocument(COLLECTION['centers'], {"number":body['Bpaa']})

        if center['Results']:
            logger.error("A center is already registered under BPAA number {}".format(body['bpaa']))
            return apiClient.badRequest("This bowling center has already been registered")

        #Check if BPAA number is valid
        if not bpaa = mongoClient.getDocument(COLLECTION['bpaa'], {"number": body['Bpaa']}):
            logger.error("BPAA number {} is not valid".format(body['Bpaa']))
            return apiClient.badRequest("Please enter a valid BPAA number")

        #Create timestamp
        ts = datetime.utcnow().isoformat()

        #Create temp data
        tempData = {"Center" = body['Name'],
                    "Bpaa" = body['Bpaa'],
                    "Email" = body['Email'],
                    "Phone" = body['Phone'],
                    "Timestamp" = ts}

        #Store temp center data in pending collection
        res = mongoClient.createDocument(COLLECTION['pending'], tempData)
        if res != 200:
            logger.error("Failed to create new temporary center registration for {}".format(tempData['Center']))
            return apiClient.internalServerError()

        #Send confirmation email to center registrant
        with open(CENTER_REQUEST_TEMPLATE, 'r') as stream:
            emailBodyTemplate = stream.read()
        emailBody = emailBodyTemplate.format(logo_location=LOGO_URL, user_email=body['Center'])
        SendEmail(body['Email'].lower(), "Confirmation", emailBody)
        
        #Send email to developer for verification
        with open(CONFIRM_CENTER_TEMPLATE, 'r') as stream:
            emailBodyTemplate = stream.read()
        emailBody = emailBodyTemplate.format(logo_location=LOGO_URL, user_email=body['Center'])
        SendEmail(DEV_USER, "New Center Request", emailBody)
        
        return apiClient.success("SUCCESS! Please check email for confirmation and further instrustions")

#Add or redeem points from user account
class LoyaltyPoints(Resource):
    def post(self):

        '''Check auth auth token first'''

        #Check if auth token in headers
        authToken = request.headers.get("X-Auth-Token")
        if not authToken:
            return apiClient.unAuthorized({})

        #Check if token matches in DB
        auth = mongoClient.getDocument(COLLECTION['auth'], {"Token": authToken})
        if not auth['Results']:
            return apiClient.unAuthorized({})
        
        #Check if token has expired
        if TimestampExpired(res['Expires']):
            logger.info("Auth token expired")
            return apiClient.unAuthorized({})

        '''Now handle body'''

        #Load json
        try:
            body = json.loads(request.data)
        except Exception as e:
            return apiClient.badRequest("Invalid json")
            
        #Verify body with schema
        retCode, retMessage = VaSchema.verifyPost(SCHEMA['externalApis']['loyaltyPoints'], body)
        
        if not retCode:
            logger.warn(f"Failed registration: {retMessage}")
            logger.warn(f"Invalid data: {body}")
            return apiClient.badRequest("Invalid parameters")

        #Find user in collection
        user = mongoClient.getDocument(COLLECTION['users'], {"Email": body['Email']})
        if not user['Results']:
            return apiClient.notFound("User account could not be found")
            
        getPoints = mongoClient.getDocument(COLLECTION['points'], {"userID": user['userID']})
        if not getPoints['Results']:
            return apiClient.notFound("Users points could not be found")

        #Create point variables
        newPts = body['Points']
        currentPts = getPoints['Points']

        #Add points
        result = currentPts + newPts

        #Results cannot be less than 0
        if result < 0:
            return apiClient.badRequest("User does not have enough points...Please try again!")

        #TODO UPDATE COLLECTION

        #TODO RETURN SUCCESS

class CenterApproval(Resource):
    def post(self):
        
        #TODO CHECK FOR DEVELOPER ADMIN PRIVILAGES??
      
        #Load json
        try:
            body = json.loads(request.data)
        except Exception as e:
            return apiClient.badRequest("Invalid json")
            
        #Verify body with schema
        retCode, retMessage = VaSchema.verifyPost(SCHEMA['externalApis']['centerApproval'], body)
        
        if not retCode:
            logger.warn(f"Failed registration: {retMessage}")
            logger.warn(f"Invalid data: {body}")
            return apiClient.badRequest("Invalid parameters")
            
        center = mongoClient.getDocument(COLLECTION['pending'], {"Bpaa": body['Bpaa']})
        if not center['Results']:
            logger.error("Failed to locate pending bpaa number {}".format(body['Bpaa'])")
            return apiClient.badRequest("Failed to locate pending center")
            
        #TODO GENERATE CENTER ID??
        
        #Insert pending center into active centers collection
        if not mongoClient.createDocument(COLLECTION['centers'], center):
            logger.error("Failed to insert {} into centers collection".format(center['Name']))
            return apiClient.internalServerError()
            
        #Delete old pending center data
        if not mongoClient.deleteDocument(COLLECTION['pending'], {"Bpaa": center['Bpaa']}):
            logger.error("Failed to delete pending data for {}".format(center['Name']))
            return apiClient.internalServerError()
            
        #Send approval email to center registrant
        with open(CENTER_APPROVED_TEMPLATE, 'r') as stream:
            emailBodyTemplate = stream.read()
        emailBody = emailBodyTemplate.format(logo_location=LOGO_URL, user_email=center['Name'])
        SendEmail(center['Email'].lower(), "Your Approved!", emailBody)
        
        return apiClient.success({})
        
#TODO CREATE CENTER DECLINE API
        
api.add_resource(CenterRegistration, '/center/registration')
api.add_resource(CenterApproval, '/center/approved')
api.add_resource(CenterDecline, '/center/declined')
api.add_resource(Points, 'loyalty/points')

#Run app if main
#Debug not for production
if __name__ = '__main__':
    app.run(debug=True, host= '0.0.0.0')
