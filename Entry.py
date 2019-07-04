class Entry():
    def __init__(self, fullEntryText, name):
        """This class is used to create single-view Entry Objects
        """
        self.name = name
        self.id = []
        self.msgType = []
        self.date = []
        self.time = []
        self.sendAddr = []
        self.recipient = []
        self.fullEntryText = fullEntryText
        self.entryType = []
        if 'Warning: "SpamAssassin' in self.fullEntryText:
            self.msgType = [15, 'Message Type: ', 'Spam Status']
        #debug('Init Entries: %s', self.fullEntryText)
        try:
            shlex.split(self.fullEntryText)
        except:
            #debug('Cannot shlex split this entry!')
            try:
                self.fullEntryText.split()
            except:
                warning('Could Not Parse line: %s', self.fullEntryText)
            else:
                #debug('Parsing with standard split')
                m = self.fullEntryText.split()
                #debug('split entry: %s', m)
                if self.msgType:
                    #debug('self.msgType: %s', self.msgType)
                    if self.msgType[2] == 'spam status':
                            if 'detected' in m:
                                self.spamStatus = [15, 'spam status',  ' '.join(m[m.index('detected') + 3: -2])]
                                self.spamScore = [15, 'spam score', m[-1]]
                #self.parseError = [15, 'Parsing Error: ', str(Exception)]
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
                    if m[x].startswith('cwd'):
                        self.cwd = [13, 'Source Directory: ', m[x].split('=')[1]]
                        if self.cwd[2] == '/var/spool/exim':
                            self.msgType = [15, 'Message Type: ', 'exim queue']
                            self.id = [13, 'Message Id: ', m[-1]]
                        else:
                            self.msgType = [15, 'Message Type: ', 'script mailer']
                        if 'args:' in m:
                            args = m.index('args:')
                            self.script = [13, 'Sending Script: ', m[args + 1]]
                            if len(m) > args + 2:
                                self.scriptArgs = [13, 'Script Arguments: ', ' '.join(m[args + 2:])]
                    else:
                        self.id = [13, 'Message ID: ', m[x]]
                    if 'Sender' in m[x]:
                        self.msgType = [15, 'Message Type: ', 'sender id']
                if x == 4:
                    if len(m[x]) == 2:
                        self.entryType = [22, 'Entry Type Symbol: ', m[x]]
                    elif 'Completed' in m[x]:
                        self.msgType = [15, 'Message Type: ', 'queue status']
                #debug('parseEntries self.fullEntryText: %s', self.fullEntryText)
                if self.msgType:
                    if self.msgType[2] == 'Spam Status':
                        if 'detected' in m[x]:
                            n = m[x].split()
                            if 'detected' in n:
                                self.spamStatus = [15, 'Spam Status',  ' '.join(n[n.index('detected')+3:-1])]
                                self.spamScore = [15, 'Spam Score', n[-1]]
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
                    self.smtpError = [22, 'SMTP Message: ', " ".join(m[x:])]
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
                if '<=' in fullEntryText:
                    if 'A=' in m[x]:
                        self.smtpAuth = [22, 'Auth. Method: ', m[x][2:]]
                    if x == 5:
                        self.sendAddr = [18, 'Sender: ', m[x]]
                    if 'P=' in m[x]:
                        self.protocol = [22, 'Protocol: ', m[x][2:]]
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
                        if '(' in m[x+1] and ')' in m[x+1]:
                            y = m[x+1]
                            stripped_recip = y[y.index('(') + 1:y.index(')')]
                            self.recipient = [19, 'Recipient: ', stripped_recip]
                        if '<' in m[x+1] and '>' in m[x+1]:
                            y = m[x+1]
                            stripped_recip = y[y.index('<') + 1:y.index('>')]
                            self.recipient = [19, 'Recipient: ', stripped_recip]
                        else:
                            self.recipient = [19, 'Recipient: ', m[x+1]]
                    if 'P=local' in fullEntryText:
                        self.msgType = [15, 'Message Type: ', 'local']
                    elif 'A=dovecot' in fullEntryText:
                        self.msgType = [15, 'Message Type: ', 'relay']
                    else:
                        self.msgType = [15, 'Message Type: ', 'incoming']
                else:
                    if x == 5:
                        if '@' in m[x]:
                            if '(' in m[x] and ')' in m[x]:
                                y = m[x]
                                stripped_recip = y[y.index('(') + 1:y.index(')')]
                                self.recipient = [19, 'Recipient: ', stripped_recip]
                            if '<' in m[x] and '>' in m[x]:
                                y = m[x]
                                stripped_recip = y[y.index('<') + 1:y.index('>')]
                                self.recipient = [19, 'Recipient: ', stripped_recip]
                            self.recipient = [19, 'Recipient: ', m[x]]
                        else:
                            if len(m) > x + 1:
                                if '@' in m[x + 1]:
                                    if '(' in m[x+1] and ')' in m[x+1]:
                                        y = m[x+1]
                                        stripped_recip = y[y.index('(') + 1:y.index(')')]
                                        self.recipient = [19, 'Recipient: ', stripped_recip]
                                    if '<' in m[x+1] and '>' in m[x+1]:
                                        y = m[x+1]
                                        stripped_recip = y[y.index('<') + 1:y.index('>')]
                                        self.recipient = [19, 'Recipient: ', stripped_recip]
                                    else:
                                        self.recipient = [19, 'Recipient: ', m[x] + m[x+1]]
                    if 'P=' in m[x]:
                        self.returnPath = [20, 'Return Path: ', m[x][3:-1]]
                    if 'T=' in m[x] and m[x][0] != 'D' and m[x][0] != 'Q':
                        self.mta = [22, 'MTA: ', m[x][2:]]
                        if 'dovecot' in self.mta[1]:
                            self.msgType = [15, 'Message Type: ', 'local']
                    if ' => ' in fullEntryText:
                        if 'T=dovecot' in fullEntryText:
                            self.msgType = [15, 'Message Type: ', 'dovecot']
                        else:
                            self.msgType = [15, 'Message Type: ', 'outgoing']
                    if ' -> ' in fullEntryText:
                        self.msgType = [15, 'Message Type: ', 'forwarder']
                    if not self.entryType and ' rejected ' in fullEntryText:
                        self.msgType = [15, 'Message Type: ', 'bounce']
                        self.id = []
                    if 'SMTP connection' in fullEntryText:
                        self.msgType = [15, 'Message Type: ', 'SMTP Connect']
                    if ' ** ' in fullEntryText:
                        self.msgType = [15, 'Message Type: ', 'bounce']
                    if ' no host name found ' in fullEntryText or ' failed to find host name ' in fullEntryText:
                        self.msgType = [15, 'Message Type: ', 'Hostname Error']
                x += 1
            self.fullEntryText = [14, 'Full Entry: ', self.fullEntryText]
