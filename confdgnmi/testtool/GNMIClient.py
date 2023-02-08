from confd_gnmi_client import ConfDgNMIClient
import typing as t

class GNMIClient:
    '''This is a user written keyword library.
    These libraries can be pretty handy for more complex tasks an typically
    more efficiant to implement compare to Resource files.

    However, they are less simple in syntax and less transparent in test protocols.

    The TestObject object (t) has the following public functions:

    '''
    
    ROBOT_LIBRARY_SCOPE = 'SUITE'

    def __init__(self) -> None:
        self._client: t.Optional[ConfDgNMIClient] = None
        self.login = 'admin'
        self.password = 'admin'

    def connect(self, ip):
        print('starting client')
        self._client = ConfDgNMIClient(*ip.split(':'), insecure=True,
                                           username=self.login, password=self.password)
        print('started')

    def disconnect(self):
        self.close()

    def close(self):
        self._client.close()

    @property
    def connection(self):
        if not self._client:
            raise SystemError('No Connection established! Connect to server first!')
        return self._client

    def set_login_name(self, login):
        '''Sets the users login name and stores it for authentication.'''
        self.login = login
        info(f'User login set to: {login}')

    def set_password(self, password):
        '''Sets the users login name and stores it for authentication.'''
        self.password = password
        info(f'Password set.')

    def get_capabilities(self):
        return self._client.get_capabilities()
