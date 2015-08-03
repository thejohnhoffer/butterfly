import json
import os
import socket
import time
import tornado
import tornado.gen
import tornado.web
import tornado.websocket
import urllib
import urlparse
import numpy as np
import cv2
import StringIO
import zlib

class WebServerHandler(tornado.web.RequestHandler):

  def initialize(self, webserver):
    self._webserver = webserver

  @tornado.web.asynchronous
  @tornado.gen.coroutine
  def get(self, uri):
    '''
    '''
    self._webserver.handle(self)


class WebServer:

  def __init__( self, core, port=2001 ):
    '''
    '''
    self._core = core
    self._port = port

  def start( self ):
    '''
    '''

    ip = socket.gethostbyname('')
    port = self._port

    webapp = tornado.web.Application([
      
      (r'/metainfo/(.*)', WebServerHandler, dict(webserver=self)),
      (r'/data/(.*)', WebServerHandler, dict(webserver=self)),
      (r'/zip/(.*)', WebServerHandler, dict(webserver=self)),
      # (r'/(.*)', tornado.web.StaticFileHandler, dict(path=os.path.join(os.path.dirname(__file__),'../web'), default_filename='index.html'))
  
    ])

    webapp.listen(port, max_buffer_size=1024*1024*150000)

    print 'Starting webserver at \033[93mhttp://' + ip + ':' + str(port) + '\033[0m'

    tornado.ioloop.IOLoop.instance().start()

  @tornado.gen.coroutine
  def handle( self, handler ):
    '''
    '''
    content = None

    splitted_request = handler.request.uri.split('/')
    query = '/'.join(splitted_request[2:])[1:]

    if splitted_request[1] == 'metainfo':

      # content = self._core.get_meta_info(path)
      content = 'metainfo'
      content_type = 'text/html'

    #image data request
    elif splitted_request[1] == 'data':

      parsed_query = urlparse.parse_qs(query)
      print 'Parsed query:', parsed_query
      try:
        datapath = parsed_query['datapath'][0]
        start = tuple(int(a) for a in parsed_query['start'][0].split(','))
        # x = int(parsed_query['x'][0])
        # y = int(parsed_query['y'][0])
        # z = int(parsed_query['z'][0])
        # w = int(parsed_query['w'][0])
        w = int(parsed_query['mip'][0])
        volsize = tuple(int(a) for a in parsed_query['size'][0].split(','))
        volume = self._core.get(datapath, start, volsize, w)

        #Show some basic statistics
        print 'Shape:', volume.shape
        # print 'Unique values in volume:' 
        # print np.unique(volume)
        # content = 'data'
        # content_type = 'text/html'

        #Temporary image output
        content = cv2.imencode('.png', volume[:,:,0].astype('uint8'))[1].tostring()
        content_type = 'image/png'

      except KeyError:
        print 'Missing query'
        content = 'Error 400: Bad request<br>Missing query'
        content_type = 'text/html'
      except (TypeError, ValueError):
        print 'Out of bounds'
        content = 'Error 400: Bad request<br>Out of bounds'
        content_type = 'text/html'
    
    #Binary zipped data request (images)
    elif splitted_request[1] == 'zip':
      parsed_query = urlparse.parse_qs(query)
      print 'Parsed query:', parsed_query
      try:
        datapath = parsed_query['datapath'][0]
        start = tuple(int(a) for a in parsed_query['start'][0].split(','))
        w = int(parsed_query['mip'][0])
        volsize = tuple(int(a) for a in parsed_query['size'][0].split(','))
        volume = self._core.get(datapath, start, volsize, w)

        #Show some basic statistics
        print 'Shape:', volume.shape

        zipped_data = zlib.compress(volume.tostring())

        output = StringIO.StringIO()
        output.write(zipped_data)
        content = output.getvalue()
        content_type = 'application/octet-stream'
      except KeyError:
        print 'Missing query'
        content = 'Error 400: Bad request<br>Missing query'
        content_type = 'text/html'
      except (TypeError, ValueError):
        print 'Out of bounds'
        content = 'Error 400: Bad request<br>Out of bounds'
        content_type = 'text/html'

    # invalid request
    if not content:
      content = 'Error 404: Not found'
      content_type = 'text/html'

    # handler.set_header('Cache-Control','no-cache, no-store, must-revalidate')
    # handler.set_header('Pragma','no-cache')
    # handler.set_header('Expires','0')
    handler.set_header('Access-Control-Allow-Origin', '*')
    handler.set_header('Content-Type', content_type)
    
    #Temporary check for img output
    handler.write(content)
