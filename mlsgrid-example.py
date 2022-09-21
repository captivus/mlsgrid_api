from src.mlsgrid_api.mlsgrid_api import MLSGridAPI

# Testing in TEST mode
mred = MLSGridAPI(debug=True, test=True)
mred._TEST_file_storage_cleanup()

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
# # Testing outside of TEST mode
mred = MLSGridAPI(debug=True)
mred._TEST_file_storage_cleanup()

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