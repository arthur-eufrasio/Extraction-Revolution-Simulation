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

        odb_path = "odbs/{}.odb".format(odb_name)
        odb = openOdb(path=odb_path)

        self.extracted_data[odb_name] = {}
        fields = [str(f) for f in config["field_variables"]]

        for field in fields:
            self.extracted_data[odb_name][field] = {}

        self._extract_paths(odb, odb_name, config, fields)

        for step_config in config["steps"]:
            step_name = str(step_config["step_name"])
            self._extract_history_outputs(odb, odb_name, step_name)

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
                p1 = path_config["point1"]   # [x, z]
                p2 = path_config["point2"]   # [x, z]
                y_coord = path_config.get("y_coordinate", 0.0)

                # Build 3D path points: (x, y, z) — path lies in the XZ plane
                point1_3d = (p1[0], y_coord, p1[1])
                point2_3d = (p2[0], y_coord, p2[1])

                path_obj_name = "path_{}_{}".format(path_name, odb_name)
                session_path = session.Path(
                    name=path_obj_name,
                    type=POINT_LIST,
                    expression=(point1_3d, point2_3d)
                )

                self.log("[Extractor] Path '{}': ({}) -> ({})".format(
                    path_name, point1_3d, point2_3d))

                for field in fields:
                    if path_name not in self.extracted_data[odb_name][field]:
                        self.extracted_data[odb_name][field][path_name] = []

                    for f_idx in frames:
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
            name="temp_xy_data",
            path=path_obj,
            frame=frame_index,
            step=step_index,
            includeIntersections=True,
            shape=UNDEFORMED,
            labelType=TRUE_DISTANCE,
            variable=(base_field_name, ELEMENT_NODAL, ((COMPONENT, field),)),
            pathStyle=PATH_POINTS
        )

        clean_data = [
            {"true_distance": item[0], "stress": item[1]}
            for item in xy_data_obj.data
        ]

        record = {
            "step": step_name,
            "frame": frame_index,
            "time": frame_time,
            "xy_datalist": tuple(clean_data)
        }
        self.extracted_data[odb_name][field][path_type].append(record)

    def _extract_history_outputs(self, odb, odb_name, step_name):
        step = odb.steps[step_name]
        ext_type = 'tool_rp'
        
        self.extracted_data[odb_name]['S13'][ext_type] = []
        self.extracted_data[odb_name]['S33'][ext_type] = []

        for region_name, history_region in step.historyRegions.items():
            if 'RF1' in history_region.historyOutputs:
                data_rf1 = history_region.historyOutputs['RF1'].data
                data_rf3 = history_region.historyOutputs['RF3'].data
                
                formatted_rf1 = [{'time': d[0], 'RF': d[1]} for d in data_rf1]
                formatted_rf3 = [{'time': d[0], 'RF': d[1]} for d in data_rf3]

                self.extracted_data[odb_name]['S13'][ext_type] = formatted_rf1
                self.extracted_data[odb_name]['S33'][ext_type] = formatted_rf3

    def _extract_contact_normal_force(self, odb, odb_name, step_name, start, stop, config):
        ext_type = 'cnormf'
        node_labels = [
            752, 1193, 753, 1192, 27, 32, 754, 1191
        ]
        
        self.extracted_data[odb_name]['S13'][ext_type] = []
        self.extracted_data[odb_name]['S33'][ext_type] = []

        step = odb.steps[step_name]

        for f_idx in range(start, stop + 1):
            frame = step.frames[f_idx]
            frame_time = frame.frameValue
            
            field_vals = list(frame.fieldOutputs['CNORMF   General_Contact_Domain'].values)
            field_vals.sort(key=self._sort_node_labels)

            rf1_sum = sum(field_vals[n-1].data[0] for n in node_labels)
            rf3_sum = sum(field_vals[n-1].data[2] for n in node_labels)

            self.extracted_data[odb_name]['S13'][ext_type].append({"RF": rf1_sum, "time": frame_time})
            self.extracted_data[odb_name]['S33'][ext_type].append({"RF": rf3_sum, "time": frame_time})

    @staticmethod
    def _sort_node_labels(value):
        instance_name = value.instance.name
        return (1, value.nodeLabel) if instance_name == "CPP-1" else (0, value.nodeLabel)

    def save_to_json(self):
        self.log("[Extractor] Saving data to JSON...")
        output_path = os.path.join(self.data_dir, "data.json")
        
        with open(output_path, "w") as f:
            json.dump(self.extracted_data, f, indent=4)
            
        self.log("[Extractor] File saved: {}".format(output_path))