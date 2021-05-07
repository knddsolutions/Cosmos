'''
  Center Registration API
'''
from datetime import datetime
from jupiter.vautil import SendEmail

from sirius.lib.MO import MO
from sirius.config.constants import Collections

from sirius.config.constants import DEV_USER, \
                                    CENTER_CONFIRMATION_TEMPLATE, \
                                    CENTER_REQUEST_TEMPLATE, \
                                    LOGO_URL

class CenterRegistration(MO):
    def __init__(self, resoure):
        super().__init__(self.__class__.__name__)

    def get(self, moid=None):
        return self.processRequest(moid)

    def patch(self, moid=None):
        return self.processRequest(moid)

    def post(self, moid=None):
        #Check if center is already registered
        self.mongoClient.getDocumentVerifyNot(self.collection, {"MemberID": self.body['MemberID']})

        #Check if BPAA number is valid
        bpaa = self.mongoClient.getDocument(Collections.members, {"MemberID": self.body['MemberID']})

        #if not bpaa['Results']:
        #    self.logger.error(f"BPAA number {self.body['MemberID']} is not valid")
        #    return self.apiClient.badRequest(self.xHeaders, "Please enter a valid BPAA number")

        #Create timestamp
        ts = datetime.utcnow().isoformat()

        #Create temp data
        tempData = self.body
        tempData['Timestamp'] = ts

        #Store temp center data in pending collection
        res, docMoid = self.mongoClient.createDocument(Collections.pending, tempData)
        if res != 200:
            self.logger.error(f"Failed to create new temporary center registration for {tempData['MemberID']}")
            return self.apiClient.internalServerError(self.xHeaders)

        #Send confirmation email to center registrant
        with open(CENTER_REQUEST_TEMPLATE, 'r') as stream:
            emailBodyTemplate = stream.read()
        emailBody = emailBodyTemplate.format(logo_location=LOGO_URL, center_name=self.body['Center'], verify_url="test")
        SendEmail(self.body['Email'].lower(), "Confirmation", emailBody)

        #Send email to developer for verification
        with open(CENTER_CONFIRMATION_TEMPLATE, 'r') as stream:
            emailBodyTemplate = stream.read()
        emailBody = emailBodyTemplate.format(logo_location=LOGO_URL, center_name=self.body['Center'])
        SendEmail(DEV_USER, "New Center Request", emailBody) # TODO need to make pan able to handle lists

        return self.apiClient.success(self.xHeaders, "Please check email for confirmation and further instrustions")

    def delete(self, moid=None):
        return self.processRequest(moid)

