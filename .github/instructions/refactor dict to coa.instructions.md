---
applyTo: '**'
---
We are trying to intergrate the
"editor\src\models\coa.py"
system into the project
it is a major refactor
there is an old "dict" based system
we want to replace all uses of "dict" with the new "coa" system
so wherever you see "dict" being used
please refactor it to use "coa" instead
we are not allowing any new uses of "dict"
and we are not allowing direct access of coa._layers
please use the provided coa methods to access layers
the first question to ask yourself when refactoring is
"is there a coa method that does what I want to do?"
second question to ask yourself is
"can I add a coa method to do what I want to do?"
METHODS THAT RETURN THE INDVIDUAL LAYER OBJECTS ARE BANNED
PLEASE USE UUIDS TO IDENTIFY LAYERS
please avoid try except blocks that don't "raise e" we want to see errors in the logs
while refactoring if you need to use a "except Exception as e"
please use "loggerRaise(e, 'message')" to log the error with context
this will help us debug issues in the field
if you find except Exception as e blocks that just use a message box
please refactor them to use loggerRaise instead
we do not use generic getters or setters like "get_layer_property" or "set_layer_property"
please use specific methods like "get_layer_name" or "set_layer_opacity"
if you find code that is using index based layer access
please refactor it to use UUID based access instead
if you find code that is building dicts manually
please refactor it to use the coa.to_string() method instead
if you lack coa method to get the particular data you need
please add a new coa method to get that data
same for setting data
do not manipulate coa._layers directly
selection is not handled inside the coa model

when wanting to use the coa use COA.get_active() to get the active instance
this allows us to have a single source of truth for the coa data
please avoid adding new global variables to track coa state
if you find code that is using global variables to track coa state
please refactor it to use the coa model instead
self.coa = CoA.get_active() is acceptable in classes that need to access the coa to avoid heavy refactoring
but avoid setting self.coa = CoA() directly

when transforming layers there are two concepts to keep in mind
shallow vs deep transformations
shallow transformations
  - work only on a per selected layer basis
  - instances are treated as ridgid bodies that move with their parent layer
deep transformations
  - work on all instances across all layers
  - instances can move independently of their parent layer

avoid dictionary based data structures or lookups
['pos_x'] is bad
.pos_x is good

ONLY GIT COMMIT IF THE USER REQUESTS IT