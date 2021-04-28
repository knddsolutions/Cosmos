'''
  Center Users api
'''

from sirius.lib.MO import MO
from sirius.config.constants import Collections

class CenterUsers(MO):
    def __init__(self, resource):
        super().__init__(self.__class__.__name__)
        if "Center-Moid" in self.xHeaders:
            self.centerMoid = self.xHeaders['Center-Moid']
        else:
            self.centerMoid = None

    def get(self, moid=None):
        if self.iamUser['Type'] == "Admin":
            # Allow any query
            return self.processRequest(moid)

        self.logger.info(f"Headers: {self.xHeaders}")
        if not self.centerMoid:
            overrideFilters = [("IamUserMoid", "$eq", self.iamUser['Moid'])]
            return self.processRequest(moid, overrideFilters)

        # Check for user in db
        centerUser = self.mongoClient.getOneDocument(self.collection, {"IamUserMoid": self.iamUser['Moid'], "CenterMoid": self.centerMoid})

        if centerUser['Type'] == "Admin":
            overrideFilters = [("CenterMoid", "$eq", self.centerMoid)]
            # In this case we force a search result for CenterMoid equal to the center in context
            return self.processRequest(moid, overrideFilters)

        else:
            overrideFilters = [("CenterMoid", "$eq", self.centerMoid), ("IamUserMoid", "$eq", self.iamUser['Moid'])]
            # Here we force center and user id
            return self.processRequest(moid, overrideFilters)

    def post(self, moid=None):

        centerInfo = self.mongoClient.getOneDocument(Collections.centers, {"Moid": self.body['CenterMoid']})

        # Center id should be in body. This will be to create a user for a center if it does not exist
        # Verify the user is not already in the db
        self.mongoClient.getDocumentVerifyNot(self.collection, {"IamUserMoid": self.iamUser['Moid'], "CenterMoid": self.body['CenterMoid']})

        # TODO Check birthdate

        # Check the center to see if the user is the root user of the center to make them an admin
        self.logger.info(f"Checking if admin center admin: {centerInfo['Email']}, userEmail: {self.iamUser['Email']}")
        if centerInfo['Email'] == self.iamUser['Email']:
            self.body['Type'] = "Admin"
        else:
            self.body['Type'] = "User"

        self.body['IamUserMoid'] = self.iamUser['Moid']

        self.logger.info(f"Creating user {self.body}")
        res, centerUserMoid = self.mongoClient.createDocument(self.collection, self.body)
        if not res:
            self.logger.error(f"Failed to insert {self.body} into centers users")
            return self.apiClient.internalServerError(self.xHeaders)

        # Create loayalty points
        loyaltyData = {"Points": 0, "CenterUserMoid": centerUserMoid, "CenterMoid": centerInfo['Moid']}
        res, moid = self.mongoClient.createDocument(Collections.points, loyaltyData)

        return self.apiClient.success(self.xHeaders, "Success")

    def patch(self):
        # TODO
        # Should be used to updated certain fields. Need to determine what is editable by user and center admins
        pass

    def delete(self, moid=None):
        if not moid:
            return self.apiClient.badRequest(self.xHeaders, "User moid required")

        centerUser = self.mongoClient.getOneDocument(self.collection, {"Moid": moid})

        requesterUser = self.mongoClient.getOneDocument(self.collection, {"IamUserMoid": self.iamUser['Moid'], "CenterMoid": centerUser['CenterMoid']})

        if centerUser['Moid'] == requesterUser['Moid'] or requesterUser['Type'] == "Admin":
            return self.processRequest(moid)
        else:
            return self.apiClient.forbidden(self.xHeaders)
