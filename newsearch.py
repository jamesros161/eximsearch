#!/opt/imh-python/bin/python
#/usr/bin/python

import urwid, datetime, os, subprocess, sys, json, re, shlex, gzip, time, logging, collections, socket, threading
from multiprocessing import Pool, Queue, current_process
from multiprocessing.pool import ThreadPool
from datetime import datetime, timedelta
os.nice(20)
logging.basicConfig(filename='log',filemode='a', level=logging.DEBUG)

info = logging.info
debug = logging.debug
warning = logging.warning

"""
SETTINGS / DEFAULT VALUE CLASSES
"""

class GlobalSettings(): 
    def __init__(self):
        """This class contains general settings / default variables for the application
        """
        self.dt = DateTimeSettings()
        self.lf = LogFileSettings()
        self.rl = ResultListSettings()
        self.df = DisplayFrameSettings()
        self.hostname = socket.gethostname()
        self.menuEnabled = True
        self.divChars = 1
        self.filterGuide = (
            "You can have multiple filters per filter type (ie. multiple senders, multiple recipients, etc) "
            "and these will be filtered as OR. \nEx: Two sender filters of user1@domain.com and user2@domain.com, will show all "
            "query results that were sent by user1@domain.com OR user2@domain.com.\nFilters of different types are filtered as AND."
            "Ex: Sender filter user1@domain.com and Date filter of 2019-05-24, will show all query results that were sent by "
            "user1@domain.com on the date 2019-05-24\nAcceptable Date-time Formats:MM-DD-YYYY or MM-DD-YYYY_HH:MM:SS\n"
            "Date Range formats: Start date,End date with NO SPACES. Ex: 2019-05-01,2019-05-31\nMessage Type Options: Incoming, Outgoing, Local"
                )
        self.filterTypes = [
            'senderFilter',
            'recipFilter',
            'dateFilter',
            'msgTypeFilter',
            'query'
        ]
        self.activeView = ''
    def unhandled_input(self,key):
        if type(key) == str:
            if key in ('q', 'N'):   
                views.quitLoop()
            if key in ('N', 'n'):
                views.newSearch()
            if key in ('S', 's'):
                views.statSummary()
            if key in 'tab':
                if frame.focus_position == 'footer':
                    frame.focus_position = 'body'
                else:
                    if self.menuEnabled:
                        frame.focus_position = 'footer'
            if s.activeView == 'singleEntry':
                if key in ('B', 'b'):
                    views.resultList('search' + str(searchCounter - 1).zfill(3))
            if s.activeView == 'resultList':
                if key in ('F', 'f'):
                    views.filterResults('search' + str(searchCounter - 1).zfill(3))
            if s.activeView == 'filterResults':
                if key in ('A', 'a'):
                    search.filterResults()
class DateTimeSettings():
    def __init__(self):
        """Settings for DateTime functions / formatting
        """
        self.logDateFormat ="%Y-%m-%d"
        self.displayDateFormat = "%m-%d-%Y"
        self.stringToDateFormat = "%Y-%m-%d"
        self.logDateTimeFormat = "%Y-%m-%d_%H:%M:%S.%f"
        self.displayDateTimeFormat = "%m-%d-%Y_%H:%M:%S"
    def stringToDate(self,newFilter):
        try:
            datetime.strptime(newFilter, self.displayDateTimeFormat)
        except ValueError:
            try:
                datetime.strptime(newFilter, self.displayDateFormat)
            except:
                return False
            else:
                return datetime.strptime(newFilter, self.displayDateFormat)
        else:
            return datetime.strptime(newFilter, self.displayDateTimeFormat)
class DisplayFrameSettings():
    def __init__(self):
        """Settings & Defaults for the Applications Interface
        """
        self.mainTitle = 'Exim Search Utility'
        self.palette = [
            # Name  , foreground,  background 
            ('header',  'black',    'light gray'),
            ('footer',  'black',    'light gray'),
            ('body',    'white',    'default'),
            ('bold',    'dark green, bold' , 'black')
        ]
