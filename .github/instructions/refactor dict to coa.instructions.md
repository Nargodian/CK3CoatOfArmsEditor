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