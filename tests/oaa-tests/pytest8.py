from oaaclient.templates import CustomIdPProvider

provider = CustomIdPProvider(name="test", idp_type="SAAS", domain="test.com")
print("Provider methods:", [m for m in dir(provider) if not m.startswith('_')])
