from rpcc import *
from person import  *


# Model description of a person record containing first and last names and an age
    
# Function to create a person record. These fuctions are not generated from the model    
class PersonCreate(Function):
    extname = "person_create"
    params = [("id", ExtPersonId, "Person identifier"),
              ("firstname", ExtString, "First name"),
              ("lastname", ExtString, "Last name"),
              ("age", ExtInteger, "Age")]
    desc = "Creates a person record"
    returns = (ExtNull)

    def do(self):
        self.person_manager.create_person(self.id, self.firstname, self.lastname, self.age)
        
        
# Function to remove a person record
class PersonRemove(Function):
    extname = "person_remove"
    params = [("person", ExtPerson, "Person to remove")]  # Note: Not using ExtPErsonId here. This forces a lookup so we know that he person exists.
    desc = "Removes a person from the database"
    
    returns = (ExtNull)
    
    def do(self):
        self.person_manager.remove_person(self.person)  # Send along the person object here,not its id.
