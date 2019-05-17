#!/usr/bin/python
#/opt/imh-python/bin/python
import urwid, datetime, os, subprocess, sys, json, re, shlex, gzip, time, logging, collections, socket, threading
from datetime import datetime, timedelta

logging.basicConfig(filename='log',filemode='a', level=logging.INFO)
logging.log = logging.info

entryList = {}
logfiles = {}
results = {}
pid = ''
query = ['','']
newQuery = ['','']
frame = ''
s = ''
w = ''
queryFilter = ''
filterEntryEditText = ''
newSearchSource = ''
starttime = ''

class GlobalSettings():
    def __init__(self):
        self.rl = ResultListSettings()
        self.datetimeformat = "%Y-%m-%d_%H:%M:%S.%f"
        self.logDateTimeFormat = "%Y-%m-%d_%H:%M:%S.%f"
        self.logDateFormat ="%Y-%m-%d"
        self.displayDateTimeFormat = "%m-%d-%Y_%H:%M:%S"
        self.displayDateFormat = "%m-%d-%Y"
        self.stringToDateFormat = "%Y-%m-%d"
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
class ResultListSettings():
    def __init__(self):
        self.ButtonColWidth = 7
        self.divChars = 1
class ButtonLabel(urwid.SelectableIcon):
    def __init__(self, text):
        curs_pos = len(text) + 1 
        urwid.SelectableIcon.__init__(self, 
            text, cursor_position=curs_pos)
class FixedButton(urwid.Button):
    _selectable = True
    signals = ["click"]
    def __init__(self, thisLabel, on_press=None, user_data=None):
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
        # we can set the label at run time, if necessary
        self._label.set_text(str(new_label))

    def mouse_event(self, size, event, button, col, row, focus):
        """
        handle any mouse events here
        and emit the click signal along with any data 
        """
        pass
    def disable(self):
        _selectable = False
    def enable(self):
        _selectable = True
class MyWidgets():
    def getButton(self, thisLabel, callingObject, callback, user_data=None):
        button = FixedButton(str(thisLabel),
        on_press=getattr(callingObject, callback),
        user_data=user_data)
        button._label.align = 'center'
        buttonMap = urwid.AttrMap(button, 'bold', focus_map='header')
        return buttonMap
    def getText(self,format,textString, alignment):
        return urwid.Text((format, textString), align=alignment, wrap='space')
    def getColRow(self,items):
        return urwid.Columns(items,
            dividechars=s.divChars,
            focus_column=None,
            min_width=1,
            box_columns=None)
    def getLineBox(self,contents,title):
        contentList = urwid.SimpleFocusListWalker(contents)
        return urwid.LineBox(contentList, title=str(title), title_align='center')
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
class GuiFrame():
    def __init__(self):
        self.palette = [('header', 'black', 'light gray'),
            ('footer', 'black', 'light gray'),
            ('body', 'white', 'default'),
            ('bold', 'dark green, bold' , 'black')]
        
        self.headerWidget = HeaderFrame('Exim Search Utility').widget
        self.footer = MainMenu([
            ['(N)ew Search','getQuery'],
            ['Add / Remove (F)ilters', 'getFilters'],
            ['(S)tats Summary', 'showStatSummary'],
            ['(T)est Mailer', 'testMailer'],
            ['(Q)uit','quitLoop']
        ])

        self.footerWidget = self.footer.widget

        self.bodyWidget = self.chooseLogs()
        
        self.primary = urwid.Frame(
            self.bodyWidget, 
            header=self.headerWidget, 
            footer=self.footerWidget, 
            focus_part='body'
            )
    def chooseLogs(self):
        global logfiles
        s.menuEnabled = False
        self.logFiles = LogFiles()
        logSelector = []
        if os.path.isfile('/var/log/exim_mainlog'):
            logfiles['/var/log/exim_mainlog'] = False
            checkBox = urwid.CheckBox('/var/log/exim_mainlog', state=False, has_mixed=False, on_state_change=toggleLogSelector, user_data='/var/log/exim_mainlog')
            logSelector = [checkBox]
        for file in os.listdir("/var/log/"):
            if file.startswith("exim_mainlog-") and file.endswith(".gz"):
                logfiles[os.path.join('/var/log/', file)] = False
        logFileList = []
        for logFile in logfiles.keys():
            if 'gz' in logFile:
                logFileList.append(logFile) 
        logFileList.sort(reverse=True)
        for logFile in logFileList:
            checkBox = urwid.CheckBox(logFile, state=False, has_mixed=False, on_state_change=toggleLogSelector, user_data=logFile)
            logSelector.append(checkBox)
        self.beginParsingButton = w.getButton('Parse Selected Logs',self.logFiles,'setLogFiles')
        logSelector.append(self.beginParsingButton)
        logSelectorFilled = []
        for item in logSelector:
           logSelectorFilled.append(urwid.Filler(item,height=1,))
        logSelectorFilled = urwid.Pile(logSelector)
        self.logSelectorWalker = urwid.SimpleFocusListWalker(logSelector)
        logSelectorList = urwid.ListBox(self.logSelectorWalker)
        logSelectorBox = urwid.LineBox(logSelectorList, title='Choose Log Files to Parse', title_align='center')
        logSelectorFiller = urwid.Filler(logSelectorBox, height=('relative', 100))
        return logSelectorFiller
    def update(self,section,newContents):
        self.primary.contents.__setitem__('body', [newContents, None])
    def setFocus(self, newFocus):
        self.primary.focus_position = newFocus
class HeaderFrame():
    def __init__(self, title):
        self.text = urwid.Text(('header', title), align='center', wrap='space')
        self.txtMap = urwid.AttrMap(self.text, 'header')
        self.div = urwid.Divider(' ',top=0,bottom=0)
        self.divMap = urwid.AttrMap(self.div, 'body')
        self.widget =  urwid.Pile((self.txtMap, self.divMap), focus_item=None)
