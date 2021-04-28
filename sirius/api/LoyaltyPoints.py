'''
  Loyalty points api
'''

from sirius.lib.MO import MO
from sirius.config.constants import Collections

class LoyaltyPoints(MO):
    def __init__(self, resource):
        super().__init__(self.__class__.__name__)

        if "Center-Moid" in self.xHeaders:
            self.centerMoid = self.xHeaders['Center-Moid']
        else:
            self.centerMoid = None

    def patch(self, moid=None):
        if not moid:
            return self.apiClient.badRequest(self.xHeaders, "Points moid required")

        # Get user points info
        userPoints = self.mongoClient.getOneDocument(self.collection, {"Moid": moid})

        # First look to see if the user being modified is valid
        # Find user in collection
        loyaltyUser = self.mongoClient.getOneDocument(Collections.users, {"Moid": userPoints['CenterUserMoid']})
        self.logger.info(f"Loyalty User: {loyaltyUser}")

        centerMoid = loyaltyUser['CenterMoid']

        # Get user data from DB
        # Requester Moid is the IAM moid from Mars. CenterMoid is found by looking at the loyalty users moid
        # There should be unique UserMoid/CenterMoid combinations in the users db
        centerAdmin = self.mongoClient.getOneDocument(Collections.users, {"IamUserMoid": self.iamUser['Moid'], "CenterMoid": centerMoid})
        self.logger.info(f"Center admin: {centerAdmin}")

        # Verify that the user making the patch is a center admin
        if centerAdmin['Type'] != "Admin":
            return self.apiClient.forbidden(self.xHeaders)

        #Create point variables
        newPts = self.body['Points']
        currentPts = userPoints['Points']

        #Add points
        result = currentPts + newPts

        #Results cannot be less than 0
        if result < 0:
            return self.apiClient.badRequest(self.xHeaders, "User does not have enough points...Please try again!")

        if not self.mongoClient.updateDocument(self.collection, {"Points": result}, {"Moid": moid}):
            self.logger.error(f"Failed to update new point value for {moid}")
            return self.apiClient.internalServerError(self.xHeaders)

        return self.apiClient.success(self.xHeaders, "Success!")

    def get(self, moid=None):
        if self.iamUser['Type'] == "Admin":
            # Allow any query
            return self.processRequest(moid)

        if not self.centerMoid:
            return self.apiClient.badRequest("Center-Moid is missing in headers")

        # Check for user in db
        centerUser = self.mongoClient.getOneDocument(Collections.users, {"IamUserMoid": self.iamUser['Moid'], "CenterMoid": self.centerMoid})

        self.logger.info(f"Center user type: {centerUser['Type']}")
        if centerUser['Type'] == "Admin":
            overrideFilters = [("CenterMoid", "$eq", self.centerMoid)]
            # In this case we force a search result for CenterMoid equal to the center in context
            return self.processRequest(moid, overrideFilters)

        else:
            overrideFilters = [("CenterUserMoid", "$eq", centerUser['Moid'])]
            # Here we force center and user id
            return self.processRequest(moid, overrideFilters)
