from oaaclient.templates import CustomApplication
import inspect

# Print the signature
print("CustomApplication signature:", inspect.signature(CustomApplication.__init__))

# Print available fields/methods
print("CustomApplication attributes:", [attr for attr in dir(CustomApplication) if not attr.startswith('_')])

# Try minimal creation
try:
    app = CustomApplication(
        name="test-app"
    )
    print("Success with name only")
    print("Instance attributes:", [attr for attr in dir(app) if not attr.startswith('_')])
except TypeError as e:
    print("Constructor error:", str(e))