class MainMenu():
    def __init__(self, menuItems):
        self.menuList = []
        for item in menuItems:
            self.menuList.append(
                w.getButton(item[0],self,item[1]))
        self.widget = urwid.Columns(
            self.menuList,
            dividechars=1,
            focus_column=None,
            min_width=1, 
            box_columns=None)
    def getButton(self,buttonLabel, callback):
        button = urwid.Button(buttonLabel,on_press=getattr(self, callback))
        button._label.align = 'center'
        buttonMap = urwid.AttrMap(button, None, focus_map='header')
        return buttonMap
    def quitLoop(self, *args):
        raise urwid.ExitMainLoop()
    def getQuery(self, *args):
        global frame
        frame.primary.focus_position = 'body'
        self.edit = urwid.Edit("Enter Search Query \n")
        self.searchFill = QuestionBox(self.edit)
        frame.primary.contents.__setitem__('body', [self.searchFill, None])
        #urwid.connect_signal(self.edit, 'postchange', newSearch)
    def getFilters(self, *args):
        global queryFilter
        if type(queryFilter) == str:
            queryFilter = Filters()
            queryFilter.addRemoveFilters()
            logging.info('MainMenu.getFilters queryFilter = %s', queryFilter)
        else:
            logging.info('queryFilter.get/add')
            queryFilter.getCurrentFilters()
            queryFilter.addRemoveFilters()
    def showStatSummary(self, *args):
        global frame
        frame.parse.parseThread.join()
        delta = {
            '1': datetime.today() - timedelta(days=1),
            '2': datetime.today() - timedelta(days=2),
            '3': datetime.today() - timedelta(days=3),
            '7': datetime.today() - timedelta(days=7)
        }
        self.sendCount = {'1':0,'2':0,'3':0,'7':0,'t':0}
        self.recCount = {'1':0,'2':0,'3':0,'7':0,'t':0}
        self.senderList = {'1':[],'2':[],'3':[],'7':[],'t':[]}
        for _,entries in entryList.items():
            for entry in entries:
                for days, difference in delta.items():
                    if entry.msgDateTime >= difference and entry.entryType == 'MESSAGE':
                        if entry.msgtype == 'OUTGOING':
                            self.sendCount[days] += 1
                            self.senderList[days].append(entry.sendAddr)
                        if entry.msgtype == 'INCOMING':
                            self.recCount[days] += 1
                if entry.entryType == 'MESSAGE':
                    if entry.msgtype == 'OUTGOING':
                        self.sendCount['t'] += 1
                        self.senderList['t'].append(entry.sendAddr)
                    if entry.msgtype == 'INCOMING':
                        self.recCount['t'] += 1
        topFiveSenders = {}
        for x in ['1','2','3','7','t']:
            topFiveSenders[x] = self.topSender(x, 5)
        self.topSenderList = {}
        for duration, senders in topFiveSenders.items():
            rows = []
            rows.append(urwid.Columns([
                urwid.Text(('header','Sender'), align='center', wrap='space'), 
                urwid.Text(('header', 'Qty'), align='center', wrap='space'),
                ], dividechars=1, focus_column=None, min_width=1, box_columns=None))
            for sender in senders:
                rows.append(urwid.Columns([
                    urwid.Text(('body',str(sender[0])), align='center', wrap='space'), 
                    urwid.Text(('body', str(sender[1])), align='center', wrap='space')
                    ], dividechars=1, focus_column=None, min_width=1, box_columns=None))
            self.topSenderList[duration] = urwid.Pile(rows, focus_item=None)
        headerRow = urwid.Columns([
            (25, urwid.Text(('header', 'Time Period'), align='center', wrap='space')),
            (25, urwid.Text(('header', 'Sent'), align='center', wrap='space')),
            (25, urwid.Text(('header', 'Received'), align='center', wrap='space')),
            ('weight', 2, urwid.Text(('header', 'Top 5 Senders'), align='center', wrap='space'))
        ], dividechars=0, focus_column=None, min_width=1, box_columns=None)
        headerRow = urwid.AttrMap(headerRow, 'header')
        statsSummary = urwid.Pile([
            headerRow,
            self.sumStatRow('Past 24 Hours', '1'),
            self.sumStatRow('Past 48 Hours', '2'),
            self.sumStatRow('Past 72 Hours', '3'),
            self.sumStatRow('Past One Week', '7'),
            self.sumStatRow('Full Exim Logs', 't')
            ], focus_item=None)
        statsFiller = urwid.Filler(statsSummary, 'middle')
        frame.primary.contents.__setitem__('body', [statsFiller, None])
    def sumStatRow(self,headerTxt,rowNumber):
        header = urwid.Text(('header', headerTxt), align='center', wrap='space')
        return urwid.LineBox(urwid.Columns([
        (25, urwid.AttrMap(header, 'header')),
            (25, urwid.Text(('body', str(self.sendCount[rowNumber])), align='center', wrap='space')),
            (25, urwid.Text(('body', str(self.recCount[rowNumber])), align='center', wrap='space')),
            ('weight', 2, self.topSenderList[rowNumber])
        ], dividechars=0, focus_column=None, min_width=1, box_columns=None))
    def testMailer(self, *args):
        logging.info("Test Mailer Option Selected")
    def topSender(self, topSenders, qty):
        return collections.Counter(self.senderList[topSenders]).most_common(qty)
