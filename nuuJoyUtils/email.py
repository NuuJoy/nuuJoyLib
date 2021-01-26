#!/usr/bin/python3


import imaplib
import smtplib


__version__ = (2021,1,26,'beta')


class emailobject():
    '''
    ***Many thing to revise for this stupid email scraping***
        Purpose:
            Scrap email data from plain text
    '''
    def __init__(self,rawmessage):
        self._rawmessage = rawmessage
        self.content = []
        contentStart = False
        for line in self._rawmessage.decode().split('\r\n'):
            if not(contentStart):
                if line.startswith('Date: '):
                    self.datetime = line.replace('Date: ','')
                elif line.startswith('Subject: '):
                    self.subject = line.replace('Subject: ','')
                elif line.startswith('From: '):
                    self.from_email = line.split('<')[-1].split('>')[0]
                elif line == '':
                    contentStart = True
            else:
                self.content.append(line)
        self.content = self.content[:-1]
    def __repr__(self):
        return 'From   : {}\n'.format(self.from_email) + \
               'Date   : {}\n'.format(self.datetime) + \
               'Subject: {}\n'.format(self.subject) + \
               '\n'.join(self.content)


class gmailReader():
    '''
    Get all/unread email from server using 'imaplib'
        Purpose:
            Get email that its subject match 'mark' arrtribute, leave other unseen
        Example:
            mail_reader = gmailReader('myemail@someprovider.com','mypassword',mark='identicaltext')
            for email in mail_reader.emailList:
                print(email)
    '''
    def __init__(self,user,psswrd,mailbox='unread',mark=''):
        self.emailList = []
        mailbox = {'all':'ALL','unread':'(UNSEEN)'}[mailbox]
        with imaplib.IMAP4_SSL('imap.gmail.com') as server:
            server.login(user,psswrd)
            server.select(mailbox='INBOX',readonly=(True if not(mark) else False))
            _, data = server.search(None,mailbox)
            for num in data[0].split():
                _, data = server.fetch(num,'(RFC822)')
                mailobj = emailobject(data[0][1])
                if mark in mailobj.subject:
                    self.emailList.append(mailobj)
                else:
                    server.store(num,'-FLAGS','(\\SEEN)')


class gmailWriter():
    '''
    Send email using 'smtplib'
        Purpose:
            Send a minimal email body to server
        Example:
            with gmailWriter('myemail@someprovider.com','mypassword') as mail_writer:
                mail_writer.sendmail('sendtosomeone@someprovider.com','mailsubject','mailbody')
    '''
    def __init__(self,user,psswrd):
        self.user   = user
        self.psswrd = psswrd
    def __enter__(self):
        self.server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        self.server.ehlo()
        self.server.login(self.user, self.psswrd)
        return self
    def __exit__(self,*args):
        self.server.close()
    def sendmail(self,to_email,subject,content):
        self.server.sendmail(self.user,to_email,'Subject: {}\n\n{}'.format(subject,content))

