

from rpcc import *

### Model description of a person record containing first and last names and an age
#
# Possible errors 
class ExtNoSuchPersonError(ExtLookupError):
    desc = "No such person is known."
    

class ExtPersonAlreadyExistsError(ExtLookupError):
    desc = "The person id already exists"
    
# Desription of how we identify the person    
class ExtPersonId(ExtString):
    name = "person-id"
    desc = "ID of a person"
    regexp = "^[a-z]{1,8}$"

# The person record itself
class ExtPerson(ExtPersonId):
    name = "person"
    desc = "A Person record"

    # Defines how we look up the person. This method is called in the context
    # of an RPCC function
    # Parameters are;
    #     fun: RPCC function context
    #    cval: The value of the person identifier sent to the function
    def lookup(self, fun, cval):
        # Hand over the lookup to the peron_manager
        return fun.person_manager.get_person(cval)
    #
    # The output function is the opposite of a lookup. It takes a person record
    # and returns its identifier
    def output(self, _fun, obj):
        #print "Person output", obj, obj.__dict__
        return obj.oid
    
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

#
# The model class defines whats in the Person object and what can be done with it.
#
class Person(Model):
    name = "person"  # The external name of the class, but is also used internally.
    exttype = ExtPerson # The class exposed to the outer world
    id_type = unicode  # The type of the identifier

    # The init function takes a row from the database and fills in the 
    # attributes of the Person object.
    def init(self, *args, **_kwargs): # Watch out, this is not the constructor
        a = list(args)  # Note that using this construct, the order is important
        # order here should match the order in the dq.select statement
        # in the manager's base_query classmethod. See below.
        self.oid = a.pop(0) 
        self.firstname = a.pop(0)
        self.lastname = a.pop(0)
        self.age = a.pop(0)

    # The following four methods specify howto access the attributes
    @template("person", ExtPerson)
    def get_person(self):
        return self

    @template("firstname", ExtString)
    def get_firstname(self):
        return self.firstname
    
    @template("lastname", ExtString)
    def get_lastname(self):
        return self.lastname
    
    @template("age", ExtInteger)
    def get_age(self):
        return self.age
    
    # The following method specifies how to change the age of a person
    @update("age", ExtInteger)

    def set_age(self, new_age):
        q = "UPDATE persons SET age=:age WHERE id=:id"
        self.db.put(q, id=self.oid, age=new_age)
            
class PersonManager(Manager):
    name = "person_manager"
    manages = Person

    model_lookup_error = ExtNoSuchPersonError

    def init(self):
        self._model_cache = {}
        
    @classmethod
    def base_query(cls, dq):
        dq.select("ds.id", "ds.firstname", "ds.lastname", "ds.age")
        dq.table("persons ds")
        return dq

    def get_person(self, person_id):
        return self.model(person_id)

    def search_select(self, dq):
        dq.table("persons ds")
        dq.select("ds.id")

    @search("person", StringMatch)
    def s_person(self, dq):
        dq.table("persons ds")
        return "ds.id"
    
    @search("firstname", StringMatch)
    def s_firstname(self, dq):
        dq.table("persons ds")
        return "ds.firstname"
        
    @search("lastname", StringMatch)
    def s_lasstname(self, dq):
        dq.table("persons ds")
        return "ds.lastname"
        
    @search("age", IntegerMatch)
    def s_age(self, dq):
        dq.table("persons ds")
        return "ds.age"
    
    def create_person(self, person_id, firstname, lastname, age):
        
        q = """INSERT INTO persons (id, firstname, lastname, age) 
               VALUES (:person_id, :firstname, :lastname, :age)"""
        try:
            self.db.put(q, person_id=person_id, firstname=firstname, lastname=lastname, age=age)
            
        except IntegrityError, e:
            print e
            raise ExtPersonAlreadyExistsError()