class ResultList():
    def __init__(self,resultEntries):
        global query
        global frame
        global queryFilter
        global newSearchSource
        self.resultEntries = resultEntries
        oldFilter = {
            'msgTypeFilter': [],
            'senderFilter': [],
            'recipFilter': [],
            'dateFilter': []
            }
        if type(newSearchSource) == urwid.wimp.Button:
            for key in oldFilter.keys():
                if getattr(queryFilter, key).current != []:
                    oldFilter[key] = getattr(queryFilter, key).current
                    logging.info('queryFilter Contents stored= %s', getattr(queryFilter, key).current)
                    getattr(queryFilter, key).current = []
            self.filteredResults = self.filterResults()
            for key in oldFilter.keys():
                if oldFilter[key] != []:
                    getattr(queryFilter, key).current = oldFilter[key]
                    logging.info('queryFilter Contents retrieved= %s', getattr(queryFilter, key).current)
                    oldFilter[key] = []
            newSearchSource = ''
        else:
            self.filteredResults = self.filterResults()
        self.div = urwid.Divider(' ',top=0,bottom=0)
        x = 1
        rows = [urwid.Divider(' ',top=0,bottom=0)]
        #rows.append(self.getSummaryRows())
        rows.append(self.div)
        for entries in self.filteredResults.values():
            for entry in entries:
                if query[1] in entry.fullEntry:
                    rows.append(self.getListColumns(x,entry))
                    rows.append(self.div)
                    x += 1
                elif query[0]:
                    if query[1] in getattr(entry, query[0]):
                        rows.append(self.getListColumns(x,entry))
                        rows.append(self.div)
                        x += 1
        self.resultListCount = x - 1
        rows.insert(0,self.getSummaryRows())
        #header = urwid.Text(('body', 'Search Query : ' + str(query) + ' Returned ' + str(x) + ' results'), align='center', wrap='space')
        resultList = urwid.SimpleFocusListWalker(rows)
        resultBox = urwid.ListBox(resultList)
        frame.primary.contents.__setitem__('body', [resultBox, None])
    def filterResults(self):
        self.resultsFiltered = []
        if type(queryFilter) != str:
            logging.info('Current Sender Filter: %s' , len(queryFilter.senderFilter.current))
            logging.info('Current Recipient Filter: %s' , len(queryFilter.recipFilter.current))
            logging.info('Current Date Filter: %s' , len(queryFilter.dateFilter.current))
            logging.info('Current Type Filter: %s' , len(queryFilter.msgTypeFilter.current))
            if len(queryFilter.msgTypeFilter.current) > 0:
                typeFilteredResults = {}
                for key, results in self.resultEntries.items():
                    for result in results:
                        for filter in queryFilter.msgTypeFilter.current:
                            if filter.upper() in result.msgtype and 'MESSAGE' in result.entryType:
                                if key not in typeFilteredResults:
                                    typeFilteredResults[key] = [result]
                                else:
                                    typeFilteredResults[key].append(result)
                self.resultsFiltered.append('msgType')
                self.resultEntries = typeFilteredResults
            self.typeFilteredResults = {}
            if len(queryFilter.senderFilter.current) > 0:
                senderFilteredResults = {}
                for key, results in self.resultEntries.items():
                    for result in results:
                        for filter in queryFilter.senderFilter.current:
                            if filter.lower() in result.sendAddr.lower():
                                if key not in senderFilteredResults:
                                    senderFilteredResults[key] = [result]
                                else:
                                    senderFilteredResults[key].append(result)
                self.resultsFiltered.append('sender')
                self.resultEntries = senderFilteredResults
            if len(queryFilter.recipFilter.current) > 0:
                recipFilteredResults = {}
                for key, results in self.resultEntries.items():
                    for result in results:
                        for filter in queryFilter.recipFilter.current:
                            if filter.lower() in result.to.lower():
                                if key not in recipFilteredResults:
                                    recipFilteredResults[key] = [result]
                                else:
                                    recipFilteredResults[key].append(result)
                self.resultsFiltered.append('recipient')
                self.resultEntries = recipFilteredResults
            if len(queryFilter.dateFilter.current) > 0:
                dateFilteredResults = {}
                for filter in queryFilter.dateFilter.current:
                    if len(filter) == 1:
                        for key, results in self.resultEntries.items():
                            for result in results:
                                if result.msgDateTime.date() == filter[0].date():
                                    if key not in dateFilteredResults:
                                        dateFilteredResults[key] = [result]
                                    else:
                                        dateFilteredResults[key].append(result)
                    if len(filter) == 2:
                        for key, results in self.resultEntries.items():
                            for result in results:
                                if result.msgDateTime >= filter[0] and result.msgDateTime <= filter[1]:
                                    if key not in dateFilteredResults:
                                        dateFilteredResults[key] = [result]
                                    else:
                                        dateFilteredResults[key].append(result)
                self.resultsFiltered.append('date')
                self.resultEntries = dateFilteredResults
        self.filteredResults = self.resultEntries
        return self.filteredResults
    def getButton(self,Buttonlabel,entry):
        button = urwid.Button(str(Buttonlabel),on_press=self.displayEntry, user_data=entry)
        button._label.align = 'center'
        button = urwid.AttrMap(button, None, focus_map='header')
        return button
    def getTextWidget(self,format,textString, alignment):
        return urwid.Text((format, textString), align=alignment, wrap='space')
    def getListColumns(self,x,entry):
        return urwid.Columns([(s.rl.ButtonColWidth,
            w.getButton(x,self,'displayEntry',user_data=entry)),
            self.getFullEntryText(entry.fullEntry)],
            dividechars=s.rl.divChars,
            focus_column=None,
            min_width=1,
            box_columns=None)
    def getFullEntryText(self,fullEntry):
        return urwid.Text(('body', fullEntry), align='left', wrap='space')
    def getSummaryValues(self):
        self.summary = {}
        if len(self.resultsFiltered) > 0:
            if 'msgType' in self.resultsFiltered:
                self.summary[' Filtered by Message Type(s) '] = queryFilter.msgTypeFilter.current
            if 'sender' in self.resultsFiltered:
                self.summary[' Filtered by Sender(s) '] = queryFilter.senderFilter.current
            if 'recipient' in self.resultsFiltered:
                self.summary[' Filtered by Recipient(s) '] = queryFilter.recipFilter.current
            if 'date' in self.resultsFiltered:
                self.summary[' Filterd By Date(s) / Date Range(s) '] = []
                for filter in queryFilter.dateFilter.current:
                    dateFilterObjArray = filter
                    dateTempArray = []
                    for dateFilterObj in dateFilterObjArray:
                        if dateFilterObj.time().__str__() == '00:00:00':
                            dateTempArray.append(datetime.strftime(dateFilterObj, s.displayDateFormat))
                        else:
                            dateTempArray.append(datetime.strftime(dateFilterObj, s.displayDateTimeFormat))
                    dateTimeFilter = ' - '.join(dateTempArray)
                    self.summary['Filterd By Date(s) / Date Range(s):'].append(dateTimeFilter)
        else:
            self.summary[' No Filters Applied '] = ['']
        return self.summary
    def getSummaryFields(self):
        summaryValues = self.getSummaryValues()
        summaryFields = []
        summaryFields.append(w.getText('bold',' There are ' + str(self.resultListCount) + ' Results ', 'center'))
        summaryFields.append(self.div)
        for key, values in summaryValues.items():
            summaryFields.append(w.getText('header',key,'center'))
            for value in values:
                summaryFields.append(w.getText('body',value,'center'))
        return summaryFields
    def getSummaryRows(self):
        summaryFields = self.getSummaryFields()
        summaryRows = [self.div]
        for field in summaryFields:
            summaryRows.append(field)
        summaryRows.append(self.div)
        blank = self.getTextWidget('body','','left')
        summaryList = urwid.Pile(summaryRows, focus_item=None)
        summaryBorder = urwid.LineBox(summaryList, title='Query Summary : ' + str(query[1]), title_align='center')
        summaryRow = urwid.Columns([blank, ('weight', 1, summaryBorder), blank], dividechars=1, focus_column=None, min_width=1, box_columns=None)
        return summaryRow
    def getSummaryCol(self,countWidth,text,count):
        return urwid.Columns([text, (countWidth, count)],
            dividechars=0,
            focus_column=None, min_width=1,
            box_columns=None)
    def displayEntry(self, *args):
        global frame
        self.entrySingleDisplay = args[-1]
        rows = [urwid.Text(('body', 'Entry PID : ' + str(self.entrySingleDisplay.msgpid)), align='center', wrap='space')]
        #rows = [urwid.Columns([(12, blank), header], dividechars=1, focus_column=None, min_width=1, box_columns=None)]
        rows.append(urwid.Divider(' ',top=0,bottom=0))
        for key, value in self.entrySingleDisplay.__dict__.items():
            if value:
                keyButton = urwid.AttrMap(urwid.Button(str(key),on_press=newSearch, user_data=[key,value]), None, focus_map='reversed')
                valueText = urwid.Text(('body', str(value)), align='left', wrap='space')
                rows.append(urwid.Columns([(17,keyButton), valueText], dividechars=1, focus_column=None, min_width=1, box_columns=None))
        singleEntryList = urwid.SimpleFocusListWalker(rows)
        singleEntryBox = urwid.ListBox(singleEntryList)
        frame.primary.contents.__setitem__('body', [singleEntryBox, None])    
