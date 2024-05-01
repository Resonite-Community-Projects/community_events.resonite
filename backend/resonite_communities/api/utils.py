import os
import importlib

from fastapi import APIRouter, Depends, FastAPI
from fastapi_versionizer import api_version, Versionizer

class VersionedAPIRouter(APIRouter):

    def __init__(self, version, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.major = int(version.split('.')[0])
        self.minor = int(version.split('.')[1])

    def add_api_route(self, *args, **kwargs):
        super().add_api_route(*args, **kwargs)
        for route in self.routes:

            # This try/catch is here to see if having a version 2.0 and 2.1 is supported, need to look deeper
            # It's accepted by the code but their is no much difference on the swagger side, is it really supported?
            try:
                route.endpoint._api_version
                continue
            except Exception:
                pass

            try:
                route.endpoint._api_version = (self.major, self.minor)
            except AttributeError:
                # Support bound methods
                route.endpoint.__func__._api_version = (self.major, self.minor)

def get_route_version_modules(route_version_module_name, route_version_module_file):

    init_file_path = os.path.abspath(route_version_module_file)
    init_dir = os.path.dirname(init_file_path)
    all_files = os.listdir(init_dir)
    python_files = [file for file in all_files if file.endswith('.py') and not file.startswith('__')]

    modules = []
    for python_file in python_files:
        module_name = python_file[:-3]
        module_path = f"{route_version_module_name}.{module_name}"
        module = importlib.import_module(module_path)
        modules.append(module)

    return modules