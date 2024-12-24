from oaaclient.templates import CustomApplication
import inspect

app = CustomApplication(name="test", application_type="SAAS")
print("CustomApplication.define_custom_permission signature:", 
      inspect.signature(app.define_custom_permission))