class Entry():
    def __init__(self):
        self.fullEntry = ''
        self.msgpid = ''
        self.sendAddr = ''
        self.host = ''
        self.hostIp = ''
        self.mta = ''
        self.interface = ''
        self.protocol = ''
        self.smtpAuth = ''
        self.size = ''
        self.msgid = ''
        self.topic = ''
        self.fr = ''
        self.to = ''
        self.msgtype = ''
        self.msgdate = ''
        self.msgtime = ''
        self.remoteId = ''
        self.bounceId = ''
        self.returnPath = ''
        self.timeInQueue = ''
        self.deliveryTime = ''
        self.smtpError = ''
        self.entryType = ''
        self.msgDateTime = ''
class Search():
    def __init__(self):
        self.rawEntries = {}
        self.queryStartTime = ''
        self.filterTypes = [
            'senderFilter',
            'recipFilter',
            'dateFilter',
            'msgTypeFilter'
            ]
        self.searchLogs()
        #self.resultPids = self.entrySearch()
        #self.resultCount = len(self.resultPids)
        #self.resultEntries = self.getResultEntries()
        #self.showResultsList()
    def searchLogs(self):
        global queryFilter
        global frame
        global logfiles
        global starttime
        if any(logfiles.values()):
                logging.info('There are Filters Set')
                self.primarySearchThreads = []
                starttime = datetime.now()
                for logfile, selected in logfiles.items():
                    if selected:
                        thread = threading.Thread(
                            name=logfile,
                            target=self.searchLogFile,
                            args=([logfile])
                            )
                        self.primarySearchThreads.append(thread)
                        thread.start()
                for thread in self.primarySearchThreads:
                    thread.join()
                    logging.log('Is Alive? %s', thread.isAlive())
                logging.info('total Query time: %s', datetime.now() - starttime)
                logging.info('rawEntries : %s', self.rawEntries.keys())
    def searchLogFile(self,*args):
        logging.info('searchLogFile Started')
        self.resultsFiltered = ''
        self.rawMsgTypeFilteredEntries = ''
        self.rawQueriedEntries = ''
        if type(queryFilter) != str:
            logging.info('queryFilter: %s', queryFilter)
            self.dateFilter(args[0])
            self.rawMsgTypeFilteredEntries = self.msgTypeFilter(args[0])
        if query[1] != '':
            if len(self.resultsFiltered) == 0:
                self.rawQueriedEntries = self.newQuerySearch(args[0])
            else:
                entriesFiltered = getattr(self, self.resultsFiltered)
                self.rawQueriedEntries = self.queryFilteredEntries(entriesFiltered, args[0])
            results = self.rawQueriedEntries
            self.rawEntries = results
    def queryFilteredEntries(self, rawEntries, logfile):
        results = {}
        for key,values in rawEntries.items():
            for value in values:
                if query[1] in value:
                    if key not in results.keys():
                        results[key] = [value]
                    else:
                        results[key].append(value)
        for keys in results.keys():
            logging.info('self.filteredResult Count: %s', len(results[keys]))
        return results
    def newQuerySearch(self,logfile):
        logging.info("New Query Search")
        rawEntries = {}
        if logfile[-2:] != 'gz':
            logging.log('query: %s', query[1])
            with open(logfile,mode='r') as f:
                for _, line in enumerate(f):
                    if query[1] in line:
                        if logfile not in rawEntries.keys():
                            rawEntries[logfile] = [line]
                        else:
                            rawEntries[logfile].append(line)
        else:
            logging.log('query: %s', query[1])
            with gzip.open(logfile,mode='r') as f:
                for _, line in enumerate(f):
                    if logfile not in line:
                        if logfile not in rawEntries.keys():
                            rawEntries[logfile] = [line]
                        else:
                            rawEntries[logfile].append(line)
        #logging.log('Query Results: %s', rawEntries)
        return rawEntries
    def dateFilter(self,logfile):
        logging.info('Start dateFilter')
        if len(queryFilter.dateFilter.current) > 0:
            rawEntries = {}
            dateFilters = queryFilter.dateFilter.current
            for dateFilter in dateFilters:
                if len(dateFilter) == 1:
                    dateString = datetime.strftime(dateFilter[0].date(),s.logDateFormat)
                    logging.info('DateString : %s', dateString)
                    if logfile[-2:] != 'gz':
                        with open(logfile,mode='r') as f:
                            for _, line in enumerate(f):
                                if dateString in line:
                                    if logfile not in rawEntries.keys():
                                        rawEntries[logfile] = [line]
                                    else:
                                        rawEntries[logfile].append(line)
                    else:
                        with gzip.open(logfile,mode='r') as f:
                            for _, line in enumerate(f):
                                if dateString in line:
                                    if logfile not in rawEntries.keys():
                                        rawEntries[logfile] = [line]
                                    else:
                                        rawEntries[logfile].append(line)
            for key in rawEntries.keys():
                logging.info('Date Filtered Entries Count: %s', len(rawEntries[key]))
            self.resultsFiltered = rawEntries
    def msgTypeFilter(self,logfile):
        typeFilters = queryFilter.msgTypeFilter.current
        if len(queryFilter.msgTypeFilter.current) > 0:
            filters = []
            rawEntries = {}
            logging.info('typeFilters : %s', typeFilters)
            for typeFilter in typeFilters:
                if typeFilter.upper() == 'INCOMING':
                    filters.append('<=')
                if typeFilter.upper() == 'OUTGOING':
                    filters.append('=>')
            if type(self.resultsFiltered) != str:
                for key,values in self.resultsFiltered.items():
                    for value in values:
                        if any(filter in value for filter in filters):
                            if key not in rawEntries.keys():
                                rawEntries[key] = [value]
                            else:
                                rawEntries[key].append(value)
            else:
                if logfile[-2:] != 'gz':
                    with open(logfile,mode='r') as f:
                        for _, line in enumerate(f):
                            if any(filter in line for filter in filters):
                                if logfile not in results.keys():
                                    rawEntries[logfile] = [line]
                                else:
                                    rawEntries[logfile].append(line)
                else:
                    with gzip.open(logfile,mode='r') as f:
                        for _, line in enumerate(f):
                            if any(filter in line for filter in filters):
                                if logfile not in rawEntries.keys():
                                    rawEntries[logfile] = [line]
                                else:
                                    rawEntries[logfile].append(line)
            self.resultsFiltered = rawEntries
            for key in rawEntries.keys():
                logging.info('MsgType Filtered Count : %s',len(rawEntries[key]))
    def recipFilter(self, logfile):
        logging.info('Log Extension : %s',logfile[-2:])
    def senderFilter(self, logfile):
        senderFilters = queryFilter.senderFilter.current
        if len(queryFilter.senderFilter.current) > 0:
            filters = []
            rawEntries = {}
            logging.info('typeFilters : %s', senderFilters)
            for senderFilter in senderFilters:
        filters = []
            rawEntries = {}
            logging.info('typeFilters : %s', typeFilters)
            for typeFilter in typeFilters:
                if typeFilter.lower() == 'INCOMING':
                    filters.append('<=')
                if typeFilter.upper() == 'OUTGOING':
                    filters.append('=>')
            if type(self.resultsFiltered) != str:
                for key,values in self.resultsFiltered.items():
                    for value in values:
                        if any(filter in value for filter in filters):
                            if key not in rawEntries.keys():
                                rawEntries[key] = [value]
                            else:
                                rawEntries[key].append(value)
            else:
                if logfile[-2:] != 'gz':
                    with open(logfile,mode='r') as f:
                        for _, line in enumerate(f):
                            if any(filter in line for filter in filters):
                                if logfile not in results.keys():
                                    rawEntries[logfile] = [line]
                                else:
                                    rawEntries[logfile].append(line)
                else:
                    with gzip.open(logfile,mode='r') as f:
                        for _, line in enumerate(f):
                            if any(filter in line for filter in filters):
                                if logfile not in rawEntries.keys():
                                    rawEntries[logfile] = [line]
                                else:
                                    rawEntries[logfile].append(line)
            self.resultsFiltered = rawEntries
            for key in rawEntries.keys():
                logging.info('MsgType Filtered Count : %s',len(rawEntries[key]))
    def showResultsList(self, logfile):
        global frame
        self.resultList = ResultList(self.resultEntries)
    def entrySearch(self):
        self.queryStartTime = datetime.now()
        resultPids = []
        for entries in entryList.values():
            for entry in entries:
                for value in entry.__dict__.values():
                    if type(query[1]) == str and type(value) != datetime:
                        if query[1] in value:
                            if not resultPids:
                                resultPids = [entry.msgpid]
                            else:
                                resultPids.append(entry.msgpid)
        resultPids = dict.fromkeys(resultPids)
        return resultPids
    def getResultEntries(self):
        results = self.resultPids
        r = 1
        for pid in results.keys():
            results[pid] = entryList[pid]
            results[r] = results.pop(pid)
            r += 1
        return results
    def showResultEntries(self):
        #for resultNo,  resultEntries in self.resultEntries.items():
        #    print("Result " + str(resultNo) + ":")
        #   for resultEntry in resultEntries:
        #        if query in resultEntry.fullEntry:
        #            print("\t" + resultEntry.fullEntry)
        #    print("\n")
        for resultPid, resultEntries in self.resultEntries.items():
            print("\nResult " + str(resultPid) + " of " + str(self.resultCount) + "\n")
            for resultEntry in resultEntries:
                if resultEntry.entryType == "MESSAGE":
                    for attr, value in resultEntry.__dict__.items():
                        print('{0:15s} => {1:100}').format(attr, value)
                    print("\n")
            for resultEntry in resultEntries:
                if resultEntry.entryType == "SMTP-ERROR":
                    for attr, value in resultEntry.__dict__.items():
                        print('{0:15s} => {1:100}').format(attr, value)
                    print("\n")
            for resultEntry in resultEntries:
                if resultEntry.entryType == "OTHER":
                    for attr, value in resultEntry.__dict__.items():
                        print('{0:15s} => {1:100}').format(attr, value)
                    print("\n")
