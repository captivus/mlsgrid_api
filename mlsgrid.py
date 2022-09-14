from mlsgrid_api import MLSGridAPI

mred = MLSGridAPI(debug=True)
#mred._DEBUG_file_storage_cleanup()
#mred.replicate_property(initial=True)
mred.replicate_property()

#mred.replicate_property(resource_name='Property', initial=True)
#print(mred.get_latest_timestamp())