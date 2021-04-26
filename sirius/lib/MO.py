'''
  High level request processing
'''

import json

from flask import request
from flask_restplus import Resource

from jupiter.vaapi import VaApi
from jupiter.vamongo import VaMongo
from jupiter.vaschema import VaSchema
from jupiter.valogger import VaLogger

from sirius.config.constants import DB_NAME, APP_NAME, \
                                    SCHEMA_FILE, \
                                    LOG_PATH

SCHEMA = VaSchema.loadYamlFile(SCHEMA_FILE)
logger = VaLogger(APP_NAME, LOG_PATH)
mongoClient = VaMongo(DB_NAME, logger)
apiClient = VaApi(mongoClient, logger)

class MO(Resource):
    def __init__(self, name):
        self.name = name
        self.collection = name
        self.schema = SCHEMA['externalApis'][self.name]
        self.xHeaders = json.loads(request.headers.get("x-auth"))
        self.logger = logger
        self.logger.info(f"Request data: {request.data}")
        self.apiClient = apiClient
        self.body = self.apiClient.verifyData(request, self.schema)
        self.mongoClient = mongoClient
        self.iamUser = self.xHeaders['IamUser']

    def processRequest(self, moid, overrideFilters=[]):
        return self.apiClient.processRequest(self.xHeaders, request, self.collection,
                                             self.schema, moid, overrideFilters)

