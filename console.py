__author__ = "Peter Bennett"
__copyright__ = "Copyright 2012, Peter A Bennett"
__license__ = "LGPL"
__maintainer__ = "Peter Bennett"
__email__ = "pab850@gmail.com"
__contact__ = "www.bytebash.com"

import pyglet
from collections import OrderedDict

class Console:
    """ A simple text console for displaying events."""
    def __init__(self,x,y,width):
        self.textBuffer = []
        self.bufferLength = 10
        self.x = x
        self.y = y
        self.timeToLive = 500
        self.width = width
        self.label = pyglet.text.Label(font_name='Consolas',
                                       font_size=10,
                                       x=self.x,
                                       color = (255, 255, 255, 255),
                                       y=self.y,
                                       width=self.width,
                                       multiline=True)  
                        
    def updateConsole(self, string):
        # Add a [label,time_to_live] list
        self.textBuffer.append(string)
        if (len(self.textBuffer)>self.bufferLength):
            self.textBuffer = self.textBuffer[1:]
        self.label.text = ''.join([str(x) + '\n' for x in self.textBuffer])

    def removeEntry(self):
        self.textBuffer = self.textBuffer[1:]
        self.label.text = ''.join([str(x) + '\n' for x in self.textBuffer])
    def setPosition(self,x,y):
        self.x = x
        self.y = y
        self.label.x = self.x
        self.label.y = self.y
    def draw(self):
        if len(self.textBuffer) > 0:
            self.timeToLive -= 1
            if self.timeToLive <= 0:
                self.timeToLive = 500
                self.removeEntry()
        else:
            self.timeToLive = 500
            
        self.label.draw()
        
class StatusConsole:
    """ A static console for displaying parameters that change over time. """
    def __init__(self,x,y,width):
        self.parameters = OrderedDict()
        self.paramCount = 0
        self.x = x
        self.y = y
        self.title = ''
        self.width = width
        self.label = pyglet.text.Label(self.title,
                                       font_name='Consolas',
                                       font_size=10,
                                       color = (255, 255, 255, 255),
                                       x=self.x,
                                       y=self.y,
                                       width=self.width,
                                       multiline=True)
    def addParameter(self, parameter):
        if(not self.parameters.has_key(parameter)):
            self.parameters[parameter] = None
            self.modified = True
    def setParameter(self, parameter, value):
        if(self.parameters.has_key(parameter)):
            self.parameters[parameter] = value
            self.modified = True
    def setTitle(self, string=''):
        self.title = string
    def updateLabel(self):
        s = ''.join([str(a) + " : " + str(b) + '\n' for a,b in self.parameters.items()])
        s = self.title + '\n' + s
        self.label.text = s
    def draw(self):
        if(self.modified):
            self.updateLabel()
        self.label.draw()
   