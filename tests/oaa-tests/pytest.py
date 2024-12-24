from oaaclient import templates
from oaaclient.templates import CustomIdPProvider
import inspect

print("CustomIdPProvider signature:", inspect.signature(CustomIdPProvider.__init__))


print("Available items in templates:", dir(templates))
#print("CustomIdPUser signature:", inspect.signature(CustomIdPUser.__init__))
#print("CustomIdPUser attributes:", dir(CustomIdPUser))
