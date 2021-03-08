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

class UpdateMembers(Resource):
    def post(self):

        #Drop members collection on update
        if not Collections.members.drop():
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

            res = mongoClient.createDocument(Collections.members, doc)

            if res != 200:
                logger.error("Failed to insert csv file")
                return apiClient.internalServerError()

        return apiClient.success({})

