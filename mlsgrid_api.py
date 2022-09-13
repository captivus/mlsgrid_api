# From requirements.txt
from dotenv import load_dotenv
import requests
import json

# From Python distribution
import os
import datetime as dt
import pytz


class MLSGridAPI():
    '''
    MLSGridAPI class requires that .env file be present and populated with MLSGrid API token
    '''
    def __init__(self, mls_system='mred', logging_tz='US/Central'):

        # MLSGrid API v2 endpoint
        self.MLSGRID_API_URL = 'https://api.mlsgrid.com/v2/'

        # MLSGrid API resources endpoints
        self.PROPERTY_URL = self.MLSGRID_API_URL + 'Property/'
        self.MEMBER_URL = self.MLSGRID_API_URL + 'Member/'
        self.OFFICE_URL = self.MLSGRID_API_URL + 'Office/'
        self.OPENHOUSE_URL = self.MLSGRID_API_URL + 'OpenHouse/'

        # Expand all resources by default (user can override)
        self.EXPAND = 'Media,Rooms,UnitTypes'
        # API expects quotes on system name
        self.MLS_SYSTEM = "'" + mls_system + "'"
        # Maximum number of records returnable = 1,000 when expanding all resources
        self.MAX_RECORDS = 1_000
        # Replicate only non-deleted records
        self.REPLICATE_NON_DELETED_RECORDS = 'MlgCanView eq true'
        # Timezone to use for logging
        self.LOGGING_TZ = logging_tz

        # Latest ModificationTimestamp
        # TODO: remove this starter value -- used only in testing prior to DB setup
        self.modification_timestamp = '2021-05-04T20:27:18.208Z'

    def set_modification_timestamp(self, modification_timestamp=''):
        # MLSGrid API docs say that they sort responses by ModificationTimestamp
        # This means we can safely save the last that we process as the latest
        with open(file='modification_timestamp.txt', mode='w+') as f:
            if modification_timestamp == '':
                modification_timestamp = self.modification_timestamp
            f.write(modification_timestamp)            
        self.modification_timestamp = modification_timestamp

    def create_session(self):
        # Configuration
        load_dotenv()
        MLSGRID_API_TOKEN=os.environ.get('MLSGRID_API_TOKEN')
        # TODO: Test for valid token
        
        # Build HTTP headers
        session = requests.Session()
        session.headers.update( {'Authorization' : 'Bearer ' + MLSGRID_API_TOKEN})

        return session

    def replicate(
            self, 
            resource_name=None,
            initial=False,
            session=None,
            next_link=None,):

        # Setup method defaults
        # Replicate property resources by default
        if resource_name == None or resource_name == 'Property':
            resource_name = self.PROPERTY_URL
        elif resource_name == 'Member':
            resource_name = self.MEMBER_URL
        elif resource_name == 'Office':
            resource_name = self.OFFICE_URL
        elif resource_name == 'OpenHouse':
            resource_name = self.OPENHOUSE_URL

        # Create a session object with authentication token
        if session == None:
            session = self.create_session()

        # TODO:
        #   * Implement some useful logging
        #       * Advise when starting & completing replication jobs
        #       * Advise of errors (and their contents)
        #   * Add $top / max_records support later ... the API knows how to manage this in the interim

        '''
        URL Schema:
        [Main API endpoint] / [Resource name] ? $filter=OriginatingSystemName eq [mls_system] and ModificationTimestamp gt [most recent timestampe in db] &$expand=Media,Rooms,UnitTypes &$top=1000
        https://api.mlsgrid.com/v2/Property?$filter=OriginatingSystemName%20eq%20%27actris%27%20and%20ModificationTimestamp%20gt%202020-12-30T23:59:59.99Z&$expand=Media,Rooms,UnitTypes

        NB example from Postman includes spaces:
        url = "https://api.mlsgrid.com/v2/Property?$filter=OriginatingSystemName eq 'mred' and MlgCanView eq true&$expand=Media,Rooms,UnitTypes"

        NB example nextLink when querying only 1 record (initial replication):
        https://api.mlsgrid.com/v2/Property?$top=1&$expand=Media%2CRooms%2CUnitTypes&$skip=1
        '''

        if initial == True:
            URL = '{resource_name}?$filter=OriginatingSystemName eq {mls_system} and MlgCanView eq true&$expand={expand}'.format(
                resource_name=resource_name,
                mls_system=self.MLS_SYSTEM,
                expand=self.EXPAND
            )
        
        else:
            URL = '{resource_name}?$filter=OriginatingSystemName eq {mls_system} and ModificationTimestamp gt {latest_timestamp}&$expand={expand}'.format(
                resource_name=resource_name,
                mls_system=self.MLS_SYSTEM,
                latest_timestamp=self.get_latest_timestamp(),
                expand=self.EXPAND,
            )

        # TESTING:  only getting 1 record at a time
        URL = URL + '&$top=2'

        print('API Request URL = ' + URL)
        
        while URL != 'Finished':
            # Post GET request to API
            response = session.get(url=URL)
            print(response)
            # Write records to database
            self.write_records(response.json()['value'])

            # set next_link to enable looping
            try:
                next_link = response.json()['@odata.nextLink']
            
            except KeyError:
                next_link = 'Finished'

            print('next_link = ' + next_link)
            URL = next_link
    

    def replicate_property(self, initial=False):
        '''Replicates the Property resource of the MLSGrid API'''

        pass

    def replicate_member(self, initial=False):
        pass

    def replicate_office(self, initial=False):
        pass

    def replicate_openhouse(self, initial=False):
        pass

    def write_records(self, records, output='file.json'):
        if output != 'database':
            # We're writing to a file that already exists
            if os.path.exists(output):
                with open(file=output, mode='r') as json_infile:
                    json_db = json.load(json_infile)

                for record in records:
                    json_db.append(record)

                with open(file=output, mode='w') as json_outfile:
                    json.dump(obj=json_db, fp=json_outfile, indent=4)
                print('Wrote ' + str(len(records)) + ' records!')
                self.set_modification_timestamp(records[len(records)-1]['ModificationTimestamp'])
                print('New ModificationTimestamp = ' + self.modification_timestamp)

            # This is the first time we're writing to the file
            if not os.path.exists(output):
                with open(file=output, mode='w') as json_outfile:
                    json.dump(obj=records, fp=json_outfile, indent=4)
                print('Wrote ' + str(len(records)) + ' records!')
                self.set_modification_timestamp(records[len(records)-1]['ModificationTimestamp'])
                print('New ModificationTimestamp = ' + self.modification_timestamp)
            

    def get_latest_timestamp(self, source='file.json'):
        # Initially returning the first timestamp provided by the API
        # return '2021-05-04T20:27:18.208Z'

        # Next iteration returning the internal property set when saving records
        #return self.modification_timestamp

        # Now Open JSON output file and pull latest ModificationTimestamp
        with open(file=source, mode='r') as json_infile:
            json_db = json.load(fp=json_infile)
        print(json_db[len(json_db)-1])

        return json_db[len(json_db) - 1]['ModificationTimestamp']



mred = MLSGridAPI()
mred.replicate(resource_name='Property', initial=True)
#print(mred.get_latest_timestamp())