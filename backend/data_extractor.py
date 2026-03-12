import json
import os
from abaqus import session
from abaqusConstants import *
from odbAccess import openOdb

class OdbDataExtractor:
    def __init__(self, config_odb, backend_project_path):
        self.config_odb = config_odb
        self.backend_project_path = backend_project_path
        self.data_dir = os.path.join(
            os.path.dirname(self.backend_project_path), 
            "backend/data"
        )
        self.extracted_data = {}
        self.log_file_path = "log/abaqus_log.txt"
        self._ensure_directories()

    def _ensure_directories(self):
        if not os.path.exists(os.path.dirname(self.log_file_path)):
            os.makedirs(os.path.dirname(self.log_file_path))
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def log(self, message):
        with open(self.log_file_path, "a") as f:
            f.write(message + "\n")

    def run(self):
        for odb_key, odb_config in self.config_odb.items():
            self.process_single_odb(str(odb_key), odb_config)
        
        self.save_to_json()

    def process_single_odb(self, odb_name, config):
        self.log("[Extractor] Processing ODB: {}".format(odb_name))

        odb_path = str(config["odb_path"])
        odb = openOdb(path=odb_path)

        self.extracted_data[odb_name] = {}
        fields = [str(f) for f in config["field_variables"]]

        for field in fields:
            self.extracted_data[odb_name][field] = {}

        self._extract_paths(odb, odb_name, config, fields)

    def _extract_paths(self, odb, odb_name, config, fields):
        base_field_name = str(config["base_name_field_variables"])
        steps_config = config["steps"]

        session.viewports['Viewport: 1'].setValues(displayedObject=odb)

        for step_config in steps_config:
            step_name = str(step_config["step_name"])
            step_index = step_config["step_index"]
            frames = step_config["frames"]
            paths_config = step_config["paths"]

            self.log("[Extractor] Step '{}', extracting {} path(s)".format(
                step_name, len(paths_config)))

            for path_config in paths_config:
                path_name = str(path_config["name"])
                p1 = path_config["point1"]  
                p2 = path_config["point2"]   
                y_coord = path_config.get("y_coordinate", 0.0)
                num_points = path_config["num_points"]

                point1_3d = (p1[0], y_coord, p1[1])
                point2_3d = (p2[0], y_coord, p2[1])
                
                points_list = self._linspace_points((point1_3d, point2_3d), num_points=num_points)

                path_obj_name = "path_{}_{}".format(step_name, path_name)
                session_path = session.Path(
                    name=path_obj_name,
                    type=POINT_LIST,
                    expression=points_list
                )

                self.log("[Extractor] Path '{}': ({}) -> ({})".format(
                    path_name, point1_3d, point2_3d))

                for field in fields:
                    if step_name not in self.extracted_data[odb_name][field]:
                        self.extracted_data[odb_name][field][step_name] = {}

                    for f_idx in frames:
                        if f_idx not in self.extracted_data[odb_name][field][step_name]:
                            self.extracted_data[odb_name][field][step_name][f_idx] = {}

                        self._process_frame_path(
                            odb, step_name, f_idx, session_path,
                            field, path_name, odb_name,
                            step_index, base_field_name
                        )

    def _process_frame_path(self, odb, step_name, frame_index, path_obj, field, path_type, odb_name, step_index, base_field_name):
        step = odb.steps[step_name]
        frame = step.frames[frame_index]
        frame_time = frame.frameValue

        self.log("[Extractor] Extracting path data: ODB={}, Step={}, Frame={}, Field={}, Path={}".format(
            odb_name, step_name, frame_index, field, path_type))

        xy_data_obj = session.XYDataFromPath(
            name="xy_{}_{}_{}".format(step_name, frame_index, path_type),
            path=path_obj,
            frame=frame_index,
            step=step_index,
            includeIntersections=False,
            shape=UNDEFORMED,
            labelType=TRUE_DISTANCE,
            variable=(base_field_name, INTEGRATION_POINT, ((COMPONENT, field),)),
            pathStyle=PATH_POINTS
        )

        clean_data = [
            {"true_distance": item[0], "stress": item[1]}
            for item in xy_data_obj.data
        ]

        self.extracted_data[odb_name][field][step_name][frame_index][path_type] = {
            "time": frame_time,
            "data": clean_data
        }

    def _linspace_points(self, points_tuple, num_points):
            point_start, point_end = points_tuple
            
            if num_points == 1:
                return (point_start,)
            
            points = []
            for i in range(num_points):
                t = float(i) / (num_points - 1)
                point = tuple(
                    point_start[j] + t * (point_end[j] - point_start[j])
                    for j in range(3)
                )
                points.append(point)
                
            return tuple(points)

    def save_to_json(self):
        self.log("[Extractor] Saving data to JSON...")
        output_path = os.path.join(self.data_dir, "data.json")
        
        with open(output_path, "w") as f:
            json.dump(self.extracted_data, f, indent=4)
            
        self.log("[Extractor] File saved: {}".format(output_path))