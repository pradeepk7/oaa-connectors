from oaaclient.templates import CustomIdPUser
import inspect

print("CustomIdPUser signature:", inspect.signature(CustomIdPUser.__init__))
print("CustomIdPUser attributes:", [attr for attr in dir(CustomIdPUser) if not attr.startswith('_')])