class LogFiles():
    def activateParsing(self, *args):
        if any(logfiles.values()):
            self.parseThread = threading.Thread(target=self.parseLogs)
            self.parseThread.start()
            bodyTxt = urwid.Text('Create a New Search or View Stats Summary', align='center', wrap='space')
            self.bodyFiller = urwid.Filler(bodyTxt, 'middle')
            frame.primary.contents.__setitem__('body', [self.bodyFiller, None])
            frame.primary.focus_position = 'footer'
            s.menuEnabled = True
        else:
            sys.exit()
        #frame.logSelectorWalker[0][-1] = w.getText('bold','Parsing Selected Files\nPlease Wait', 'center')
        #if any(logfiles.values()):
        #    #args[0].set_label('Parsing Selected Files....')
        #    self.parseLogs()
        #else:
        #    sys.exit()
    def parseLogs(self):
        global entryList
        global pid
        #eximMainLog = self.getLogs()
        if any(logfiles.values()):
            eximMainLog = self.getLogs()
        else:
            sys.exit()
        starttime = datetime.now()
        logging.info('Parsing Starttime : %s', starttime)
        for i in eximMainLog:
            pid = i.split()[2][1:-1]
            if pid in entryList:
                entryList[pid].append(Entry())
            else:
                entryList[pid] = [Entry()]
            #if '<=' in i:
            #    self.parseIncoming(i)
            #elif '=>' in i:
            #    self.parseDeliveries(i)
            #elif '**' in i:
            #    self.parseFailures(i)
            #elif 'SMTP syntax error' in i:
            #    self.parseSmtpErrors(i)
            #else:
            #    self.parseOthers(i)
        logging.info('Time to create basic entryPID list: %s', datetime.now() - starttime)
    def setLogFiles(self):
        self.logFileNames = []
        for logFile, ParseChoice in logfiles.items():
            self.logFileNames.append(logFile)
        bodyTxt = urwid.Text('Create a New Search or View Stats Summary', align='center', wrap='space')
        self.bodyFiller = urwid.Filler(bodyTxt, 'middle')
        frame.primary.contents.__setitem__('body', [self.bodyFiller, None])
        frame.primary.focus_position = 'footer'
        s.menuEnabled = True
    def parseIncoming(self,i):
        global entryList
        entryList[pid][-1].fullEntry = i
        m = shlex.split(i)
        if m[5] == '<>':
            entryList[pid][-1].msgtype = 'BOUNCE'
        else:
            entryList[pid][-1].msgtype = 'INCOMING'
        entryList[pid][-1].msgdate = m[0]
        entryList[pid][-1].msgtime = m[1]
        entryList[pid][-1].msgpid = pid
        entryList[pid][-1].msgid = m[3]
        entryList[pid][-1].sendAddr = m[5]
        entryList[pid][-1].entryType = 'MESSAGE'
        msgDateTime = entryList[pid][-1].msgdate + '_' + entryList[pid][-1].msgtime
        entryList[pid][-1].msgDateTime = datetime.strptime(msgDateTime, s.datetimeformat)

        x = 1
        while x < len(m):
            if 'H=' in m[x]:
                if m[x+1][0] == '(':
                    entryList[pid][-1].host = m[x][2:] + ' ' + m[x+1]
                    entryList[pid][-1].hostIp = m[x+2].split(':')[0]
                    if s.hostname in entryList[pid][-1].host:
                        entryList[pid][-1].msgType = 'INCOMING'
                        entryList[pid][-1].entryType = 'RELAY'
                else:
                    entryList[pid][-1].host = m[x][2:]
                    entryList[pid][-1].hostIp = m[x+1].split(':')[0]
                    if s.hostname in entryList[pid][-1].host:
                        entryList[pid][-1].msgType = 'INCOMING'
                        entryList[pid][-1].entryType = 'RELAY'
            if 'P=' in m[x]:
                entryList[pid][-1].protocol = m[x][2:]
                if 'local' in entryList[pid][-1].protocol:
                    entryList[pid][-1].msgtype = 'LOCAL'
            if 'T=' in m[x] and m[x][0] != 'R':
                entryList[pid][-1].topic = m[x][2:]
            if 'S=' in m[x] and m[x][0] != 'M':
                entryList[pid][-1].size = m[x][2:]
            if 'I=' in m[x] and m[x][0] != 'S':
                entryList[pid][-1].interface = m[x].split(':')[0][2:]
            if 'R=' in m[x]:
                entryList[pid][-1].bounceId = m[x][2:]
            if 'U=' in m[x]:
                entryList[pid][-1].mta = m[x][2:]
            if 'id=' in m[x]:
                entryList[pid][-1].remoteId = m[x][3:]
            if 'A=' in m[x]:
                entryList[pid][-1].smtpAuth
            if m[x] == 'from':
                if m[x+1] == '<>':
                    entryList[pid][-1].fr = m[x+1]
                else:
                    entryList[pid][-1].fr = m[x+1][1:-1]
            if m[x] == 'for':
                entryList[pid][-1].to = m[x+1]
            if 'QT=' in m[x]:
                entryList[pid][-1].timeInQueue = m[x][3:]
            if 'RT=' in m[x]:
                entryList[pid][-1].deliveryTime = m[x][3:]
            x += 1
    def parseDeliveries(self,i):
        global entryList
        entryList[pid][-1].fullEntry = i
        m = shlex.split(i)
        entryList[pid][-1].msgtype = 'OUTGOING'
        entryList[pid][-1].msgdate = m[0]
        entryList[pid][-1].msgtime = m[1]
        entryList[pid][-1].msgpid = pid
        entryList[pid][-1].msgid = m[3]
        entryList[pid][-1].entryType = 'MESSAGE'

        msgDateTime = entryList[pid][-1].msgdate + '_' + entryList[pid][-1].msgtime
        entryList[pid][-1].msgDateTime = datetime.strptime(msgDateTime, s.datetimeformat)
        if '@' in m[5]:
            entryList[pid][-1].to = m[5]
        else:
            entryList[pid][-1].to = m[5] + ' ' + m[6]
        x = 1
        while x < len(m):
            if 'H=' in m[x]:
                entryList[pid][-1].host = m[x][2:]
                entryList[pid][-1].hostIp = m[x+1].split(':')[0]
            if 'P=' in m[x]:
                entryList[pid][-1].returnPath = m[x][3:-1]
            if 'T=' in m[x] and m[x][0] != 'D' and m[x][0] != 'Q':
                entryList[pid][-1].mta = m[x][2:]
                if 'dovecot_virtual_delivery' in entryList[pid][-1].mta:
                    entryList[pid][-1].msgtype = 'LOCAL DELIVERY'
            if 'S=' in m[x] and m[x][0] != 'M':
                entryList[pid][-1].size = m[x][2:]
            if 'I=' in m[x] and m[x][0] != 'S':
                entryList[pid][-1].interface = m[x][3:].split(']')[0]
            if 'R=' in m[x]:
                entryList[pid][-1].protocol = m[x][2:]
            if 'U=' in m[x]:
                entryList[pid][-1].mta = m[x][2:]
            if 'id=' in m[x]:
                m[x].split()
                for a in m[x]:
                    if 'id=' in a:
                        entryList[pid][-1].remoteId = a[3:]
            if 'A=' in m[x]:
                entryList[pid][-1].smtpAuth
            if 'F=<' in m[x]:
                entryList[pid][-1].sendAddr = m[x][2:]
                if not entryList[pid][-1].sendAddr == '<>':
                    entryList[pid][-1].sendAddr = m[x][3:-1]
                entryList[pid][-1].fr = entryList[pid][-1].sendAddr
            if 'C=' in m[x]:
                entryList[pid][-1].delStatus = m[x][2:]
            if 'QT=' in m[x]:
                entryList[pid][-1].timeInQueue = m[x][3:]
            if 'DT=' in m[x]:
                entryList[pid][-1].deliveryTime = m[x][3:]
            x += 1
    def parseFailures(self, i):
        global entryList
        entryList[pid][-1].fullEntry = i
        m = shlex.split(i)
        entryList[pid][-1].msgtype = 'FAILED'
        entryList[pid][-1].msgdate = m[0]
        entryList[pid][-1].msgtime = m[1]
        entryList[pid][-1].msgpid = pid
        entryList[pid][-1].msgid = m[3]
        entryList[pid][-1].entryType = 'MESSAGE'

        msgDateTime = entryList[pid][-1].msgdate + '_' + entryList[pid][-1].msgtime
        entryList[pid][-1].msgDateTime = datetime.strptime(msgDateTime, s.datetimeformat)
        if '@' in m[5]:
            entryList[pid][-1].to = m[5]
        else:
            entryList[pid][-1].to = m[5] + ' ' + m[6]
        x = 1
        while x < len(m):
            if 'H=' in m[x]:
                entryList[pid][-1].host = m[x][2:]
                entryList[pid][-1].hostIp = m[x+1].split(':')[0]
            if 'P=' in m[x]:
                entryList[pid][-1].returnPath = m[x][3:-1]
            if 'T=' in m[x] and m[x][0] != 'D' and m[x][0] != 'Q':
                entryList[pid][-1].mta = m[x][2:]
                if 'dovecot_virtual_delivery' in entryList[pid][-1].mta:
                    entryList[pid][-1].msgtype = 'LOCAL DELIVERY'
            if 'S=' in m[x] and m[x][0] != 'M':
                entryList[pid][-1].size = m[x][2:]
            if 'I=' in m[x] and m[x][0] != 'S':
                entryList[pid][-1].interface = m[x][3:].split(']')[0]
            if 'R=' in m[x]:
                if 'fail' in m[x]:
                    entryList[pid][-1].smtpError = " ".join(m[x:])[2:]
                entryList[pid][-1].protocol = m[x][2:]
            if 'U=' in m[x]:
                entryList[pid][-1].mta = m[x][2:]
            if 'id=' in m[x]:
                m[x].split()
                for a in m[x]:
                    if 'id=' in a:
                        entryList[pid][-1].remoteId = a[3:]
            if 'A=' in m[x]:
                entryList[pid][-1].smtpAuth
            if 'F=<' in m[x]:
                entryList[pid][-1].sendAddr = m[x][2:]
                if not entryList[pid][-1].sendAddr == '<>':
                    entryList[pid][-1].sendAddr = m[x][3:-1]
                entryList[pid][-1].fr = entryList[pid][-1].sendAddr
            if 'C=' in m[x]:
                entryList[pid][-1].delStatus = m[x][2:]
            if 'QT=' in m[x]:
                entryList[pid][-1].timeInQueue = m[x][3:]
            if 'DT=' in m[x]:
                entryList[pid][-1].deliveryTime = m[x][3:]
            if 'A=' in m[x]:
                print(m)
            if m[x] == 'SMTP':
                entryList[pid][-1].smtpError = " ".join(m[x:])
            x += 1
    def parseOthers(self, i):
        global entryList
        entryList[pid][-1].fullEntry = i
        m = shlex.split(i)
        entryList[pid][-1].msgdate = m[0]
        entryList[pid][-1].msgtime = m[1]
        entryList[pid][-1].msgpid = pid
        entryList[pid][-1].msgid = m[3]
        entryList[pid][-1].entryType = 'OTHER'
        entryList[pid][-1].entryData = ' '.join(m[3:])
        msgDateTime = entryList[pid][-1].msgdate + '_' + entryList[pid][-1].msgtime
        entryList[pid][-1].msgDateTime = datetime.strptime(msgDateTime, s.datetimeformat)

        x = 1
        while x < len(m):
            if 'H=' in m[x]:
                entryList[pid][-1].host = m[x][2:]
                if x+1 < len(m) and ':' in m[x+1]:
                    entryList[pid][-1].hostIp = m[x+1].split(':')[0]
            if 'P=' in m[x]:
                entryList[pid][-1].returnPath = m[x][3:-1]
            if 'T=' in m[x] and m[x][0] != 'D' and m[x][0] != 'Q':
                entryList[pid][-1].mta = m[x][2:]
                if 'dovecot_virtual_delivery' in entryList[pid][-1].mta:
                    entryList[pid][-1].msgtype = 'LOCAL DELIVERY'
            if 'S=' in m[x] and m[x][0] != 'M':
                entryList[pid][-1].size = m[x][2:]
            if 'I=' in m[x] and m[x][0] != 'S':
                entryList[pid][-1].interface = m[x][3:].split(']')[0]
            if 'R=' in m[x]:
                if 'fail' in m[x]:
                    entryList[pid][-1].smtpError = " ".join(m[x:])[2:]
                entryList[pid][-1].protocol = m[x][2:]
            if 'U=' in m[x]:
                entryList[pid][-1].mta = m[x][2:]
            if 'id=' in m[x]:
                m[x].split()
                for a in m[x]:
                    if 'id=' in a:
                        entryList[pid][-1].remoteId = a[3:]
            if 'A=' in m[x]:
                entryList[pid][-1].smtpAuth
            if 'F=<' in m[x]:
                entryList[pid][-1].sendAddr = m[x][2:]
                if not entryList[pid][-1].sendAddr == '<>':
                    entryList[pid][-1].sendAddr = m[x][3:-1]
                entryList[pid][-1].fr = entryList[pid][-1].sendAddr
            if 'C=' in m[x]:
                entryList[pid][-1].delStatus = m[x][2:]
            if 'QT=' in m[x]:
                entryList[pid][-1].timeInQueue = m[x][3:]
            if 'DT=' in m[x]:
                entryList[pid][-1].deliveryTime = m[x][3:]
            if m[x] == 'from':
                if m[x+1] == '<>':
                    entryList[pid][-1].fr = m[x+1]
                else:
                    entryList[pid][-1].fr = m[x+1][1:-1]
            x += 1
    def parseSmtpErrors(self, i):
        global entryList
        entryList[pid][-1].fullEntry = i
        m = i.split()
        entryList[pid][-1].smtpError = i[i.index('SMTP'):]
        entryList[pid][-1].entryType = 'SMTP-ERROR'
        entryList[pid][-1].msgdate = m[0]
        entryList[pid][-1].msgtime = m[1]
        entryList[pid][-1].msgpid = pid
        msgDateTime = entryList[pid][-1].msgdate + '_' + entryList[pid][-1].msgtime
        entryList[pid][-1].msgDateTime = datetime.strptime(msgDateTime, s.datetimeformat)    
