from oaaclient import templates

# Print all permission-related classes
print("Available permission classes:", [
    name for name in dir(templates) 
    if "Permission" in name
])