class Menus():
        def __init__(self):
            self.main = [
            # Label ,
            # callback function
            ['(N)ew Search',
                'newSearch'],
            ['Add / Remove (F)ilters',
                'addRemoveFilters'],
            ['(S)tats Summary',
                'comingSoon'],
            ['(T)est Mailer',
                'comingSoon'],
            ['(Q)uit',
                'quitLoop']
        ]
            self.resultsList = [
                ['(N)ew Search',
                    'newSearch'],
                ['(F)ilter Current Results',
                    'filterResults'],
                ['(C)lear Applied Filters',
                    'clearFilters'],
                ['(H)ome',
                    'home'],
                ['(Q)uit',
                    'quitLoop']
            ]
            self.singleEntry = [
                ['(N)ew Search',
                    'newSearch'],
                ['(S)how Related Entries',
                    'showRelatedEntries'],
                ['(B)ack To Result List',
                    'resultList',
                    mostRecentSearchNo],
                ['(H)ome',
                    'home'],
                ['(Q)uit',
                    'quitLoop']
            ]
            self.addRemoveFilters = [
                ['(N)ew Search',
                    'newSearch'],
                ['(A)pply Current Results',
                    'applyFilters'],
                ['(B)ack To Result List',
                    'resultList',
                    mostRecentSearchNo],
                ['(H)ome',
                    'home'],
                ['(Q)uit',
                    'quitLoop']
            ]
class LogFileSettings():
    def __init__(self):
        """Settings for the LogFile class / objects
        """
        self.dir = '/var/log/'
        self.mainLogName = 'exim_mainlog'
        self.mainLogPath = os.path.join(self.dir, self.mainLogName)
class ResultListSettings():
    def __init__(self):
        """Settings specific to the ResultList view
        """
        self.ButtonColWidth = 7
        self.divChars = 1
        self.resultOverflow = False

"""
STATE MANAGEMENT / TRACKING
"""
class State():
    def __init__(self):
        self.active_view = None
        self.previous_view = None
        self.active_result_list = None
        self.previous_result_list = None
        self.active_query = None
        self.previous_query = None
        self.active_filters = None

        self.active_entry_on_screen = None
        self.prev_entry_on_screen = None
    
    def set_view(self, view):
        debug('State.set_view: %s', view)
        #assign current view to previous view and store view as active_view
        if self.active_view:
            self.prev_view = self.active_view
        else:
            self.prev_view = None
        self.active_view = view

        #store view names in easily accessible attributes

        self.active_view_name = self.active_view.view_name
        if self.prev_view:
            self.prev_view_name = self.prev_view.view_name
        else:
            self.prev_view_name = None

        #store status of active and prev view as to whether or not it was a result list or single entry
        self.is_active_view_result_list = self.active_view.is_view_result_list
        self.is_active_view_single_entry = self.active_view.is_view_single_entry
        self.is_active_view_add_filters = self.active_view.is_view_add_filters
        if self.prev_view:
            self.is_prev_view_result_list = self.prev_view.is_view_result_list
            self.is_prev_view__single_entry = self.prev_view.is_view_single_entry
            self.is_prev_view__add_filters = self.prev_view.is_view_add_filters
    def get_view(self, active_prev):
        debug('State.get_view: %s', active_prev)
        if active_prev == 'active':
            return self.active_view
        if active_prev == 'prev':
            return self.prev_view
        else:
            warning('State.get_view() active_prev parameter is invalid.')
            sys.exit('State.get_view() active_prev parameter is invalid.')
    def get_view_name(self,active_prev):
        debug('State.get_view_name: %s', active_prev)
        if active_prev == 'active':
            return self.active_view.view_name
        if active_prev == 'prev':
            return self.prev_view.view_name
        else:
            warning('State.get_view_name() active_prev parameter is invalid.')
            sys.exit('State.get_view_name() active_prev parameter is invalid.')

    def set_result_list(self,result_list):
        debug('State.set_result_list: %s', result_list)
        #assign current result_list to previous result_list and store result_list as active_result_list
        if self.active_result_list:
            self.prev_result_list = self.active_result_list
        else:
            self.prev_result_list = None
        self.active_result_list = result_list

        #store result_list names in easily accessible attributes
        self.active_result_list_name = self.active_result_list.list_name
        if self.prev_result_list:
            self.prev_result_list_name = self.prev_result_list.list_name
        else:
            self.prev_result_list_name = None
        #store status of result_list as filtered or not.
        self.is_active_result_list_filtered = self.active_result_list.is_filtered
        if self.prev_result_list:
            self.is_prev_result_list_filtered = self.prev_result_list.is_filtered
        else:
            self.prev_result_list_filtered = None
    def get_result_list(self,active_prev):
        debug('State.get_result_list: %s', active_prev)
        if active_prev == 'active':
            return self.active_result_list
        if active_prev == 'prev':
            return self.prev_result_list
        else:
            warning('State.get_result_list() active_prev parameter is invalid.')
            sys.exit('State.get_result_list() active_prev parameter is invalid.')
    def get_result_list_name(self,active_prev):
        debug('State.get_result_list_name: %s', active_prev)
        if active_prev == 'active':
            return self.active_result_list.list_name
        if active_prev == 'prev':
            return self.prev_result_list.list_name
        else:
            warning('State.get_result_list_name() active_prev parameter is invalid.')
            sys.exit('State.get_result_list_name() active_prev parameter is invalid.')
    
    def set_query(self,query):
        debug('State.set_query: %s', query)
        self.prev_query = self.active_query
        self.active_query = query
    def get_query(self, active_prev):
        debug('State.get_query: %s', active_prev)
        if active_prev == 'active':
            return self.active_query
        if active_prev == 'prev':
            return self.prev_query
        else:
            warning('State.get_query() active_prev parameter is invalid.')
            sys.exit('State.get_query() active_prev parameter is invalid.')
    
    def set_active_filters(self, active_filters):
        debug('State.set_active_filters: %s', active_filters)
        self.active_filters = active_filters
    def get_active_filters(self):
        debug('State.get_active_filters: %s', self.active_filters)
        return self.active_filters

    def set_entry_on_screen(self,entry_on_screen):
        debug('State.set_entry_on_screen: %s', entry_on_screen)
        self.prev_entry_on_screen = self.active_entry_on_screen
        self.active_entry_on_screen = entry_on_screen
    def get_entry_on_screen(self,active_prev):
        debug('State.get_entry_on_scareen: %s', active_prev)
        if active_prev == 'active':
            return self.active_entry_on_screen
        if active_prev == 'prev':
            return self.prev_entry_on_screen
        else:
            warning('State.entry_on_screen() active_prev parameter is invalid.')
            sys.exit('State.entry_on_screen() active_prev parameter is invalid.')
    def get_entry_on_screen_name(self,active_prev):
        debug('State.get_entry_on_screen_name: %s', active_prev)
        if active_prev == 'active':
            return self.active_entry_on_screen.entry_name
        if active_prev == 'prev':
            return self.prev_entry_on_screen.entry_name
        else:
            warning('State.entry_on_screen() active_prev parameter is invalid.')
            sys.exit('State.entry_on_screen() active_prev parameter is invalid.')