class QuestionBox(urwid.Filler):
    def keypress(self, size, key):
        global newQuery
        if key != 'enter':
            return super(QuestionBox, self).keypress(size, key)
        newQuery = ['',self.original_widget.get_edit_text()]
        self.original_widget.set_edit_text('')
        newSearch(newQuery)
class FilterEntry(urwid.Filler):
    def keypress(self, size, key):
        global filterEntryEditText
        if key != 'enter':
            return super(FilterEntry, self).keypress(size, key)
        filterEntryEditText = self.original_widget.get_edit_text()
        self.original_widget.set_edit_text('')
class Filter():
    def __init__(self,filterType):
        self.current = []
        self.filterType = filterType
        self.markedForDeletion = []
        self.markForAddition = []
    def checkForAddFilterEntry(self, *args):
        global filterEntryEditText
        if filterEntryEditText:
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
                filterDateArray = []
                for date in filterStringArray:
                    filterDateArray.append(stringToDate(date))
                if filterDateArray in self.current:
                    self.current.remove(filterDateArray)
            else:
                self.current.remove(item)
            currentFilterWalker = queryFilter.filterDisplayWalkers[self.filterType]
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
        if self.filterType == 'Date':
            if ',' in newFilter:
                newFilter = newFilter.split(',')
            else:
                newFilter = [newFilter]
            dateTimeFilter = []
            for entry in newFilter:
                dateString = stringToDate(entry)
                if not dateString:
                    addFilterTrue = False
                else:
                    dateTimeFilter.append(stringToDate(entry))
        if addFilterTrue:
            if newFilter not in self.current:
                if self.filterType == 'Date':
                    if dateTimeFilter not in self.current:
                        self.current.append(dateTimeFilter)
                        newFilter = ','.join(newFilter)
                        newFilterCheckBoxItem = w.getCheckBoxItem(newFilter,
                            on_state_change=[self,'markForDeletion'],
                            user_data=newFilter)
                else:
                    self.current.append(newFilter)
                newFilterCheckBoxItem = w.getCheckBoxItem(newFilter,
                    on_state_change=[self,'markForDeletion'],
                    user_data=newFilter)
                currentFilterWalker = queryFilter.filterDisplayWalkers[self.filterType]
                if newFilterCheckBoxItem not in currentFilterWalker:
                    currentFilterWalker.insert(-1, newFilterCheckBoxItem)
