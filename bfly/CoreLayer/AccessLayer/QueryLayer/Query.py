from mimetypes import types_map
from UtilityLayer import INPUT
from UtilityLayer import RUNTIME
from UtilityLayer import OUTPUT
from urllib2 import URLError
import numpy as np

class Query():
    """ Describe content of :mod:`AccessLayer` requests

    Arguments
    -----------
    args: list
        See :class:`TileQuery` for use of positional arguments
    keywords: dict
        Each derived class may use any keyword arguments given \ 
        keys each match a `NAME` of a :class:`NamedStruct`in \ 
        :class:`INPUT`, :class:`RUNTIME`, or :class:`OUTPUT`.

    Attributes
    ------------
        INPUT: :class:`INPUT`
        RUNTIME: :class:`RUNTIME`
        OUTPUT: :class:`OUTPUT`
        keywords: dict
            Taken from ``keywords`` argument
    """
    #: default mime type for HTTP response
    _basic_mime = 'text/plain'

    def __init__(self,*args,**keywords):
        self.INPUT = INPUT()
        self.RUNTIME = RUNTIME()
        self.OUTPUT = OUTPUT()

        command = keywords.get(self.INPUT.METHODS.NAME,'')
        self.INPUT.METHODS.VALUE = command
        self.keywords = keywords

    def set_key(self, struct, key, empty=''):
        """ Copy a the key from keywords to the structure

        Arguments
        ----------
        struct: :class:`NamelessStruct`
            Where to store a value from :data:`keywords`
        key: str
            The key to transfer from :data:`keywords`
        empty: anything
            The value if :data:`keywords` has no ``key``\ 
            and the ``key`` has no default in the struct
        """
        # Get field to be set
        field = struct.get(key, {})
        # Get default value from struct
        default = field.get('VALUE', empty)
        # Get value from input keywords if exists
        val = self.keywords.get(field.NAME, default)
        # Set keyword value to field
        setattr(field, 'VALUE', val)

    @property
    def is_data(self):
        """ Checks whether the method requests images
        """
        image_methods = self.INPUT.METHODS.IMAGE_LIST
        return self.INPUT.METHODS.VALUE in image_methods

    @property
    def mime_type(self):
        """ Gets the mime type for the file_type

        The mime type is from :data:`INPUT.IMAGE` \ 
        if :meth:`is_data`, or :data:`INPUT.INFO` \ 
        otherwise.

        Returns
        --------
        str
            The mime type from ``mimetypes.types_map``
        """
        info_type = self.INPUT.INFO.FORMAT.VALUE
        image_type = self.INPUT.IMAGE.FORMAT.VALUE
        # Use image type for data and info type for info
        file_type = image_type if self.is_data else info_type
        # Get the right mime type or use default for this class
        _basic_mime = self._basic_mime.format(file_type)
        return types_map.get('.'+file_type, _basic_mime)

    def update_source(self, keywords):
        """ Set all attribute values to match keywords

        Arguments
        ----------
        keywords: dict
            * :class:`RUNTIME` ``.IMAGE.SOURCE.NAME``
                (str) -- The subclass of :class:`Datasource`
            * :class:`RUNTIME` ``.IMAGE.BLOCK.NAME``
                (numpy.ndarray) -- 3x1 for any given tile shape
            * :class:`OUTPUT` ``.INFO.TYPE.NAME``
                (str) -- numpy dtype of any given tile
            * :class:`OUTPUT` ``.INFO.SIZE.NAME``
                (numpy.ndarray) -- 3x1 for full volume shape

            Keyword arguments only for :class:`HDF5`

            * :class:`RUNTIME` ``.IMAGE.SOURCE.HDF5.OUTER.NAME``
                (str) -- The direct filename to an hdf5 file
            * :class:`RUNTIME` ``.IMAGE.SOURCE.HDF5.INNER.NAME``
                (str) -- The datset in the file with image data
        """
        # take named keywords
        output = self.OUTPUT.INFO
        runtime = self.RUNTIME.IMAGE
        # Get the right kind of datsource and datatype
        source_val = keywords.get(runtime.SOURCE.NAME)
        type_val = keywords.get(output.TYPE.NAME)
        # Get the right blocksize
        block = keywords.get(runtime.BLOCK.NAME)
        # Unpack dimensions for full volume
        full_size = keywords.get(output.SIZE.NAME, [0,0,0])

        # Make sure the source and type are valid
        self.check_list(runtime.SOURCE.LIST, source_val, 'source')
        self.check_list(output.TYPE.LIST, type_val, 'type')
        # Make sure the blocksize and size have len 3
        self.check_length(3, block, 'blocksize')
        self.check_length(3, full_size, 'full size')
        # Make sure size is bigger than blocksize
        msg = 'bigger than {}'.format(block)
        within = np.all(np.uint32(block) <= full_size)
        self.check_any(within, msg, full_size, 'full size')

        # Set all the clean values
        output.TYPE.VALUE = type_val
        runtime.SOURCE.VALUE = source_val
        runtime.BLOCK.VALUE = np.uint32(block)

        # Set the output size
        output.SIZE.VALUE = {
            output.SIZE.Z.NAME: int(full_size[0]),
            output.SIZE.Y.NAME: int(full_size[1]),
            output.SIZE.X.NAME: int(full_size[2])
        }

        # Optional keywords by source
        inner_path = runtime.SOURCE.HDF5.INNER
        outer_path = runtime.SOURCE.HDF5.OUTER
        optional_fields = [inner_path, outer_path]
        # Assign all optional keywords
        for op in optional_fields:
            op.VALUE = keywords.get(op.NAME,op.VALUE)

    def check_any(self, is_good, message, value, term):
        """ Calls :mod:`raise_error` if check doesn't pass

        Arguments
        ----------
        is_good: bool
            The result of the tested condition
        message: str
            description of possible failure
        value: anything
            the tested property value
        term: str
            the tested property name

        """
        errors = self.RUNTIME.ERROR
        k_check = errors.CHECK.NAME
        k_term = errors.TERM.NAME
        k_out = errors.OUT.NAME

        if not is_good:
            self.raise_error('CHECK',{
                k_check: message,
                k_out: str(value),
                k_term: term
            })

    def check_list(self, whitelist, value, term):
        """ Checks that a value is in a given list

        Arguments
        -----------
        whitelist: list-like
            The list of desired values
        value: anything
            The value should be in the ``whitelist``
        term: str
            The name of the attriubte to test
        """
        in_list = value in whitelist
        msg = 'in {}'.format(whitelist)
        self.check_any(in_list,msg,value,term)

    def check_length(self, length, value, term):
        """ Checks that a value has a given length

        Arguments
        -----------
        length: int
            The desired length of the value
        value: list-like
            The value should be a list or array
        term: str
            The name of the attriubte to test
        """
        msg0 = 'a list or array'
        has_len = hasattr(value, '__len__')
        self.check_any(has_len, msg0, value, term)

        msg1 = 'of length {}'.format(length)
        is_length = len(value) == length
        self.check_any(is_length, msg1, value, term)

    @staticmethod
    def raise_error(status, detail):
        """ raises a 503 URLError for logging

        Arguments
        ----------
        status: str
            The name of the log template
        detail: dict
            * :data:`RUNTIME` ``.ERROR.CHECK.NAME`` \ 
                (str) -- description of failure
            * :data:`RUNTIME` ``.ERROR.TERM.NAME`` \ 
                (str) -- the failed property name
            * :data:`RUNTIME` ``.ERROR.OUT.NAME`` \ 
                (str) -- the failed property value

        Raises
        -------
        URLError
            Contains all ``detail`` needed for log
        """
        raise URLError([status, 503, detail])

