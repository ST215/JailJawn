class Facility:
    def __init__(self, facilityName, adultMaleCount, adultFemaleCount, juvenileMaleCount, juvenileFemaleCount,
                 inCountOutCountMale, inCountOutCountFemale, workersMale, workersFemale, furloughMale,
                 furloughFemale, openWardMale, openWardFemale, emergTripsMale, emergTripsFemale):

        self.facilityName = facilityName
        self.adultMaleCount = adultMaleCount
        self.adultFemaleCount = adultFemaleCount
        self.juvenileMaleCount = juvenileMaleCount
        self.juvenileFemaleCount = juvenileFemaleCount
        self.inCountOutCountMale = inCountOutCountMale
        self.inCountOutCountFemale = inCountOutCountFemale
        self.workersMale = workersMale
        self.workersFemale = workersFemale
        self.furloughMale = furloughMale
        self.furloughFemale = furloughFemale
        self.openWardMale = openWardMale
        self.openWardFemale = openWardFemale
        self.emergTripsMale = emergTripsMale
        self.emergTripsFemale = emergTripsFemale

    def print_description(self):
        print(self.facilityName, self.adultMaleCount, self.adultFemaleCount, self.juvenileMaleCount, self.juvenileFemaleCount,
              self.inCountOutCountMale, self.inCountOutCountFemale, self.workersMale, self.workersFemale, self.furloughMale,
              self.furloughFemale,
              self.openWardMale, self.openWardFemale, self.emergTripsMale, self.emergTripsFemale)
