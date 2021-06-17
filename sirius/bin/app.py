from flask import Flask
from flask_restplus import Api

from jupiter.vaapi import RegisterApis
from jupiter.valogger import VaLogger
from jupiter.vaschema import VaSchema

from sirius.api import *
from sirius.config.constants import APP_NAME, \
                                    APP_DNS, \
                                    SCHEMA_FILE, \
                                    PORT, LOG_PATH

#Set name of flask instance
app = Flask(__name__)
api = Api(app)

SCHEMA = VaSchema.loadYamlFile(SCHEMA_FILE)
logger = VaLogger(APP_NAME, LOG_PATH)

def _startup():
    ''' Application startup method
        1. Registers APIS
    '''
    logger.info("Application startup")

    #_tempUpdateDB()
    # Rgister api
    RegisterApis(APP_DNS, SCHEMA, logger)



api.add_resource(CenterRegistration, '/CenterRegistration')
api.add_resource(CenterRegistration, '/CenterRegistration/<moid>')
api.add_resource(CenterPending, '/CenterPending')
api.add_resource(CenterPending, '/CenterPending/<moid>')
api.add_resource(CenterUsers, '/CenterUsers')
api.add_resource(CenterUsers, '/CenterUsers/<moid>')
api.add_resource(LoyaltyPoints, '/LoyaltyPoints')
api.add_resource(LoyaltyPoints, '/LoyaltyPoints/<moid>')
api.add_resource(UpdateMembers, '/center/updateMembers')

#api.add_resource(Coupons, '/center/loyalty/coupons')

#Run app if main
#Debug not for production
if __name__ == '__main__':
    _startup()
    app.run(host= '0.0.0.0', port=PORT)
