import json
from datetime import date, datetime
from datetime import time as d_time
from datetime import timezone


class DB:
    def __init__(self, name, verbose=True):
        self.name = name + ".db"
        file = open(self.name, "a+")
        file.close()
        self.verbose = verbose
        if self.verbose:
            print(
                f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] DB created at "
                + self.name
            )

    def get(self, name):
        file = open(self.name, "r")
        data = json.loads(file.read())
        file.close()
        try:
            result = data[name]
            return result
        except:
            if self.verbose:
                print(
                    f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] ERROR : No [{name}] in the database"
                )
            return None

    def print(self):
        file = open(self.name, "r")
        data = json.loads(file.read())
        file.close()
        for key in data:
            print(f"{key} -> {data[key]}")
        return

    def modify(self, name, value):
        file = open(self.name, "r")
        data = json.loads(file.read())
        file.close()
        if self.match(name):
            file = open(self.name, "w")
            data[name] = value
            new_data = json.dumps(data)
            file.write(new_data)
            file.close()
            if self.verbose:
                print(
                    f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] The data {name} has been modified successfully"
                )
        else:
            self.add(name, value)
            if self.verbose:
                print(
                    f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] The data {name} has been modified successfully"
                )

    def remove(self, name):
        file = open(self.name, "r")
        data = json.loads(file.read())
        file.close()
        if self.match(name):
            del data[name]
            file = open(self.name, "w")
            new_data = json.dumps(data)
            file.write(new_data)
            file.close()
            if self.verbose:
                print(
                    f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] The data {name} has been removed successfully"
                )
        else:
            if self.verbose:
                print(
                    f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] ERROR : No ["
                    + name
                    + "] in the database"
                )

    def add(self, name, value):
        file = open(self.name, "r")
        data = json.loads(file.read())
        file.close()
        if self.match(name):
            if self.verbose:
                print(
                    f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] ERROR : [{name}] already exist in the database"
                )
        else:
            data.update({name: value})
            file = open(self.name, "w")
            new_data = json.dumps(data)
            file.write(new_data)
            file.close()
            if self.verbose:
                print(
                    f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] The data ({name} -> {value}) has been added successfully"
                )
        return

    def match(self, name):
        file = open(self.name, "r")
        data = json.loads(file.read())
        file.close()
        return name in data
