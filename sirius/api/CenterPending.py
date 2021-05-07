'''
  Center Pending api
'''
from jupiter.vautil import SendEmail

from sirius.lib.MO import MO
from sirius.config.constants import Collections

from sirius.config.constants import DEV_USER, \
                                    CENTER_APPROVED_TEMPLATE, \
                                    CENTER_DECLINED_TEMPLATE, \
                                    LOGO_URL, BANNERS_URL

class CenterPending(MO):
    def __init__(self, resource):
        super().__init__(self.__class__.__name__)

    def get(self, moid=None):
        return self.processRequest(moid)

    def delete(self, moid=None):
        # TODO Add reason field?
        # Will remove the pending request
        if not moid:
            return self.apiClient.badRequest(self.xHeaders, "Pending center moid required")

        pendingCenter = self.mongoClient.getOneDocument(self.collection, {"Moid": moid})

        res = self.processRequest(moid)
        if res.status_code != 200:
            return res

        # Reason for checking 200 first is so we can send an email after deletion is confirmed
        #Send decline email to center registrant
        with open(CENTER_DECLINED_TEMPLATE, 'r') as stream:
            emailBodyTemplate = stream.read()

        emailBody = emailBodyTemplate.format(logo_location=LOGO_URL, user_email=pendingCenter['Email'], center_name['Center'])
        SendEmail(pendingCenter['Email'].lower(), "An error occured...", emailBody) # TODO should be an error occourd?

        return res

    def post(self, moid=None):
        # For posts we will move the pending document to centers

        if not moid:
            return self.apiClient.badRequest(self.xHeaders, "Pending center moid required")

        pendingCenter = self.mongoClient.getOneDocument(self.collection, {"Moid": moid})

        postData = pendingCenter

        #Insert pending center into active centers collection
        res, registrationMoid =  self.mongoClient.createDocument(Collections.centers, postData)
        if not res:
            self.logger.error(f"Failed to insert {postData} into centers collection")
            return self.apiClient.internalServerError(self.xHeaders)

        #Delete old pending center data
        if self.mongoClient.deleteDocument(self.collection, {"Moid": moid}) != 200:
            self.logger.error(f"Failed to delete pending data for {moid}")
            return self.apiClient.internalServerError(self.xHeaders)

        #Send approval email to center registrant
        with open(CENTER_APPROVED_TEMPLATE, 'r') as stream:
            emailBodyTemplate = stream.read()
        emailBody = emailBodyTemplate.format(logo_location=LOGO_URL, user_email=postData['Email'], center_name=pendingCenter['Center'])
        SendEmail(postData['Email'].lower(), "You're Approved!", emailBody)

        return self.apiClient.success(self.xHeaders)

