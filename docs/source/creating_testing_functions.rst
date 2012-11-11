Creating testing functions
------------------------------

API initialization
==================
::

    from rhevm_api.utils.test_utils import get_api
    ELEMENT = 'my_object_name'
    COLLECTION = 'my_objects_collection_name'
    my_api = get_api(ELEMENT, COLLECTION)

Fetching REST Objects
======================
There are 2 possible ways:

    **using getDS**::

        from core_api.apis_utils import getDS
        objectName = getDS('ObjectName')

    **directly**::

        from core_api.apis_utils import data_st
        objectName = data_st.ObjectName

Object creation example
=======================
::
    
    def addNewObject(positive, **kwargs): # path to this function should appear in actions.conf
        majorV, minorV = kwargs.pop('version').split(".")
        objVersion = Version(major=majorV, minor=minorV)
        newObject = objectName(version=objVersion, **kwargs) # build new object
        obj, status = my_api.create(newObject, positive) # call for POST method and send new object
        return status  # must return status for test reports

Object update example
=====================
::

    def updateObject(positive, object_name, **kwargs):
        objForUpdate = my_api.find(object_name)
        newObject = objectName()
        if 'name' in kwargs:
            newObject.set_name(kwargs.pop('name'))
        if 'description' in kwargs:
            newObject.set_description(kwargs.pop('description'))
        newObject, status = my_api.update(objForUpdate, newObject, positive)
        return status

Object delete example
========================
::

    def removeObject(positive, object_name):    
        obj = my_api.find(object_name)
        return my_api.delete(dc, positive)

Get element from an  element collection
========================================
::

    def getObjectFromOtherObjectCollection(parent_obj_name, get_obj_name):
        objAPI = get_api(object_type, object_collection_name)
        parentObj = objAPI.find(parent_obj_name)
        return my_api.getElemFromElemColl(parentObj, get_obj_name)

Get element sub-collection
===========================
::

    def getObjCollection(obj_name, collection_name, collection_elem_name):
        object = my_api.find(obj_name)
        return util.getElemFromLink(object, link_name=collection_name, attr=collection_elem_name,   get_href=True)

Add element to an element sub-collection
========================================
::

    def addElementToObjCollection(positive, parent_obj_name, add_object_name):
        parentObjColl = getObjCollection(parent_obj_name, collection_name, collection_elem_name)
        addObj = my_api.find(add_object_name)
        obj, status = my_api.create(addObj, positive, collection=parentObjColl)
    return status