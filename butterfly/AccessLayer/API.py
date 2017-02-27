from RequestHandler import RequestHandler
from QueryLayer import InfoQuery
from QueryLayer import DataQuery
from urllib2 import HTTPError
import numpy as np

class API(RequestHandler):

    def parse(self, request):

        super(API, self).parse(request)

        meths = self.INPUT.METHODS.LIST
        command = self._match_list('method',request,meths)

        if command == self.INPUT.METHODS.META.NAME:
            return self._get_meta_info()
        if command == self.INPUT.METHODS.FEAT.NAME:
            return self._get_feature_info()
        # Handle all methods the same if in same list
        if command in self.INPUT.METHODS.GROUP_LIST:
            return self._get_group(command)
        if command in self.INPUT.METHODS.IMAGE_LIST:
            return self.get_data(command)

        return 'Unsupported Request Category'

    '''
    Loads dictionary for info methods
    '''

    def _get_meta_info(self):
        # Get needed metadata
        info = self.OUTPUT.INFO
        meta_info = self._get_group_dict('')

        # Get requested query parameters
        out_format = self._get_list_query(self.INPUT.INFO.FORMAT)

        return InfoQuery(**{
            self.INPUT.METHODS.NAME: self.INPUT.METHODS.META.NAME,
            info.CHANNEL.NAME: meta_info[info.CHANNEL.NAME],
            info.TYPE.NAME: meta_info[info.TYPE.NAME],
            info.PATH.NAME: meta_info[info.PATH.NAME],
            info.SIZE.NAME: meta_info[info.SIZE.NAME],
            self.INPUT.INFO.FORMAT.NAME: out_format
        })

    def _get_feature_info(self):
        # Get needed metadata
        info = self.OUTPUT.INFO
        # meta_info = self._get_group_dict('')

        # Get requested query parameters
        out_format = self._get_list_query(self.INPUT.INFO.FORMAT)

        return InfoQuery(**{
            self.OUTPUT.INFO.NAMES.NAME: ['not yet'],
            self.INPUT.METHODS.NAME: self.INPUT.METHODS.FEAT.NAME
        })

    '''
    Lists values from config for group methods
    '''

    def get_value(self, g):
        return g.get(self.INPUT.GROUP.NAME,'')

    def _find_all_groups(self, _method):
        group_methods = self.INPUT.METHODS.GROUP_LIST
        group_queries = self.INPUT.GROUP.LIST
        # List all parent methods of _method
        if _method in group_methods:
            group_index = group_methods.index(_method)
            group_methods = group_methods[:group_index]
            group_queries = group_queries[:group_index]

        return zip(group_methods, group_queries)

    def _get_group_dict(self, _method):
        configured = self.BFLY_CONFIG
        # validate each query value in each configured level
        for method, query in self._find_all_groups(_method):
            valid_groups = configured.get(method,[])
            valid_values = map(self.get_value, valid_groups)
            # Check query value against all valid query values
            query_value = self.get_query_argument(query,'')
            self._match_list(query, query_value, valid_values)
            # Continue matching query_value from list of valid groups
            configured = valid_groups[valid_values.index(query_value)]
        return configured

    def _get_group(self, _method):
        out_format = self._get_list_query(self.INPUT.INFO.FORMAT)
        group_list = self._get_group_dict(_method).get(_method,[])
        group_values = map(self.get_value, group_list)

        # Return an empty query
        return InfoQuery(**{
            self.INPUT.METHODS.NAME: _method,
            self.INPUT.INFO.FORMAT.NAME: out_format,
            self.OUTPUT.INFO.NAMES.NAME: group_values
        })

    '''
    Loads data from tiles for image methods
    '''

    def get_data(self, _method):
        # Parse all the group terms
        meta_dict = self._get_group_dict('')
        path_key = self.OUTPUT.INFO.PATH.NAME

        # Begin building needed keywords
        terms = {path_key: meta_dict[path_key]}
        terms[self.INPUT.METHODS.NAME] = _method

        # get terms from IMAGE
        for key in ['VIEW','FORMAT']:
            term = getattr(self.INPUT.IMAGE, key)
            terms[term.NAME] = self._get_list_query(term)

        # get integers from POSITION
        for key in ['X','Y','Z','WIDTH','HEIGHT','DEPTH']:
            term = getattr(self.INPUT.POSITION, key)
            terms[term.NAME] = self._get_int_query(term)

        # get integers from RESOLUTION
        term = getattr(self.INPUT.RESOLUTION, 'XY')
        terms[term.NAME] = self._get_int_query(term)

        return DataQuery(**terms)

    '''
    Handles Logs and Exceptions
    '''

    def _except(self,result,kwargs):
        action = 'exist'
        if 'check' in kwargs:
            kwargs['val'] = result
            action = 'check'
        message = self.log(action, **kwargs)
        raise HTTPError(self.request.uri, 400, message, [], None)

    def _match_condition(self,result,checked,kwargs):
        if not checked: self._except(result, kwargs)
        return result

    def _try_condition(self,result,check,kwargs):
        try: return check(result)
        except: self._except(result, kwargs)

    def _try_typecast_int(self,qparam,result):
        return self._try_condition(result, np.uint32, {
            'check' : 'a number',
            'term' : qparam
        })

    def _match_list(self,name,v,vlist):
        return self._match_condition(v, v in vlist, {
            'check' : 'one of ['+', '.join(vlist)+']',
            'term' : name
        })

    def _get_list_query(self, _query):
        result = self.get_query_argument(_query.NAME, _query.VALUE)
        return self._match_list(_query.NAME,result,_query.LIST)

    def _get_int_query(self, _query):
        result = self.get_query_argument(_query.NAME, _query.VALUE)
        return self._try_typecast_int(_query.NAME, result)

