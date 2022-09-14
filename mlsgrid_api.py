# From requirements.txt
import resource
from dotenv import load_dotenv
import requests
import json
from ratelimit import limits, sleep_and_retry

# From Python distribution
import os
import datetime as dt
import pytz


class MLSGridAPI():
    '''
    MLSGridAPI class requires that .env file be present and populated with MLSGrid API token
    '''
    def __init__(self, mls_system='mred', logging_tz='US/Central', debug=False):

        # MLSGrid API v2 endpoint
        self.MLSGRID_API_URL = 'https://api.mlsgrid.com/v2/'

        # MLSGrid API resources endpoints
        self.PROPERTY_URL = self.MLSGRID_API_URL + 'Property/'
        self.MEMBER_URL = self.MLSGRID_API_URL + 'Member/'
        self.OFFICE_URL = self.MLSGRID_API_URL + 'Office/'
        # TODO: complete support for OpenHouse replication (writing of records doesn't yet work)
        self.OPENHOUSE_URL = self.MLSGRID_API_URL + 'OpenHouse/'

        # Expand all resources by default (user can override)
        self.EXPAND = 'Media,Rooms,UnitTypes'
        # API expects quotes on system name
        self.MLS_SYSTEM = "'" + mls_system + "'"
        # Maximum number of records returnable = 1,000 when expanding all resources
        self.MAX_RECORDS = 1_000
        # Replicate only non-deleted records
        self.REPLICATE_NON_DELETED_RECORDS = 'MlgCanView eq true'

        # TODO: create SESSION property rather than pass the session object around everywhere
        #self.SESSION = self.create_session()

        # Timezone to use for logging
        self.LOGGING_TZ = logging_tz
        # Debug mode
        self.DEBUG = debug
        self.DEBUG_MAX_RECORDS = 2
        self.DEBUG_REPLICATE_ITERATIONS = 3

        # Output file configuration
        self.OUTPUT_FILE_PREFIX = '_output_file_'

        # Latest ModificationTimestamp
        # TODO: remove this starter value -- used only in testing prior to DB setup
        # TODO: tailor to each 
        self.modification_timestamp = {}
        #self.modification_timestamp['Property'] = '2021-05-04T20:27:18.208Z'
        #self.modification_timestamp['Member'] = ''
        self.modification_timestamp['Property'] = ''
        self.modification_timestamp['Member'] = ''
        self.modification_timestamp['Office'] = ''
        self.modification_timestamp['OpenHouse'] = ''

    # TODO: tailor to each resource
    def set_modification_timestamp(self, modification_timestamp=None, resource_name=None):
        # MLSGrid API docs say that they sort responses by ModificationTimestamp
        # This means we can safely save the last that we process as the latest
        timestamp_file = '_modification_timestamp_' + resource_name + '.txt'
        
        with open(file=timestamp_file, mode='w+') as f:
            f.write(modification_timestamp)            
        self.modification_timestamp[resource_name] = modification_timestamp
        if self.DEBUG:  print('New ModificationTimestamp = ' + self.modification_timestamp[resource_name])

    def create_session(self):
        # Configuration
        load_dotenv()
        MLSGRID_API_TOKEN=os.environ.get('MLSGRID_API_TOKEN')
        # TODO: Test for valid token
        
        # Build HTTP headers
        session = requests.Session()
        session.headers.update({'Authorization' : 'Bearer ' + MLSGRID_API_TOKEN})

        return session


    def _replicate(
            self, 
            resource_name=None,
            initial=False,
            session=None,
            next_link=None,):

        # Setup method defaults
        # Replicate property resources by default
        if resource_name == None or resource_name == 'Property':
            resource_name_url = self.PROPERTY_URL
        elif resource_name == 'Member':
            resource_name_url = self.MEMBER_URL
        elif resource_name == 'Office':
            resource_name_url = self.OFFICE_URL
        elif resource_name == 'OpenHouse':
            resource_name_url = self.OPENHOUSE_URL

        # Create a session object with authentication token
        if session == None:
            session = self.create_session()

        # TODO:
        #   * Implement some useful logging
        #       * Advise when starting & completing replication jobs
        #       * Advise of errors (and their contents)
        #   * Add $top / max_records support later ... the API knows how to manage this in the interim

        # if initial == True:
        #     URL = '{resource_name_url}?$filter=OriginatingSystemName eq {mls_system} and MlgCanView eq true&$expand={expand}'.format(
        #         resource_name_url=resource_name_url,
        #         mls_system=self.MLS_SYSTEM,
        #         expand=self.EXPAND
        #     )
        
        if initial == True:
            URL = '{resource_name_url}?$filter=OriginatingSystemName eq {mls_system} and MlgCanView eq true{expand}'.format(
                resource_name_url=resource_name_url,
                mls_system=self.MLS_SYSTEM,
                expand='' if resource_name == 'OpenHouse' else '&$expand=' + self.EXPAND
            )
        
        else:
            URL = '{resource_name_url}?$filter=OriginatingSystemName eq {mls_system} and ModificationTimestamp gt {latest_timestamp}&$expand={expand}'.format(
                resource_name_url=resource_name_url,
                mls_system=self.MLS_SYSTEM,
                latest_timestamp=self.get_latest_timestamp(resource_name=resource_name),
                expand=self.EXPAND,
            )

        # TESTING:  Limit number of records returned
        if self.DEBUG:
            URL = URL + '&$top=' + str(self.DEBUG_MAX_RECORDS)
            print('API Request URL = ' + URL)
        
        replication_iterations = 0

        while URL != 'Finished':
            # Break if in debug mode and we've replicated as many 
            if self.DEBUG and replication_iterations >= self.DEBUG_REPLICATE_ITERATIONS:
                break
            
            URL = self._replication_iteration(url=URL, session=session, resource_name=resource_name)
            replication_iterations = replication_iterations + 1

    # Implement the ratelimit decorate to limit calls to once per second    
    @sleep_and_retry
    @limits(calls=1, period=2)
    def _replication_iteration(self, url=None, session=None, resource_name=None):
        # Post GET request to API
        response = session.get(url=url)
        if self.DEBUG:  print(response)

        # Write records to database
        # FIXME:  for OpenHouse records, as this JSON schema isn't returned
        self.write_records(records=response.json()['value'], resource_name=resource_name, output_to='file')

        # set next_link to enable looping
        try:
            next_link = response.json()['@odata.nextLink']
        
        except KeyError:
            next_link = 'Finished'

        if self.DEBUG:  print('next_link = ' + next_link)

        url = next_link

        return url

    def replicate_property(self, initial=False, session=None, next_link=None):
        '''Replicates the Property resource of the MLSGrid API'''
        self._replicate(resource_name='Property', initial=initial, session=session, next_link=next_link)

    def replicate_member(self, initial=False, session=None, next_link=None):
        '''Replicates the Member resource of the MLSGrid API'''
        self._replicate(resource_name='Member', initial=initial, session=session, next_link=next_link)

    def replicate_office(self, initial=False, session=None, next_link=None):
        '''Replicates the Office resource of the MLSGrid API'''
        self._replicate(resource_name='Office', initial=initial, session=session, next_link=next_link)

    # TODO: complete support for OpenHouse replication
    # def replicate_openhouse(self, initial=False, session=None, next_link=None):
    #     '''Replicates the OpenHouse resource of the MLSGrid API'''
    #     self._replicate(resource_name='OpenHouse', initial=initial, session=session, next_link=next_link)

    # TODO: tailor output files for each resource
    # TODO: overwrite output file on initial replication, otherwise expect output file to exist
    def write_records(self, records, resource_name=None, output_to='file'):
        if output_to == 'file':
            # We're writing to a file that already exists

            output_file = self.OUTPUT_FILE_PREFIX + resource_name + '.json'

            if os.path.exists(output_file):
                with open(file=output_file, mode='r') as json_infile:
                    json_db = json.load(json_infile)

                for record in records:
                    json_db.append(record)

                with open(file=output_file, mode='w') as json_outfile:
                    json.dump(obj=json_db, fp=json_outfile, indent=4)
                print('Wrote ' + str(len(records)) + ' records!')
                self.set_modification_timestamp(records[len(records)-1]['ModificationTimestamp'], resource_name=resource_name)

            # This is the first time we're writing to the file
            if not os.path.exists(output_file):
                with open(file=output_file, mode='w') as json_outfile:
                    json.dump(obj=records, fp=json_outfile, indent=4)
                print('Wrote ' + str(len(records)) + ' records!')
                self.set_modification_timestamp(records[len(records)-1]['ModificationTimestamp'], resource_name=resource_name)
        
        elif output_to == 'database':
            pass
            

    def get_latest_timestamp(self, resource_name=None):
        # Initially returning the first timestamp provided by the API
        # return '2021-05-04T20:27:18.208Z'

        # Next iteration returning the internal property set when saving records
        #return self.modification_timestamp

        output_file = self.OUTPUT_FILE_PREFIX + resource_name + '.json'

        # Now Open JSON output file and pull latest ModificationTimestamp
        with open(file=output_file, mode='r') as json_infile:
            json_db = json.load(fp=json_infile)
        #print(json_db[len(json_db)-1])

        return json_db[len(json_db) - 1]['ModificationTimestamp']


    def _DEBUG_file_storage_cleanup(self):
        # Delete output files & modification timestamp files
        for key in self.modification_timestamp.keys():
            f = self.OUTPUT_FILE_PREFIX + key + '.json'
            if os.path.exists(f):   os.remove(f)
            f = '_modification_timestamp_' + key + '.txt'
            if os.path.exists(f):   os.remove(f)
