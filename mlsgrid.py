from mlsgrid_api import MLSGridAPI

# Testing in DEBUG mode
mred = MLSGridAPI(debug=True)
mred._DEBUG_file_storage_cleanup()

# Test replication of Property resource
mred.replicate_property(initial=True)
mred.replicate_property()

# Test replication of Member resource
mred.replicate_member(initial=True)
mred.replicate_member()

# Test repliication of Office resource
mred.replicate_office(initial=True)
mred.replicate_office()

# Test replication of OpenHouse resource
mred.replicate_openhouse(initial=True)
mred.replicate_openhouse()


'''
# # Testing outside of DEBUG mode
mred = MLSGridAPI()
mred._DEBUG_file_storage_cleanup()

# Test replication of Property resource
mred.replicate_property(initial=True)
mred.replicate_property()

# Test replication of Member resource
mred.replicate_member(initial=True)
mred.replicate_member()

# Test repliication of Office resource
mred.replicate_office(initial=True)
mred.replicate_office()
'''