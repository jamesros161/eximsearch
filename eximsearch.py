#!/usr/bin/python
#/opt/imh-python/bin/python

import urwid, datetime, os, subprocess, sys, json, re, shlex, gzip, time, logging, collections, socket, threading
from multiprocessing import Pool, Queue, current_process
from multiprocessing.pool import ThreadPool
from datetime import datetime, timedelta

os.nice(20)
logging.basicConfig(filename='log',filemode='a', level=logging.DEBUG)
info = logging.info
debug = logging.debug
warning = logging.warning
searchCounter = 1
filterEntryEditText = ''
mostRecentSearchNo = ''
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

        self.mainMenu = [
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
        self.resultsListMenu = [
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
        self.singleEntryMenu = [
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
        self.filterResultsMenu = [
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
s = GlobalSettings()
"""
CUSTOM WIDGET CLASSES
"""

class ButtonLabel(urwid.SelectableIcon):
    def __init__(self, text):
        """Subclassing for urwid.Button's labeling
           This customization removes the cursor from
           the active button
           This should only need to be called by the 
           FixedButton class.
        
        Arguments:
            urwid {class} -- urwid base class
            text {str} -- Button Label
        """
        curs_pos = len(text) + 1 
        urwid.SelectableIcon.__init__(self, 
            text, cursor_position=curs_pos)
class FixedButton(urwid.Button):
    """SubClass of the urwid.Button class used 
       along with ButtonLabel in order to customize
       the appearance and behavior of buttons.
    
    Arguments:
        urwid {class} -- urwid base class
    
    Returns:
        urwid.Button -- a standard urwid Button
    """
    _selectable = True
    signals = ["click"]
    def __init__(self, thisLabel, on_press=None, user_data=None):
        """Creates a new Button
        
        Arguments:
            thisLabel {text} -- Button Label
        
        Keyword Arguments:
            on_press {callback} -- function to be executed on click (default: {None})
            user_data {tuple} -- tuple (or list) that contains any arguments 
                 or data to be passed to on_ress function  (default: {None})
        """
        self._label = ButtonLabel(thisLabel)
        # you could combine the ButtonLabel object with other widgets here
        self.user_data = user_data
        self.on_press = on_press
        display_widget = self._label 
        urwid.WidgetWrap.__init__(self, 
            urwid.AttrMap(display_widget, 
            None, focus_map="header"))
        self.callback = on_press
    def keypress(self, size, key):
        """Overrides default urwid.Button.keypress method
        
        Arguments:
            size {int} -- size of widget
            key {bytes or unicode} -- [a single keystroke value]
        
        Returns:
            None or Key -- [None if key was handled by this widget or 
                            key (the same value passed) if key was 
                            not handled by this widget]
        """
        if key in ('enter', 'space'):
            if self.user_data != None:
                self.callback(self.user_data)
            else:
                self.callback()
        else:
            return key
        #key = super(FixedButton, self).keypress(size, key)
        #logging.info("keypress super key = %s", key)
    def set_label(self, new_label):
        """Method to allow changing the button's label
        
        Arguments:
            new_label {[str]} -- [New Button Label]
        """
        self._label.set_text(str(new_label))
    def mouse_event(self, size, event, button, col, row, focus):
        """
        handle any mouse events here
        and emit the click signal along with any data 
        """
        pass
    def disable(self):
        """Function to allow the disabling of the button"""
        _selectable = False
    def enable(self):
        """Function to allow the enabling of a disabled button"""
        _selectable = True
class MyWidgets():
    """A collection of functions to simplify creation of
       frequently used widgets """

    def __init__(self):
        self.div = urwid.Divider(' ',top=0,bottom=0)
        self.blankFlow = self.getText('body','','center')
        self.blankBox = urwid.Filler(self.blankFlow)
        self.searchProgress = urwid.ProgressBar('body', 'header', current=0, done=100, satt=None)
    def getButton(self, thisLabel, callingObject, callback, user_data=None, buttonMap='bold', focus_map='header'):
        """Creates and returns a FixedButton object.
        
        Arguments:
            thisLabel {[str]} -- Label of the Button
            callingObject {obj} -- The name of the object that the callback belongs to
            callback {function} -- [function to be executed when button is clicked]
        
        Keyword Arguments:
            user_data {tuple} -- A tuple or list of arguments or data to be passed to 
                                 the callback function (default: {None})
        
        Returns:
            FixedButton -- A FixedButton object
            FLOW WIDGET
        """
        button = FixedButton(str(thisLabel),
        on_press=getattr(callingObject, callback),
        user_data=user_data)
        button._label.align = 'center'
        buttonMap = urwid.AttrMap(button, buttonMap, focus_map=focus_map)
        return buttonMap
    def getText(self,format,textString, alignment,**kwargs):
        """Creates a basic urwid.Text widget
        
        Arguments:
            format {str} -- Name of a format attribute specified in DisplayFrameSettings.pallette
            textString {str} -- The text string contents of text widget
            alignment {str} -- Text alignment (left, right, center)
        
        Returns:
            urwid.Text -- An urwidText Widget
            FLOW WIDGET
        """
        return urwid.Text((format, textString), align=alignment, wrap='space', **kwargs)
    def getColRow(self,items, **kwargs):
        """Creates a single row of columns
        
        Arguments:
            items {list} -- List of widgets, each item forming one column.
                             Items may be tuples containing width specs
        
        Returns:
            [urwid.Column] -- An urwid.Columns object 
            FLOW / BOX WIDGET
        """
        return urwid.Columns(items,
            dividechars=s.divChars,
            focus_column=None,
            min_width=1,
            box_columns=None)
    def getLineBox(self,contents,title, **kwargs):
        """ Creates a SimpleFocusListWalker using contents as the list,
            adds a centered title, and draws a box around it. If the contents
            are not a list of widgets, then set content_list to False.
            
            The character that is used to draw the border can 
            be adjusted with the following keyword arguments:
                tlcorner,tline,trcorner,blcorner,rline,bline,brcorner
        
        Arguments:
            contents {widget} -- an original_widget, no widget lists -
            title {string} -- Title String
        
        Keyword Arguments:
            content_list -- If true, the value of contents must be a list of widgets
                            If false, the value must be a single widget to be used as
                            original_widget -- default{False}
        
        Returns:
            urwid.LineBox -- urwid.LineBox object
            FLOW / BOX WIDGET
        """
        return urwid.LineBox(contents, title=str(title), title_align='center')
    def getListBox(self,contents):
        """Creates a ListBox using a SimpleFocusListWalker, with the contents
           being a list of widgets
        
        Arguments:
            contents {list} -- list of widgets
        
        Returns:
            list -- [0]: urwid.ListBox
                    [1]: urwid.SimpleFocusListWalker - Access this to make changes to the list
                               which the SimpleFocusListWalker will follow.   
        BOX WIDGET 
        """
        debug('Started getListBox: %s', contents)
        walker = urwid.SimpleFocusListWalker(contents)
        listBox = urwid.ListBox(walker)
        return [listBox, walker]
    def getCheckBox(self,label,on_state_change=None,user_data=None):
        """gets an individual CheckBox item that executes the specified function 
            with each change of state.
        
        Arguments:
            label {str} -- Checkbox item label
        
        Keyword Arguments:
            on_state_change {list} -- a list of the following [calling object, function] (default: {None})
            user_data {list} -- list of values to be bassed to function as arguments (default: {None})
        
        Returns:
            object -- urwid.CheckBox object
            FLOW WIDGET
        """
        return urwid.CheckBox(label, 
        state=False, 
        has_mixed=False, 
        on_state_change=getattr(on_state_change[0],on_state_change[1]), 
        user_data=user_data)
    def getHeaderWidget(self,title=s.df.mainTitle,subtitle=''):
        """Generates a basic header with a title and optional subtitle
           This is meant to be used exclusively by the Headers.new() method
        
        Arguments:
            title {str} -- Title String
        
        Keyword Arguments:
            subtitle {str} -- Optional Sub-Title (default: {''})
        
        Returns:
            object -- urwid.Pile object to be used as the header's widget 
            FLOW WIDGET
        """
        self.title = self.getText('header',title,'center')
        self.subtitle = self.getText('header',subtitle,'center')
        titleMap = urwid.AttrMap(self.title, 'header')
        divMap = urwid.AttrMap(self.div, 'body')
        if subtitle:
            subtitleMap = urwid.AttrMap(self.subtitle, 'header')
            return urwid.Pile((titleMap, subtitleMap, divMap), focus_item=None)
        else:
            return urwid.Pile((titleMap, divMap), focus_item=None)
    def getFooterWidget(self,menuItems):
        """Generates a footer column row containing a list of buttons for a
            basic menu / navigation. This is meant to be used exclusively by
            the Footers.new() method
        
        Arguments:
            menuItems {list} -- List of Menu Items (each item is a list) 
                                in the following format:
                                [
                                    [Label,callback function]
                                    [Label,callback function]
                                ]       
        Returns:
            object -- urwid.menuItems object to be used as the header's widget
            FLOW WIDGET
        """
        menuList = []
        for item in menuItems:
            if len(item) == 3:
                menuList.append(
                    w.getButton(item[0],views,item[1],user_data=item[2]))
            else:
                menuList.append(
                    w.getButton(item[0],views,item[1]))
        return urwid.Columns(
            menuList,
            dividechars=1,
            focus_column=None,
            min_width=1, 
            box_columns=None)
class QuestionBox(urwid.Filler):
    def keypress(self, size, key):
        if key != 'enter':
            return super(QuestionBox, self).keypress(size, key)
        entry = self.original_widget.get_edit_text()
        self.original_widget.set_edit_text('')
        debug('%s Entry String: %s', self.original_widget, entry)
        search.new(entry)
class FilterEntry(urwid.Filler):
    def keypress(self, size, key):
        global filterEntryEditText
        if key != 'enter':
            return super(FilterEntry, self).keypress(size, key)
        filterEntryEditText = self.original_widget.get_edit_text()
        self.original_widget.set_edit_text('')
w = MyWidgets()
"""
VIEW CLASSES
"""
class Views():
    def __init__(self):
        """A collection of methods, each of which is used to activate a 
            specific view / page in the applications interface. These 
            methods are called by the footer's navigation buttons. Pages
            area generated views of various classes, the objects of which are
            stored in Views.page
        """
        self.page = {}
    def addRemoveFilters(self):
        """Page for adding / removing filters from
           current filter lists
        """
        debug('Started Views.addRemoveFilters')
    def comingSoon(self):
        debug('Started Views.comingSoon')
        comingSoonStatus = urwid.Pile([
            w.getText('body', 'Feature Still under Development. Coming Soon....', 'center')
            ])
        comingSoonFiller = urwid.Filler(comingSoonStatus, 'middle')
        comingSoonBox = self.centeredListLineBox(comingSoonFiller, '',10)
        self.show(comingSoonBox, frame,'body')
    def centeredListLineBox(self,contents, title, listHeight, **kwargs):
        filler = urwid.Filler(contents, height=listHeight)
        insideCol = w.getColRow([w.blankBox,('weight',2,filler),w.blankBox])
        debug('centeredListLineBox filler.sizing(): %s', filler.sizing())
        lineBox = w.getLineBox(insideCol,title)
        debug('centeredListLineBox listBox: %s', contents)
        outsidefiller = urwid.Filler(lineBox,height=listHeight)
        outsideCol = w.getColRow([w.blankBox,('weight',2,outsidefiller),w.blankBox])
        return urwid.Filler(outsideCol, height=listHeight)
    def chooseLogs(self):
        """Page opened on application start to select the 
           logs that will be used in searches / filters
        """
        debug('Started Views.chooseLogs')
        s.menuEnabled = False
        s.activeView = 'chooseLogs'
        logCheckBoxes = [w.div]
        for log in logFiles.availableLogs:
            logCheckBoxes.append(
                w.getCheckBox(log,
                    on_state_change=[logFiles,'update'], 
                    user_data=[log])
                    )
        logCheckBoxes.append(w.div)
        logCheckBoxes.append(w.getButton('Continue', views, 'home'))
        listBox = w.getListBox(logCheckBoxes)[0]
        chooseLogsBox = self.centeredListLineBox(
            listBox, 
            'Choose Your Logs to Search',
            len(logCheckBoxes) + 3)
        self.show(chooseLogsBox,frame,'body',focus='body')
        return chooseLogsBox
    def filterResults(self, *args):
        debug('Started Views.filterResults View: %s', args)
        s.activeView = 'filterResults'
        filters.addRemoveFilters()
    def show(self,widget,target, location, focus=''):
        target.contents.__setitem__(location, [widget, None])
        if focus:
            target.focus_position = focus
    def home(self):
        """Page displayed as Home Page for the application
        """
        if not s.menuEnabled:
            self.show(self.chooseLogs(),frame,'body',focus='body')
        s.menuEnabled = True
        s.activeView = 'home'
        debug('Started Views.home')
        homeText = w.getText('body', 'Welcome to the best Exim Search Utility ever created.\nSelect an option below to begin.','center')
        homeFiller = urwid.Filler(homeText, 'middle')
        self.show(homeFiller, frame, 'body', )
        self.show(footers.main, frame, 'footer')
        frame.focus_position = 'footer'
    def newSearch(self):
        """Page opened when starting an entirely new
           search. Not used for revising or filtering 
           previous searches
        """
        debug('Started Views.newSearch')
        s.activeView = 'newSearch'
        selectQuery = urwid.Edit('Enter your query below\n',align='center')
        selectFiller = QuestionBox(selectQuery, 'middle')
        queryBox = self.centeredListLineBox(selectFiller, 'New Search Query', 5)
        self.show(queryBox, frame, 'body')
        frame.focus_position = 'body'
    def quitLoop(self):
        """Page opened upon a request to quit, and 
            asks for confirmation of quiting
        """
        debug('Started Views.quitLoop s.activeView: %s', s.activeView)
        if s.activeView == 'chooseLogs':
            noButton = w.getButton('No', views, 'chooseLogs')
        else:
            noButton = w.getButton('No', views, 'exit')
        quitList = [
            w.div,
            w.getColRow([
                w.getButton('Yes', views, 'exit'),
                noButton]),
            w.div]
        quitBox = w.getListBox(quitList)[0]
        quitLineBox = self.centeredListLineBox(
            quitBox, 
            'Are You Sure You Want to Quit?',
            len(quitList) + 2)
        self.show(quitLineBox,frame,'body',focus='body')
    def searching(self):
        debug('Started Views.searching')
        searchingStatus = urwid.Pile([
            w.getText('body', 'Searching Logs Now. Please wait....', 'center'),
            w.searchProgress
            ])
        statusFiller = urwid.Filler(searchingStatus, 'middle')
        statusBox = self.centeredListLineBox(statusFiller, '',10)
        self.show(statusBox, frame,'body')
        loop.draw_screen()
    def showRelatedEntries(self, *args):
        debug('Started Views.showRelatedEntries: %s', args)
    def statSummary(self):
        """Page opened to display a summary of general
           stats for the email logs"""
        debug('Started Views.statSummary')
    def resultList(self,*args):
        debug('Start Views.resultList : %s', args)
        searchNo = args[0]
        s.activeView = 'resultList'
        currentResults = results.getRawResultList(searchNo)
        x = 1
        listDisplayCols = []
        for result in currentResults.resultList:
            listDisplayCols.append(w.getColRow(
                [
                    (5, w.getButton(
                        str(x),
                        self,
                        'singleEntry',
                        user_data=[currentResults.resultList.index(result), searchNo])),
                    w.getText('body',result,'left')
                ]
            ))
            x += 1
        resultListWalker = urwid.SimpleFocusListWalker(listDisplayCols)
        resultListBox = urwid.ListBox(resultListWalker)
        #resultListFiller = urwid.Filler(resultListBox)
        s.df.resultsListMenu[1] = [
            '(F)ilter Current Results',
            'filterResults',
            searchNo
            ]
        footers.update('resultsListMenu', s.df.resultsListMenu)
        self.show(resultListBox, frame,'body')
        frame.focus_position = 'body'
        self.show(footers.resultsListMenu,frame,'footer')
        return resultListBox
    def singleEntry(self, *args):
        debug('Start Views.singleEntry : %s', args)
        s.activeView = 'singleEntry'
        entryNo = args[0][0]
        searchNo = args[0][1]
        singleEntryFields = results.getSingleEntry(entryNo,searchNo)
        singleEntryFields.sort()
        singleEntryCols = [w.div]
        for field in singleEntryFields:
            singleEntryCols.append(w.getColRow([
                (30,w.getButton(field[2],search,'new',user_data=field[3], buttonMap='body')),
                ('weight',4,w.getText('body', field[3], 'left'))
            ]))
        singleEntryWalker = urwid.SimpleFocusListWalker(singleEntryCols)
        singleEntryList = urwid.ListBox(singleEntryWalker)
        #singleEntryFiller = urwid.Filler(singleEntryList)
        s.df.singleEntryMenu[2] = [
            '(B)ack To Result List',
            'resultList',
            searchNo
            ]
        footers.update('singleEntryMenu', s.df.singleEntryMenu)
        self.show(footers.singleEntryMenu, frame, 'footer')
        self.show(singleEntryList,frame,'body')
    def newSearchSummary(self,searchNo, query):
        s.activeView = 'newSearchSummary'
        if s.rl.resultOverflow:
            if query:
                summaryRows = [w.getText('header', ' for ' + query, 'center')]
            else:
                summaryRows = []
            summaryRows.extend([
                w.div,
                w.getText('bold',' There are too many Results \n Only showing the first ' 
                    + str(results.getCount(searchNo)) + 
                    ' Results \nConsider applying filters to narrow down results ', 'center'),
                w.div
            ])
            s.rl.resultOverflow = False
        else:
            if query:
                summaryRows = [w.getText('header', ' for ' + query, 'center')]
            else:
                summaryRows = []
            summaryRows = [
                w.div,
                w.getText('bold','There are ' + str(results.getCount(searchNo)) + ' results', 'center'),
                w.div
            ]
        activeFilters = results.getActiveFilterStrings()
        if activeFilters:
            summaryRows.append(w.getText('bold', 'Currently Active Filters:', 'center'))
            for activeFilter in activeFilters:
                summaryRows.append(w.getText('body', activeFilter, 'center'))
        summaryRows.append(w.div)
        summaryRows.append(w.getButton('Show Results', self,'resultList', user_data=searchNo))
        summary = urwid.SimpleFocusListWalker(summaryRows)
        summaryList = urwid.ListBox(summary)
        return views.centeredListLineBox(summaryList, 'Search Results', len(summaryRows) + 5)
    def clearFilters(self):
        filters.clear()
        currentResultList = results.getRawResultList(mostRecentSearchNo)
        debug('clearFilters mostRecentSearchNo: %s', mostRecentSearchNo)
        views.resultList(currentResultList.original_results)
    def applyFilters(self, *args):
        search.filterResults()
        frame.set_focus('body')
    def testMailer(self):
        """Page opened to allow user to send test emails"""
        debug('Started Views.testMailer')
    def exit(self):
        raise urwid.ExitMainLoop()
class Filters():
    def __init__(self):
        self.senderFilter = Filter('sendAddr')
        self.recipFilter = Filter('recipient')
        self.dateFilter = Filter('date')
        self.msgTypeFilter = Filter('msgType')
    def get(self):
        x = {
            'sendAddr': self.senderFilter.current,
            'recipient': self.recipFilter.current,
            'date': self.dateFilter.current,
            'msgType': self.msgTypeFilter.current,
        }
        return x
    def clear(self):
        self.senderFilter.current = []
        self.recipFilter.current = []
        self.dateFilter.current = []
        self.msgTypeFilter.current = []
    def getCheckBox(self,title,contents,submitLabel,submitAction):
        button = w.getButton(str(submitLabel),submitAction[0],submitAction[1])
        contents.append(button)
        checkBoxWalker = urwid.SimpleFocusListWalker(contents)
        checkBoxList = urwid.ListBox(checkBoxWalker)
        return [checkBoxWalker,
            urwid.LineBox(checkBoxList, 
            title=str(title), title_align='center')]
    def getCheckBoxItem(self,label,on_state_change=None,user_data=None):
        return urwid.CheckBox(label, state=False, has_mixed=False, on_state_change=getattr(on_state_change[0],on_state_change[1]), user_data=user_data)
    def filterDisplayList(self,filterInst,filterType):
        filterDisplayList = []
        for filter in getattr(filterInst,'current'):
            if filterType == 'date':
                filter = ','.join(filter)
            filterDisplayList.append(
                self.getCheckBoxItem(filter,
                    on_state_change=[filterInst,'markForDeletion'],
                    user_data=filter))
        checkBox = self.getCheckBox('Active Filter List', filterDisplayList,'Remove Selected Filter(s)', [filterInst,'remFilters'])
        return checkBox
    def filterSetList(self,filterInst,filterType):
        filterSetList = []
        filterInput = urwid.Edit("Enter Desired Filter\n")
        filterEntryFill = FilterEntry(filterInput)
        filterEntryAdapter = urwid.BoxAdapter(filterEntryFill, 2)
        filterSetList.append(filterEntryAdapter)
        urwid.connect_signal(filterInput, 'postchange', getattr(filterInst,'checkForAddFilterEntry'))
        button = w.getButton('Add Filter', filterInst, 'addFilters', user_data=filterInput)
        filterSetList.append(button)
        filterAddWalker = urwid.SimpleFocusListWalker(filterSetList)
        checkBoxList = urwid.ListBox(filterAddWalker)
        addBox = [filterAddWalker,
            urwid.LineBox(checkBoxList, 
            title='Add ' + filterType + ' Filter(s)', title_align='center')]
        return addBox
    def getCurrentFilters(self):
        self.filterDisplayItems = [
            [self.senderFilter,'sendAddr'],
            [self.recipFilter,'recipient'],
            [self.dateFilter,'date'],
            [self.msgTypeFilter,'msgType']]
        filterDisplays = []
        self.filterDisplayWalkers = {}
        for x in self.filterDisplayItems:
            boxitem = self.filterDisplayList(x[0],x[1])
            filterDisplays.append(boxitem[1])
            self.filterDisplayWalkers[x[1]] = boxitem[0]
        filterDisplayRow = w.getColRow(filterDisplays)
        return filterDisplayRow
    def setCurrentFilters(self):
        filterSetDisplays = []
        for x in self.filterDisplayItems:
            boxitem = self.filterSetList(x[0],x[1])
            filterSetDisplays.append(boxitem[1])
        filterSetRow = w.getColRow(filterSetDisplays)
        return filterSetRow
    def getFilterHeaders(self):
        filterHeaders = w.getColRow([
        urwid.LineBox(urwid.Filler(w.getText('body','Sender filter in\nuser@domain.com format\nMultiple senders are filtered as OR','center')), title='Sender Filters', title_align='center'),
        urwid.LineBox(urwid.Filler(w.getText('body','Recipient filter in\nuser@domain.com format\nMultiple recipients are filtered as OR','center')), title='Recipient Filters', title_align='center'),
        urwid.LineBox(urwid.Filler(w.getText('body','Date filter in\nYYYY-MM-DD format: \
            Date ranges in\n START DATE, END DATE Format\n Ex: 2019-01-01,2019-01-31\n\
            Date-time format in \n YYYY-MM-DD_HH:MM:SS.SSS','center')), title='Date Filters', title_align='center'),
        urwid.LineBox(urwid.Filler(w.getText('body','Type filter options:\nIncoming, Outgoing, Local\nMultiple Types are filtered as OR','center')), title='Type Filters', title_align='center')
        ])
        return filterHeaders
    def getHeader(self):
        headerText = w.getText('center', s.filterGuide, 'center')
        #headerFiller = urwid.Filler(headerText, height='pack')
        headerBox = urwid.LineBox(headerText, title='Add / Remove Filters', title_align='center')
        return headerBox    
    def addRemoveFilters(self):
        header = self.getHeader()
        getFilters = self.getCurrentFilters()
        setFilters = self.setCurrentFilters()
        #applyButton = w.getButton('(A)pply Filters to Current Results', search,'filterResults')
        #applyBox = urwid.LineBox(applyButton)
        filterPile = urwid.Pile([
            ('pack', header),
            #(5, filterHeaders),
            (5,setFilters),
            getFilters
        ])
        #filterPageList = urwid.Pile(filterPile)
        #self.filterFiller = urwid.Filler(self.filterPageList,valign='middle')
        s.df.filterResultsMenu[2] = [
            '(B)ack To Result List',
            'resultList',
            mostRecentSearchNo
            ]
        footers.update('filterResultsMenu', s.df.filterResultsMenu)
        debug('Active Footer for filterResultsMenu: %s',footers.filterResultsMenu.contents[2][0].original_widget.user_data)
        views.show(footers.filterResultsMenu, frame, 'footer')
        views.show(filterPile,frame,'body',focus='body')
        #frame.update('body',filterPile)
        #frame.setFocus('body')
"""
URWID FRAME CLASSES
"""
class Frame():
    def __init__(self):
        headers.new('main', s.df.mainTitle)
        footers.new('main', s.df.mainMenu)
        
        #self.bodyWidget = self.chooseLogs()
        #self.primary = urwid.Frame(
        #    self.bodyWidget, 
        #    header=self.headerWidget, 
        #    footer=self.footerWidget, 
        #    focus_part='body'
        #    )
        #def update(self,section,newContents):
        #    self.primary.contents.__setitem__('body', [newContents, None])
        #def setFocus(self, newFocus):
        #    self.primary.focus_position = newFocus
class Footers():
    def __init__(self):
        """This class is used to create footer nav objects
           which are stored in the Footers.widgets dictionary
           keyed by footer name.
        """
        self.widgets = {}
        self.main = w.getFooterWidget(s.df.mainMenu)
        self.resultsListMenu = w.getFooterWidget(s.df.resultsListMenu)
        self.singleEntryMenu = w.getFooterWidget(s.df.singleEntryMenu)
        self.filterResultsMenu = w.getFooterWidget(s.df.filterResultsMenu)
    def new(self,name,menuItems):
        """Creates a new footerWidget using a list of
           menuItems, and a name for the footer
        
        Arguments:
            name {str} -- A unique name for the new footer
            menuItems {list} -- List of Menu Items (each item is a list) 
                                in the following format:
                                [
                                    [Label,callback function]
                                    [Label,callback function]
                                ]
        
        Raises:
            Exception: Raised if a footer with the given name already exists
        """
        footerWidget = w.getFooterWidget(menuItems)
        #if not name in self.widgets.keys():
        #    self.widgets[name] = footerWidget
        #else:
        #    raise Exception('A footer by the name of {} already exists'.format(name))
        if hasattr(self, name):
            raise Exception('A footer by the name of {} already exists'.format(name))
        else:
            setattr(self,name,footerWidget)
    def update(self,name,menuItems):
        if hasattr(self, name):
            newWidget = w.getFooterWidget(menuItems)
            setattr(self,name, newWidget)
        else:
            raise Exception('A footer by the name of {} does not exist'.format(name))
class Headers():
    def __init__(self):
        """This class is used to create header objects
           which are stored in the Headers.widgets dictionary
           keyed by header name.
        """
        
        self.widgets = {}
        self.main = w.getHeaderWidget(subtitle='If you can do better, then do it')
        self.resultList = w.getHeaderWidget(subtitle='')
    def new(self,name,title=s.df.mainTitle,subtitle=''):
        """Creates a new Header widget object based on the
           provided name, title, and optional sub-title. Uses 
           the main application title as default.
        
        Arguments:
            name {str} -- unique name for header
        
        Keyword Arguments:
            title {str} -- String to be displayed as the Main Title. 
                           Defaults to the mainTitle stored in s.df.mainTitle (default: {s.df.mainTitle})
            subtitle {str} -- Optional sub-title string (default: {''})
        
        Raises:
            Exception: Raised if a header with the given name already exists
        """
        headerWidget = w.getHeaderWidget(title,subtitle=subtitle)
        #if not name in self.widgets.keys():
        #    self.widgets
        #    self.widgets[name] = headerWidget
        #else:
        #    raise Exception('A Header by the name of {} already exists'.format(name))
        if hasattr(self, name):
            raise Exception('A footer by the name of {} already exists'.format(name))
        else:
            setattr(self,name,headerWidget)

"""
DATA / QUERY PROCESSING CLASSES
"""

class LogFiles():
    def __init__(self):
        """This Class handles obtaining and updating
           lists of log files including the currently
           available logs, and the logss currently 
           selected for searching.
        """
        self.availableLogs = self.getListofAvailableLogs()
        self.sortLogs(self.availableLogs)
        self.selectedLogs = []
    def sortLogs(self, logsToBeSorted):
        """Sorts list of log files with the primary file first
            and the gzipped files next, sorted by date in decending
            order.
        
        Arguments:
            logsToBeSorted {list} -- the logfile list that will be sorted
        """
        logsToBeSorted.sort(reverse=True)
        for log in logsToBeSorted:
            if log == s.lf.mainLogPath:
                logsToBeSorted.insert(0, logsToBeSorted.pop(logsToBeSorted.index(s.lf.mainLogPath)))
    def update(self, *args):
        """updates an item in the selectedLogs list by either adding or removing the item
        
        Arguments:
            itemsToUpdate {list} -- list of items to update. if only updating one item, it must still be contained in a list
        
        Raises:
            TypeError: raised if itemsToUpdate is not a list
        
        Returns:
            dict -- Dictionary of items added or removed in this call.
        """
        debug('LogFiles update args: %s', type(args[0]))
        updates = {'removed':[],'added':[]}
        if type(args[0]) == urwid.wimp.CheckBox:
            itemsToUpdate = args[2]
            isLogSelected = args[1]
            
            if type(itemsToUpdate) != list:
                raise TypeError('{} provided where list is required', type(itemsToUpdate))   
            if isLogSelected:
                for x in itemsToUpdate:
                    if x not in self.selectedLogs:
                        updates['added'].append(x)
                        self.selectedLogs.append(x)
                        debug('LogFiles update self.selectedLogs after append: %s', self.selectedLogs)
                        self.sortLogs(self.selectedLogs)
                    else:
                        warning('LogFiles.update: Failed to add log %s : Log already on selectedLogs list', x)
            else:
                for x in itemsToUpdate:
                    if x in self.selectedLogs:
                        updates['removed'].append(x)
                        self.selectedLogs.remove(x)
                        debug('LogFiles update self.selectedLogs after remove: %s', self.selectedLogs)
                        self.sortLogs(self.selectedLogs)
                    else:
                        warning('LogFiles.update: Failed to remove log %s : Log is not on selectedLogs list', x)
        #for x in itemsToUpdate:
        #    if x in self.selectedLogs:
        #        updates['removed'].append(x)
        #        self.selectedLogs.remove(x)
        #        self.sortLogs(self.selectedLogs)
        #    else:
        #        self.selectedLogs.append(x)
        #        updates['added'].append(x)
        #        self.sortLogs(self.selectedLogs)
        return updates
    def getListofAvailableLogs(self):
        """Obtains list of log files available in the 
           directory set in LogFileSettings.dir
        
        Returns:
            list -- list of available log files
        """
        logdir = s.lf.dir
        loglist = []
        for file in os.listdir(logdir):
            if file.startswith("exim_mainlog"):
                loglist.append(os.path.join(logdir, file))
        return loglist
class Entries():
    def __init__(self, fullEntryText):
        """This class is used to create single-view Entry Objects
        """
        self.msgType = []
        self.date = []
        self.time = []
        self.sendAddr = []
        self.recipient = []
        self.fullEntryText = fullEntryText
        #debug('Init Entries: %s', self.fullEntryText)
        try:
            shlex.split(self.fullEntryText)
        except:
            m = self.fullEntryText.split()
            self.parseError = [15, 'Parsing Error: ', str(Exception)]
            x = 0
            while x <= len(m):
                if x == 0:
                    self.date = [10, 'Date: ', m[x]]
                if x == 1:
                    self.time = [11, 'Time: ', m[x]]
                if x == 2:
                    self.pid = [12, 'Process ID: ', m[x]]
                if x == 3:
                    self.id = [13, 'Message ID: ', m[x]]
                x += 1
            self.fullEntryText = [14, 'Full Entry: ', self.fullEntryText]        
        else:
            m = shlex.split(self.fullEntryText)
            x = 0
            while x < len(m):
                if x == 0:
                    self.date = [10, 'Date: ', m[x]]
                if x == 1:
                    self.time = [11, 'Time: ', m[x]]
                if x == 2:
                    self.pid = [12, 'Process ID: ', m[x]]
                if x == 3:
                    self.id = [13, 'Message ID: ', m[x]]
                if x == 4:
                    if len(m[x]) == 2:
                        self.entryType = [22, 'Entry Type Symbol: ', m[x]]
                #debug('parseEntries self.fullEntryText: %s', self.fullEntryText)
                if 'H=' in m[x]:
                    if len(m) > x + 1:
                        if m[x+1][0] == '(':
                            self.host = [16,'Host: ', m[x][2:] + ' ' + m[x+1]]
                            self.hostIp = [17, 'Host IP: ', m[x+2].split(':')[0]]
                            if s.hostname in self.host:
                                self.msgType = [15, 'Type: ', 'relay']
                        else:
                            self.host = [16, 'Host: ', m[x][2:]]
                            self.hostIp = [17, 'Host IP: ', m[x+1].split(':')[0]]
                            if s.hostname in self.host:
                                self.msgType = [15, 'Type: ', 'relay']
                if m[x] == 'SMTP':
                    self.smtpError = [22, 'Failure Message: ', " ".join(m[x:])]
                if 'S=' in m[x] and m[x][0] != 'M':
                    self.size = [22, 'Size: ', m[x][2:]]
                if 'I=' in m[x] and m[x][0] != 'S':
                    self.interface = [22, 'Receiving Interface: ', m[x].split(':')[0][2:]]
                if 'R=' in m[x]:
                    self.bounceId = [22, 'Bounce ID: ', m[x][2:]]
                if 'U=' in m[x]:
                    self.mta = [22, 'MTA / User: ', m[x][2:]]
                if 'id=' in m[x]:
                    self.remoteId = [22, 'Sending Server Message ID: ', m[x][3:]]
                if 'F=<' in m[x]:
                    self.sendAddr = [18, 'Sender: ', m[x][2:]]
                    if not self.sendAddr[1] == '<>':
                        self.sendAddr = [18, 'Sender: ', m[x][3:-1]]
                    self.fr = self.sendAddr
                if 'C=' in m[x]:
                    self.delStatus = [22, 'Delivery Status: ', m[x][2:]]
                if 'QT=' in m[x]:
                    self.timeInQueue = [22, 'Time Spent in Queue: ', m[x][3:]]
                if 'DT=' in m[x]:
                    self.deliveryTime = [22, 'Time Spent being Delivered: ', m[x][3:]]
                if 'RT=' in m[x]:
                    self.deliveryTime = [22, 'Time Spent being Delivered: ', m[x][3:]]
                if ' <= ' in fullEntryText:
                    self.msgType = [15, 'Message Type: ', 'incoming']
                    if 'A=' in m[x]:
                        self.smtpAuth = [22, 'Auth. Method: ', m[x][2:]]
                        if 'dovecot' in m[x]:
                            self.msgType = [15, 'Type: ', 'relay']
                    if x == 5:
                        self.sendAddr = [18, 'Sender', m[x]]
                    if 'P=' in m[x]:
                        self.protocol = [22, 'Protocol: ', m[x][2:]]
                        if 'local' in self.protocol[1]:
                            self.msgtype = [15, 'Type: ', 'local']
                    if 'T=' in m[x] and m[x][0] != 'R':
                        self.topic = [21, 'Subject: ', m[x][2:]]
                    if m[x] == 'from':
                        if len(m) > x +1:
                            if m[x+1] == '<>':
                                self.fr = [18, 'Sender: ', m[x+1]]
                                self.msgType = [15, 'Type: ', 'bounce']
                            else:
                                self.fr = [18, 'Sender: ', m[x+1][1:-1]]
                    if m[x] == 'for':
                        self.receipient = [19, 'Recipient: ', m[x+1]]
                    x += 1
                else:
                    if x == 5:
                        if '@' in m[x]:
                            self.receipient = [19, 'Recipient: ', m[x]]
                        else:
                            if len(m) > x + 1:
                                if '@' in m[x + 1]:
                                    self.receipient = [19, 'Recipient: ', m[x] + m[x+1]]
                    if 'P=' in m[x]:
                        self.returnPath = [20, 'Return Path: ', m[x][3:-1]]
                    if 'T=' in m[x] and m[x][0] != 'D' and m[x][0] != 'Q':
                        self.mta = [22, 'MTA: ', m[x][2:]]
                        if 'dovecot' in self.mta[1]:
                            self.msgType = [15, 'Type: ', 'local']
                    if ' => ' in fullEntryText:
                        self.msgType = [15, 'Message Type: ', 'outgoing']
                    x += 1
            
            self.fullEntryText = [14, 'Full Entry: ', self.fullEntryText]
    def getTimeOrd(self):
        x = str(self.date[2]) + '_' + str(self.time[2])
        x = datetime.strptime(x, s.dt.logDateTimeFormat)
        return x.toordinal()
    def getEntryFields(self):

        fieldList = [a for a in dir(self) if not a.startswith('__') and not callable(getattr(self,a))]
        fields = []
        for field in fieldList:
            x = getattr(self,field)
            if x:
                fields.append([
                    x[0],
                    field,
                    x[1],
                    x[2]
                ])
        return fields
class ResultLists():
    def __init__(self,listNumber,resultType,query,resultContents,count,original_results='',isFiltered=False, filters_applied=[]):
        self.listNumber = listNumber
        self.isFiltered = isFiltered
        self.query = query
        self.original_results = original_results
        self.filteredApplied = filters_applied
        self.count = count
        if resultType == 'logResults':
            self.resultList = resultContents
            self.parseEntries()
        else:
            resultContents.sort(key=lambda x: str(x.getTimeOrd()), reverse=False)
            i = 0
            self.resultList = []
            for entry in resultContents:
                name = 'entry-' + str(i)
                setattr(self,name,entry)
                self.resultList.append(entry.fullEntryText[2])
                i += 1
        debug('List of Attr in new ResultList: %s', dir(self))
    def parseEntries(self):
        i = 0
        for result in self.resultList:
            name = 'entry-' + str(i)
            if hasattr(self, name):
                raise Exception('Entry number {} has already been parsed'.format(name))
            else:
                setattr(self,name,Entries(result))
            i += 1
    def getListOfEntries(self):
        listOfEntries = []
        for attr in dir(self):
            if 'entry-' in attr:
                listOfEntries.append(getattr(self,attr))
        return listOfEntries
class Results():
    def __init__(self):
        self.currentFilters = {
            'Type': [],
            'Sender': [],
            'Recipient': [],
            'Date': [],
        }
        self.entries = {}
        self.filterEntryEditText = ''
    def new(self, name, resultType,
        query, resultContents, original_results='',
        isFiltered=False,filters_applied=[]):
        """Class of Result Lists
        
        Arguments:
            name {str} -- name of this result instance
            resultType {str} -- the origin source of this result list (logResults,FilteredResults, etc)
            resultContents {list} -- a list of results. each list item must be str
        
        Raises:
            TypeError: raised if resultContents is not a list
            TypeError: raised if the first item in resultContents is not a str
        """
        debug('New Result List created: %s', name)
        if resultType == 'logResults':
            if type(resultContents) != list:
                raise TypeError('{} provided :: resultContents must be a list of strings'.format(type(resultContents)))
            try:
                type(resultContents[0])
            except:
                pass
            else:
                if type(resultContents[0]) != str:
                    raise TypeError('{} provided :: resultContents must be a list of strings'.format(type(resultContents[0])))
            count = len(resultContents)
            if hasattr(self, name):
                raise Exception('A result list by the name of {} already exists'.format(name))
            else:
                setattr(self,name,ResultLists(
                    name, resultType, query,
                    resultContents, count,
                    original_results,
                    isFiltered, filters_applied))
        else:
            count = len(resultContents)
            setattr(self,name,ResultLists(
                name, resultType, query,
                resultContents, count,
                original_results,
                isFiltered, filters_applied))
    def getSingleEntry(self,entryNo,searchNo):
        debug('Started Results.getSingleEntry: %s, %s', entryNo, searchNo)
        entryId = 'entry-' + str(entryNo)
        resultList = getattr(self, searchNo)
        debug('resultList : %s', resultList)
        entry = getattr(resultList, entryId)
        return entry.getEntryFields()
    def getActiveFilterStrings(self):
        activeFilterStringList = []
        for filterType, activeFilter in self.currentFilters.items():
            if activeFilter:
                activeFilterStringList.append('Message ' + filterType + ' = ' + ', '.join(activeFilter))
        return activeFilterStringList
    def getCount(self,searchNo):
        resultList = getattr(self,searchNo)
        return resultList.count
    def getRawResultList(self, searchNo):
        return getattr(self,searchNo)
    def checkForAddFilterEntry(self, *args):
        debug('Results.checkForAddFilterEntry args: %s', args)
        #if self.filterEntryEditText:
        #    newFilter = self.filterEntryEditText
        #    self.filterEntryEditText = ''
        #    self.currentFilters[filterType].append(newFilter)
    def addFilters(self, *args):
        debug('Results.addFilters args: %s', args)
class Filter():
    def __init__(self,filterType):
        self.current = []
        self.filterType = filterType
        self.markedForDeletion = []
        self.markForAddition = []
    def checkForAddFilterEntry(self, *args):
        global filterEntryEditText
        if filterEntryEditText:
            debug('Filter.checkForAddFilterEntry newFilter: %s', filterEntryEditText)
            newFilter = filterEntryEditText
            filterEntryEditText = ''
            self.addFilters(newFilter)
    def markForDeletion(self,*args):
        logging.info
        if args[2] in self.markedForDeletion:
            self.markedForDeletion.remove(args[2])
        else:
            self.markedForDeletion.append(args[2])
    def remFilters(self):
        for item in self.markedForDeletion:
            if self.filterType == 'Date':
                filterStringArray = item.split(',')
                if filterStringArray in self.current:
                    self.current.remove(filterStringArray)
            else:
                self.current.remove(item)
            currentFilterWalker = filters.filterDisplayWalkers[self.filterType]
            for filter in currentFilterWalker:
                try:
                    if item in filter.label:
                        currentFilterWalker.remove(filter)
                        self.markedForDeletion = []
                except:
                    pass
    def addFilters(self, *args):
        if type(args[0]) == str:
            newFilter = args[0]
        else:
            newFilter = args[0].get_edit_text()
            args[0].set_edit_text('')
        addFilterTrue = True
        if self.filterType == 'date':
            if ',' in newFilter:
                newFilter = newFilter.split(',')
            else:
                newFilter = [newFilter]
            dateTimeFilter = []
            for entry in newFilter:
                dateString = s.dt.stringToDate(entry)
                if not dateString:
                    addFilterTrue = False
                else:
                    dateTimeObject = s.dt.stringToDate(entry)
                    dateTimeFilter.append(datetime.strftime(dateTimeObject.date(), s.dt.logDateFormat))
        if addFilterTrue:
            if newFilter not in self.current:
                if self.filterType == 'date':
                    if dateTimeFilter not in self.current:
                        self.current.append(dateTimeFilter)
                        newFilter = ','.join(newFilter)
                        newFilterCheckBoxItem = filters.getCheckBoxItem(newFilter,
                            on_state_change=[self,'markForDeletion'],
                            user_data=newFilter)
                else:
                    self.current.append([newFilter])
                newFilterCheckBoxItem = filters.getCheckBoxItem(newFilter,
                    on_state_change=[self,'markForDeletion'],
                    user_data=newFilter)
                currentFilterWalker = filters.filterDisplayWalkers[self.filterType]
                if newFilterCheckBoxItem not in currentFilterWalker:
                    currentFilterWalker.insert(-1, newFilterCheckBoxItem)

class Search():
    def new(self, query):
        global mostRecentSearchNo
        s.rl.resultOverflow = False
        debug('New Search Object with query: %s', query)
        updateThread = threading.Thread(target=views.searching())
        updateThread.start()
        updateThread.join()
        searchNumber = self.incrementCounter()
        mostRecentSearchNo = searchNumber
        results.new(searchNumber, 'logResults', query, self.queryLogs(query),original_results=searchNumber)
        views.show(views.newSearchSummary(searchNumber,query), frame, 'body')
    def incrementCounter(self):
        global searchCounter
        searchCounterStr = 'search' + str(searchCounter).zfill(3)
        searchCounter += 1
        return searchCounterStr
    def filterResults(self,*args):
        global mostRecentSearchNo
        debug("Start Search.filterResults: %s", filters.get())
        currentSearchNo = 'search' + str(searchCounter - 1).zfill(3)
        filteredSearchNo = self.incrementCounter()
        mostRecentSearchNo = filteredSearchNo
        currentResultList = results.getRawResultList(currentSearchNo)
        self.currentFilters = filters.get()
        filteredResults = []
        originalQuery = currentResultList.query
        #originalInput = currentResultList
        entryList = currentResultList.getListOfEntries()
        entryList.sort()
        debug('filterResults entryList: %s', entryList)
        filteredResults = self.filterInput('sendAddr', input=entryList)
        filteredResults = self.filterInput('recipient', input=filteredResults)
        filteredResults = self.filterInput('date', input=filteredResults)
        filteredResults = self.filterInput('msgType', input=filteredResults)
        debug("Filtered Results Count: %s", len(filteredResults))
        if currentResultList.isFiltered:
            original_results = currentResultList.original_results
        else:
            original_results = currentSearchNo
        results.new(filteredSearchNo, 'filteredResults', originalQuery, filteredResults, original_results=original_results, isFiltered=True)
        views.show(views.newSearchSummary(filteredSearchNo,originalQuery), frame, 'body')
    def filterInput(self, filterType, input=None):
        if not self.currentFilters[filterType]:
            return input
        else:
            filteredResults = []
            filterSet = self.currentFilters[filterType]
            #debug('filterInput filters: %s', filterSet)
            for item in input[:]:
                x = getattr(item,filterType)
                #debug('filterInput x.filterType: %s', x)
                for filters in filterSet:
                    for filter in filters:
                        #debug('filterInput filter: %s', filter)
                        if filter in x:
                            filteredResults.append(item)
            return filteredResults
    def formatFilterStr(self, filterType, filters):
        formattedFilter = []
        self.filterExclusions = []
        logging.info('formatFilterStr filters: %s', filters)
        if filterType == 'Sender':
            for filterString in filters:
                formattedFilter.append(' from <' + filterString + '>')
                formattedFilter.append(' F=<' + filterString + '>')
            return formattedFilter
        if filterType == 'Recipient':
            formattedFilter = []
            for filterString in filters:
                formattedFilter.append(' for ' + filterString)
                formattedFilter.append(' => ' + filterString)
            logging.info('formatFilterStr formattedFilter: %s', formattedFilter)
            return formattedFilter
        if filterType == 'Type':
            for filter in filters:
                if filter.lower() == 'incoming':
                    formattedFilter.append(' <= ')
                    self.filterExclusions.extend([
                        'A=dovecot',
                        'P=local',
                        'H=(' + s.hostname + ')'
                        ])
                if filter.lower() == 'outgoing':
                    formattedFilter.append(' => ')
                    self.filterExclusions.extend([
                        ' T=dovecot'
                        ])
                if filter.lower() == 'local':
                    formattedFilter.append('P=local')
            return formattedFilter
        if filterType == 'Date':
            for filterString in filters:
                debug('Date Formatting filterString in filters: %s', filterString)
                if len(filterString) == 1:
                    formattedFilter.append(filterString[0])
                if len(filterString) == 2:
                    d = DateRange()
                    formattedFilter.extend(d.getDateRangeArray(filterString))
                    debug('Date Formatting formattedFilter: %s', formattedFilter)
            return formattedFilter
        else:
            return filters            
    def queryLogs(self,query):
        starttime = datetime.now()
        #debug(":filterLogs :: Current Thread:: %s", threading.current_thread().getName())
        #debug('filterLogs filter: %s', query)
        #for log in self.selectedLogs:
        logPoolArgs = []
        for log in logFiles.selectedLogs:
            logPoolArgs.append([query,log])
        queryLogProcessPool = ThreadPool()
        searchedLogs = queryLogProcessPool.map(queryLogProcess, logPoolArgs)
        results = []
        for resultList in searchedLogs:
            results.extend(resultList)
        logging.info('QT = %s : filteredLog Pool Result Count: %s',datetime.now() - starttime, len(results))
        return results
class DateRange():
    def getDateRangeArray(self,dateRangeStrings):
        dateRangeArray = []
        startDate = datetime.strptime(dateRangeStrings[0], s.dt.logDateFormat)
        endDate = datetime.strptime(dateRangeStrings[1], s.dt.logDateFormat)
        for single_date in self.dateRange(startDate, endDate):
            dateRangeArray.append(single_date.strftime(s.dt.logDateFormat))
        return dateRangeArray
    def dateRange(self,start_date, end_date):
        for n in range(int ((end_date - start_date).days)):
            yield start_date + timedelta(n)
def queryLogProcess(poolArgs):
    os.nice(20)
    query,log = poolArgs
    #debug('Log = %s, filters = %s', log, query)
    rawEntries = []
    if log[-2:] != 'gz':
        with open(log,mode='r') as f:
            for i, line in enumerate(f):
                pass
            #debug('Lines in file: %s', i)
            totalLines = i
        
        #logPoolArgs = []
        with open(log,mode='r') as p:
            for i, line in enumerate(p):
                if len(rawEntries) == 10000:
                    s.rl.resultOverflow = True
                    debug('ResultOverflow = True')
                    break
                if query in line:
                    if line not in rawEntries:
                        rawEntries.append(line)
                if i % 1000000 == 0:
                    percent = float(i) / float(totalLines)
                    completion = int(percent * 100)
                    #debug('Total Lines in file: %s', totalLines)
                    #debug('Current Line Percent: %s', completion)
                    w.searchProgress.set_completion(completion)
                    loop.draw_screen()
    else:
        with gzip.open(log,mode='r') as f:
            for i, line in enumerate(f):
                pass
            #debug('Lines in file: %s', i)
            totalLines = i
        with gzip.open(log,mode='r') as f:
            for i, line in enumerate(f):
                if len(rawEntries) == 10000:
                    s.rl.resultOverflow = True
                    debug('ResultOverflow = True')
                    break
                if query in line:
                    if line not in rawEntries:
                        rawEntries.append(line)
                if i % 1000000 == 0:
                    percent = float(i) / float(totalLines)
                    completion = int(percent * 100)
                    #debug('Total Lines in file: %s', totalLines)
                    #debug('Current Line Percent: %s', completion)
                    w.searchProgress.set_completion(completion)
                    loop.draw_screen()
    return rawEntries
if __name__ == '__main__':
    debug('Application Start')

    #Initialize & retrieve LogFiles list
    logFiles = LogFiles()

    #Initialize Frame
    frame = urwid.Frame(urwid.Filler(w.getText('body','Loading...Please Wait','center')))

    #Initialize views,headers,footers
    views = Views()
    headers = Headers()
    footers = Footers()

    #Initialize Results Object
    results = Results()
    #Initialize Filter Object
    filters = Filters()
    #Initialize Search Object
    search = Search()

    #Get Initial Frame Sections
    frame.contents.__setitem__('header', [headers.main, None])
    frame.contents.__setitem__('footer', [footers.main, None])
    frame.contents.__setitem__('body', [views.chooseLogs(), None])

    loop = urwid.MainLoop(frame, s.df.palette, unhandled_input=s.unhandled_input)
    loop.run()