class Filters():
    def __init__(self):
        self.senderFilter = Filter('Sender')
        self.recipFilter = Filter('Recipient')
        self.dateFilter = Filter('Date')
        self.msgTypeFilter = Filter('Type')
    def filterDisplayList(self,filterInst,filterType):
        filterDisplayList = []
        for filter in getattr(filterInst,'current'):
            if filterType == 'Date':
                tempDateArray = []
                for dateItem in filter:
                    if dateItem.time().__str__() == '00:00:00':
                        logging.info('DateTime Delta : %s', dateItem.time().__str__())
                        tempDateArray.append(datetime.strftime(dateItem,s.displayDateFormat))
                    else:
                        tempDateArray.append(datetime.strftime(dateItem,s.displayDateTimeFormat))
                filter = ','.join(tempDateArray)
            filterDisplayList.append(
                w.getCheckBoxItem(filter,
                    on_state_change=[filterInst,'markForDeletion'],
                    user_data=filter))
        checkBox = w.getCheckBox('Active Filter List', filterDisplayList,'Remove Selected Filter(s)', [filterInst,'remFilters'])
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
            [self.senderFilter,'Sender'],
            [self.recipFilter,'Recipient'],
            [self.dateFilter,'Date'],
            [self.msgTypeFilter,'Type']]
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
        #filterHeaders = self.getFilterHeaders()
        filterPile = urwid.Pile([
            ('pack', header),
            #(5, filterHeaders),
            (5,setFilters),
            getFilters
        ])
        #filterPageList = urwid.Pile(filterPile)
        #self.filterFiller = urwid.Filler(self.filterPageList,valign='middle')
        frame.update('body',filterPile)
        frame.setFocus('body')
