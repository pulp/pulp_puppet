Plugin Reports
==============

Install Distributor
-------------------

The publish report's ``summary`` value is a string describing the success or
failure of the operation.

The publish report's ``details`` value has the following format::

 {
   "errors": [
     [
       {
         "version": "3.2.0",
         "name": "stdlib",
         "author": "puppetlabs"
       },
       "failed to download: not found"
     ]
   ],
   "success_unit_keys": [
     {
       "version": "4.1.0",
       "name": "stdlib",
       "author": "puppetlabs"
     }
   ]
 }


The ``details`` report object has two keys:

``errors``
 An array containing error reports. Each error report is a 2-member array: the
 first position is an object representing a unit key, and the second position is
 an error message.

``success_unit_keys``
 An array containing objects representing unit keys of modules that were
 successfully published.