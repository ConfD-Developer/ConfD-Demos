from typing import Literal

DataTypeStr = Literal['ALL', 'CONFIG', 'STATE', 'OPERATIONAL']

def datatype_str_to_int(data_type: DataTypeStr, no_error = True):
    ''' Convert text representation of DataType to standardized integer. '''
    if data_type == 'ALL':
        return 0
    if data_type == 'CONFIG':
        return 1
    if data_type == 'STATE':
        return 2
    if data_type == 'OPERATIONAL':
        return 3
    if no_error:
        return 42
    raise ValueError(f'Unknown data_type! ({data_type})')

EncodingStr = Literal['JSON', 'BYTES', 'PROTO', 'ASCII', 'JSON_IETF']

def encoding_str_to_int(encoding: EncodingStr, no_error = True) -> int:
    ''' Convert text representation of Encoding to standardized integer. '''
    if encoding == 'JSON':
        return 0
    if encoding == 'BYTES':
        return 1
    if encoding == 'PROTO':
        return 2
    if encoding == 'ASCII':
        return 3
    if encoding == 'JSON_IETF':
        return 4
    if no_error:
        return 42
    raise ValueError(f'Unknown encoding! ({encoding})')

def encoding_int_to_str(encoding: int, no_error = True) -> EncodingStr:
    if encoding == 0:
        return 'JSON'
    if encoding == 1:
        return 'BYTES'
    if encoding == 2:
        return 'PROTO'
    if encoding == 3:
        return 'ASCII'
    if encoding == 4:
        return 'JSON_IETF'
    if no_error:
        return f'UNKNOWN({encoding})'
    raise ValueError(f'Unknown encoding! ({encoding})')
