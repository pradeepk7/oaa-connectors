from oaaclient.templates import CustomIdPProvider
import inspect

# Create test provider
provider = CustomIdPProvider(
    name="test",
    idp_type="SAAS",
    domain="test.com"
)

print("Available methods:", [m for m in dir(provider) if not m.startswith('_')])
print("\nProvider signature:", inspect.signature(CustomIdPProvider.__init__))
