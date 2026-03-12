# -*- coding: utf-8 -*-
import sys
import os
import json

os.chdir(os.getenv("BACKEND_PROJECT_PATH", None))
sys.dont_write_bytecode = True

from data_extractor import OdbDataExtractor

from abaqus import *
from abaqusConstants import *
from part import *
from step import *
from material import *
from section import *
from assembly import *
from interaction import *
from mesh import *
from visualization import *
from connectorBehavior import *


class Command:
    def __init__(self):
        log_path = "log/abaqus_log.txt"
        if os.path.exists(log_path):
            os.remove(log_path)

        Command.log("[Command] Iniciando execução...\n")

        self.create_paths()
        self.start_extractor()

        Command.log("[Command] End.")

    @staticmethod
    def log(msg):
        log_dir = "log"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        log_path = os.path.join(log_dir, "abaqus_log.txt")
        with open(log_path, "a") as f:
            f.write(msg + "\n")
            f.flush()

    def create_paths(self):
        self.backend_project_path = os.getenv("BACKEND_PROJECT_PATH", None)

        self.path_dir_config = os.path.join(
            os.path.dirname(self.backend_project_path), "backend/extraction_config"
        )
        self.path_data = os.path.join(
            os.path.dirname(self.backend_project_path), "backend/data"
        )

        Command.log("[Command] The paths to the directories were successfully created.")
        Command.log("       - Extraction Dir Config Path: " + self.path_dir_config)
        Command.log("       - Extraction Data Path: " + self.path_data)

    def read_data(self):
        path_config_odb = os.path.join(
            self.path_dir_config, "config_odb.json"
        )

        with open(path_config_odb, 'r') as file:
            config_odb = json.load(file)

        return config_odb

    def start_extractor(self):
        Command.log("[Command] Beggining extraction....")

        config_odb = self.read_data()
        odb_data_extractor = OdbDataExtractor(config_odb, self.backend_project_path)
        odb_data_extractor.run()

        Command.log("       [Extraction] The extraction was completed.")


if __name__ == "__main__":
    try:
        model = Command()
    except Exception as e:
        import traceback
        
        log_dir = "log"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        log_path = os.path.join(log_dir, "abaqus_log.txt")

        with open(log_path, "a") as f:
            f.write("\n====================================================\n")
            f.write("\n[COMMAND ERROR] An exception occurred during execution:\n")
            traceback.print_exc(file=f)
            f.write("\n====================================================\n")