state = State()

class View():
    def __init__(self, view_name, 
        header, footer, body,
        is_view_result_list=False,
        is_view_single_entry=False,
        is_view_add_filters=False):

        self.view_name = view_name
        self.header = header
        self.footer = footer
        self.body = body
        self.is_view_result_list = is_view_result_list
        self.is_view_single_entry = is_view_result_list
        self.is_view_add_filters = is_view_result_list
class ResultList():
    def __init__(self,list_name,listOfEntries,is_filtered=False):
        self.list_name = list_name
        self.listOfEntries = listOfEntries
        self.is_filtered = is_filtered

class Testing():
    def set_get_views(self):
        state.set_view(View('Test A', 'Test A Header', 'Test A Header', 'Test A Body'))
        current_view = state.get_view('active')
        debug('Current View: %s', current_view)
        current_view_name = state.get_view_name('active')
        debug('Current View Name: %s', current_view_name)


        state.set_view(View('Test B', 'Test B Header', 'Test B Header', 'Test B Body'))
        current_view = state.get_view('active')
        current_view_name = state.get_view_name('active')
        prev_view = state.get_view('prev')
        prev_view_name = state.get_view_name('prev')
        debug('Current View: %s', current_view)
        debug('Current View Name: %s', current_view_name)
        debug('Previous View: %s', prev_view)
        debug('Previous View Name: %s', prev_view_name)
    def set_get_result_lists(self):
        state.set_result_list(ResultList('Test List A', ['entry1','entry2','entry3','entry4']))
        current_result_list = state.get_result_list('active')
        current_result_list_name = state.get_result_list_name('active')
        debug('\nCurrent Result List Name: %s', current_result_list_name)
        debug('Current Result LIst: %s\n', current_result_list)


        state.set_result_list(ResultList('Test List B', ['entry5','entry6','entry7','entry8']))
        current_result_list = state.get_result_list('active')
        current_result_list_name = state.get_result_list_name('active')
        prev_result_list = state.get_result_list('prev')
        prev_result_list_name = state.get_result_list_name('prev')
        debug('Current result list: %s', current_result_list)
        debug('Current result List Name: %s', current_result_list_name)
        debug('Previous result list: %s', prev_result_list)
        debug('Previous result list Name: %s', prev_result_list_name)
    def set_get_query(self):
        state.set_query('Test Query 1')
        current_query = state.get_query('active')
        debug('Current Query:: %s', current_query)

        state.set_query('Test Query 2')
        current_query = state.get_query('active')
        prev_query = state.get_query('prev')
        debug('Current Query:: %s', current_query)
        debug('Previous Query:: %s', prev_query)
    def set_get_active_filters(self):
        state.set_active_filters('Test Filters 1')
        current_filters = state.get_active_filters()
        debug('Current filters:: %s', current_filters)
test = Testing()

test.set_get_active_filters()