def newSearch(*args):
    global query
    global newQuery
    global newSearchSource
    #if newQuery[1]:
    query = newQuery
    newQuery = ['','']
    global frame
    if type(args[0]) == urwid.wimp.Button:
        query[1] = args[1][1]
        query[0] = args[1][0]
        newSearchSource = args[0]
    logging.log('Start Search')
    search = Search()
    return search
def toggleLogSelector(*args):
    global logfiles
    logfiles[args[2]] = args[1]
def input_handling(key):
    if type(key) == str:
        if key in ('q', 'N'):   
            raise urwid.ExitMainLoop()
        if key in ('N', 'n'):
            frame.footer.getQuery()
        if key in ('S', 's'):
            frame.footer.showStatSummary()
        if key in 'tab':
            if frame.primary.focus_position == 'footer':
                frame.primary.focus_position = 'body'
            else:
                if s.menuEnabled:
                    frame.primary.focus_position = 'footer'
def stringToDate(newFilter):
    try:
        datetime.strptime(newFilter, s.displayDateTimeFormat)
    except ValueError:
        try:
            datetime.strptime(newFilter, s.displayDateFormat)
        except:
            return False
        else:
            return datetime.strptime(newFilter, s.displayDateFormat)
    else:
        return datetime.strptime(newFilter, s.displayDateTimeFormat)
s = GlobalSettings()
w = MyWidgets()
frame = GuiFrame()
loop = urwid.MainLoop(frame.primary, frame.palette, unhandled_input=input_handling)
loop.run()
