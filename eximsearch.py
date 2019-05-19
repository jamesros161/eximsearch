#!/usr/bin/python
#/opt/imh-python/bin/python
import urwid, datetime, os, subprocess, sys, json, re, shlex, gzip, time, logging, collections, socket, threading
from multiprocessing import Pool, Queue, current_process
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
    def unhandled_input(self,key):
        if type(key) == str:
            if key in ('q', 'N'):   
                raise urwid.ExitMainLoop
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
class DateTimeSettings():
    def __init__(self):
        """Settings for DateTime functions / formatting
        """
        self.logDateFormat ="%Y-%m-%d"
        self.displayDateFormat = "%m-%d-%Y"
        self.stringToDateFormat = "%Y-%m-%d"
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
                'statSummary'],
            ['(T)est Mailer',
                'testMailer'],
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
    def getButton(self, thisLabel, callingObject, callback, user_data=None):
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
        buttonMap = urwid.AttrMap(button, 'bold', focus_map='header')
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
        titleMap = urwid.AttrMap(self.getText('header',title,'center'), 'header')
        divMap = urwid.AttrMap(self.div, 'body')
        if subtitle:
            subtitleMap = urwid.AttrMap(self.getText('header',subtitle,'center'), 'header')
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
            menuList.append(
                w.getButton(item[0],views,item[1]))
        return urwid.Columns(
            menuList,
            dividechars=1,
            focus_column=None,
            min_width=1, 
            box_columns=None)
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
        self. page = {}
    def addRemoveFilters(self):
        """Page for adding / removing filters from
           current filter lists
        """
        debug('Started Views.addRemoveFilters')
    def centeredListLineBox(self,contents, title, listHeight, **kwargs):
        filler = urwid.Filler(contents, height=listHeight)
        insideCol = w.getColRow([w.blankBox,('weight',2,filler),w.blankBox])
        debug('centeredListLineBox filler.sizing(): %s', filler.sizing())
        lineBox = w.getLineBox(insideCol,'Choose Your Logs to Search')
        debug('centeredListLineBox listBox: %s', contents)
        outsidefiller = urwid.Filler(lineBox,height=listHeight)
        outsideCol = w.getColRow([w.blankBox,('weight',2,outsidefiller),w.blankBox])
        return urwid.Filler(outsideCol, height=listHeight)
    def chooseLogs(self):
        """Page opened on application start to select the 
           logs that will be used in searches / filters
        """
        debug('Started Views.chooseLogs')
        logCheckBoxes = [w.div]
        for log in logFiles.availableLogs:
            logCheckBoxes.append(
                w.getCheckBox(log,
                    on_state_change=[logFiles,'update'], 
                    user_data=[log])
                    )
        listBox = w.getListBox(logCheckBoxes)[0]
        return self.centeredListLineBox(
            listBox, 
            'Choose Your Logs to Search',
            len(logCheckBoxes) + 3)
        #height = len(logFiles.availableLogs) + 3
        #filler = urwid.Filler(listBox, height=height)
        #insideCol = w.getColRow([w.blankBox,('weight',2,filler),w.blankBox])
        #debug('chooseLogs filler.sizing(): %s', filler.sizing())
        #lineBox = w.getLineBox(insideCol,'Choose Your Logs to Search')
        #debug('chooseLogs listBox: %s', listBox)
        #outsidefiller = urwid.Filler(lineBox,height=height)
        #outsideCol = w.getColRow([w.blankBox,('weight',2,outsidefiller),w.blankBox])
        #filler = urwid.Filler(outsideCol, height=height)
        #return outsideCol
    def show(self,widget,location):
        self.primary.contents.__setitem__('body', [newContents, None])

    def home(self):
        """Page displayed as Home Page for the application
        """
        debug('Started Views.home')
    def newSearch(self):
        """Page opened when starting an entirely new
           search. Not used for revising or filtering 
           previous searches
        """
        debug('Started Views.newSearch')
    def quitLoop(self):
        """Page opened upon a request to quit, and 
            asks for confirmation of quiting
        """
        debug('Started Views.quitLoop')
    def statSummary(self):
        """Page opened to display a summary of general
           stats for the email logs"""
        debug('Started Views.statSummary')
    def testMailer(self):
        """Page opened to allow user to send test emails"""
        debug('Started Views.testMailer')

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
class Headers():
    def __init__(self):
        """This class is used to create header objects
           which are stored in the Headers.widgets dictionary
           keyed by header name.
        """
        
        self.widgets = {}
        self.main = w.getHeaderWidget()
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
class Results():
    def __init__(self,name,resultType,resultContents):
        """Class of Result Lists
        
        Arguments:
            name {str} -- name of this result instance
            resultType {str} -- the origin source of this result list (logResults,FilteredResults, etc)
            resultContents {list} -- a list of results. each list item must be str
        
        Raises:
            TypeError: raised if resultContents is not a list
            TypeError: raised if the first item in resultContents is not a str
        """
        if type(resultContents) != list:
            raise TypeError('{} provided :: resultContnents must be a list of strings'.format(type(resultContents)))
        if type(resultContents[0]) != str:
            raise TypeError('{} provided :: resultContnents must be a list of strings'.format(type(resultContents[0])))
        self.resultType = resultType
        self.list = resultContents
        self.count = len(self.list)
        self.name = name
    def update(self,itemsToUpdate):
        """updates an item in the result list by either adding or removing the item
        
        Arguments:
            itemsToUpdate {list} -- list of items to update. if only updating one item, it must still be contained in a list
        
        Raises:
            TypeError: raised if itemsToUpdate is not a list
        
        Returns:
            dict -- Dictionary of items added or removed in this call.
        """
        if type(itemsToUpdate) != list:
            raise TypeError('{} provided where list is required', type(itemsToUpdate))
        updates = {'removed':[],'added':[]}
        listToBeUpdated = self.list
        for x in itemsToUpdate:
            if x in listToBeUpdated:
                updates['removed'].append(x)
                self.list.remove(x)
            else:
                self.list.append(x)
                updates['added'].append(x)
        return updates

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

    #Get Initial Frame Sections
    frame.contents.__setitem__('header', [headers.main, None])
    frame.contents.__setitem__('footer', [footers.main, None])
    frame.contents.__setitem__('body', [views.chooseLogs(), None])

    loop = urwid.MainLoop(frame, s.df.palette, unhandled_input=s.unhandled_input)
    loop.run()